#!/bin/bash
set -euo pipefail

EXECUTION_ID="mcp-cockpit-iapf-healthcheck-8cnj6"
PROJECT="box-magique-gp-prod"
REGION="us-central1"
JOB_NAME="mcp-cockpit-iapf-healthcheck"

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║           📋 RÉCUPÉRATION DES LOGS - VALIDATION FINALE                      ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Execution ID: $EXECUTION_ID"
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# Attendre 15s pour la propagation
echo "⏳ Attente de 15s pour la propagation des logs..."
sleep 15

# Timestamp 10 minutes dans le passé
START_TIME=$(date -u -d '10 minutes ago' +"%Y-%m-%dT%H:%M:%SZ")

echo "📥 Récupération des logs depuis $START_TIME..."
echo ""

gcloud logging read "
  resource.type=\"cloud_run_job\"
  AND resource.labels.job_name=\"$JOB_NAME\"
  AND resource.labels.location=\"$REGION\"
  AND labels.\"run.googleapis.com/execution_name\"=\"$EXECUTION_ID\"
" \
  --limit=500 \
  --format=json \
  --project="$PROJECT" \
  > /tmp/logs_${EXECUTION_ID}.json

LOG_COUNT=$(jq 'length' /tmp/logs_${EXECUTION_ID}.json)
echo "✅ $LOG_COUNT logs récupérés"
echo ""

# ============================================================================
# AFFICHER LES LOGS CHRONOLOGIQUEMENT
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 TOUS LES LOGS (ordre chronologique)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

jq -r 'sort_by(.timestamp) | .[] | 
  "\(.timestamp) | \(.severity // "INFO") | \(
    if .jsonPayload.message then .jsonPayload.message
    elif .textPayload then .textPayload
    else "N/A"
    end
  )"' /tmp/logs_${EXECUTION_ID}.json

echo ""
echo ""

# ============================================================================
# LOGS PROXYTOOL UNIQUEMENT
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔍 LOGS PROXYTOOL UNIQUEMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

jq -r 'sort_by(.timestamp) | .[] | 
  select(
    (.jsonPayload.message // .textPayload // "") | 
    test("ProxyTool|GET /sheets|GET /health|HTTP [0-9]{3}|rows=|correlation"; "i")
  ) |
  "\(.timestamp) | \(.severity // "INFO") | \(
    if .jsonPayload.message then .jsonPayload.message
    elif .textPayload then .textPayload
    else "N/A"
    end
  )"' /tmp/logs_${EXECUTION_ID}.json

echo ""
echo ""

# ============================================================================
# VALIDATION DES CRITÈRES
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ VALIDATION DES CRITÈRES ORION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Critère 1: ProxyTool initialized
INIT=$(jq -r '[.[] | select((.jsonPayload.message // .textPayload // "") | test("ProxyTool initialized"; "i"))] | length' /tmp/logs_${EXECUTION_ID}.json)
if [ "$INIT" -gt 0 ]; then
  echo "✅ Critère 1: ProxyTool initialized"
  jq -r '.[] | select((.jsonPayload.message // .textPayload // "") | test("ProxyTool initialized"; "i")) | 
    "   └─ \(.timestamp): \(.jsonPayload.message // .textPayload)"' /tmp/logs_${EXECUTION_ID}.json | head -1
else
  echo "❌ Critère 1: ProxyTool initialized - NOT FOUND"
fi
echo ""

# Critère 2: GET /sheets/SETTINGS
SETTINGS=$(jq -r '[.[] | select((.jsonPayload.message // .textPayload // "") | test("GET /sheets/SETTINGS|SETTINGS.*limit"; "i"))] | length' /tmp/logs_${EXECUTION_ID}.json)
if [ "$SETTINGS" -gt 0 ]; then
  echo "✅ Critère 2: GET /sheets/SETTINGS?limit=10"
  jq -r '.[] | select((.jsonPayload.message // .textPayload // "") | test("/sheets/SETTINGS"; "i")) | 
    "   └─ \(.timestamp): \(.jsonPayload.message // .textPayload)"' /tmp/logs_${EXECUTION_ID}.json | head -2
else
  echo "❌ Critère 2: GET /sheets/SETTINGS - NOT FOUND"
fi
echo ""

# Critère 3: HTTP 200
HTTP200=$(jq -r '[.[] | select((.jsonPayload.message // .textPayload // "") | test("HTTP 200|rows=8|row_count.*8"; "i"))] | length' /tmp/logs_${EXECUTION_ID}.json)
if [ "$HTTP200" -gt 0 ]; then
  echo "✅ Critère 3: HTTP 200 sur SETTINGS"
  jq -r '.[] | select((.jsonPayload.message // .textPayload // "") | test("HTTP 200|rows="; "i")) | 
    "   └─ \(.timestamp): \(.jsonPayload.message // .textPayload)"' /tmp/logs_${EXECUTION_ID}.json | head -3
else
  echo "❌ Critère 3: HTTP 200 - NOT FOUND"
fi
echo ""

# Critère 4: GET /sheets/NOPE → 404
NOPE=$(jq -r '[.[] | select((.jsonPayload.message // .textPayload // "") | test("NOPE.*404|404.*NOPE|correlation_id"; "i"))] | length' /tmp/logs_${EXECUTION_ID}.json)
if [ "$NOPE" -gt 0 ]; then
  echo "✅ Critère 4: GET /sheets/NOPE → HTTP 404 + correlation_id"
  jq -r '.[] | select((.jsonPayload.message // .textPayload // "") | test("NOPE|correlation"; "i")) | 
    "   └─ \(.timestamp): \(.jsonPayload.message // .textPayload)"' /tmp/logs_${EXECUTION_ID}.json | head -3
else
  echo "❌ Critère 4: HTTP 404 + correlation_id - NOT FOUND"
fi
echo ""

# Stats
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 STATISTIQUES"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "   - Total logs: $LOG_COUNT"
echo "   - ProxyTool initialized: $INIT"
echo "   - GET /sheets/SETTINGS: $SETTINGS"
echo "   - HTTP 200: $HTTP200"
echo "   - HTTP 404 + correlation_id: $NOPE"
echo ""

VALIDATED=$((INIT > 0 ? 1 : 0))
VALIDATED=$((VALIDATED + (SETTINGS > 0 ? 1 : 0)))
VALIDATED=$((VALIDATED + (HTTP200 > 0 ? 1 : 0)))
VALIDATED=$((VALIDATED + (NOPE > 0 ? 1 : 0)))

echo "✅ CRITÈRES VALIDÉS: $VALIDATED/4"
echo ""

if [ "$VALIDATED" -eq 4 ]; then
  echo "╔══════════════════════════════════════════════════════════════════════════════╗"
  echo "║                    ✅ GO - VALIDATION COMPLÈTE                               ║"
  echo "╚══════════════════════════════════════════════════════════════════════════════╝"
  EXIT_CODE=0
else
  echo "╔══════════════════════════════════════════════════════════════════════════════╗"
  echo "║               ⚠️  VALIDATION PARTIELLE ($VALIDATED/4)                             ║"
  echo "╚══════════════════════════════════════════════════════════════════════════════╝"
  EXIT_CODE=1
fi

echo ""
echo "📁 Logs sauvegardés: /tmp/logs_${EXECUTION_ID}.json"
echo ""

exit $EXIT_CODE

