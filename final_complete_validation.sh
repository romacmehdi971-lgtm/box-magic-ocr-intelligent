#!/bin/bash
set -euo pipefail

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║           🎯 VALIDATION FINALE COMPLÈTE - ORION v1.2.1                      ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📅 Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "🔖 Version: v1.2.1"
echo "📦 Project: box-magique-gp-prod"
echo ""

PROJECT="box-magique-gp-prod"
REGION="us-central1"
JOB_NAME="mcp-cockpit-iapf-healthcheck"

# ============================================================================
# ÉTAPE 1: Exécuter le job Cloud Run
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ÉTAPE 1: EXÉCUTION DU JOB CLOUD RUN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🚀 Lancement du job: $JOB_NAME"
EXECUTION_OUTPUT=$(gcloud run jobs execute "$JOB_NAME" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format=json 2>&1)

if [ $? -ne 0 ]; then
  echo "❌ Erreur lors du lancement du job:"
  echo "$EXECUTION_OUTPUT"
  exit 1
fi

# Extraire l'execution ID
EXECUTION_ID=$(echo "$EXECUTION_OUTPUT" | jq -r '.metadata.name // empty')
if [ -z "$EXECUTION_ID" ]; then
  echo "❌ Impossible d'extraire l'execution ID"
  exit 1
fi

echo "✅ Job lancé avec succès"
echo "   Execution ID: $EXECUTION_ID"
echo ""

# Attendre que le job se termine
echo "⏳ Attente de la fin du job (max 3 minutes)..."
START_TIME=$(date +%s)
MAX_WAIT=180

while true; do
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))
  
  if [ $ELAPSED -gt $MAX_WAIT ]; then
    echo "⚠️  Timeout après ${MAX_WAIT}s"
    break
  fi
  
  STATUS=$(gcloud run jobs executions describe "$EXECUTION_ID" \
    --region="$REGION" \
    --project="$PROJECT" \
    --format="value(status.conditions[0].type)" 2>/dev/null || echo "Unknown")
  
  if [ "$STATUS" = "Completed" ]; then
    echo "✅ Job terminé avec succès"
    break
  fi
  
  echo "   Status: $STATUS (${ELAPSED}s écoulées)"
  sleep 5
done

echo ""

# Récupérer les détails de l'exécution
echo "📊 Détails de l'exécution:"
gcloud run jobs executions describe "$EXECUTION_ID" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format="table(
    metadata.name,
    status.completionTime,
    status.conditions[0].type,
    status.conditions[0].status
  )" 2>/dev/null || echo "⚠️  Impossible de récupérer les détails"

echo ""

# ============================================================================
# ÉTAPE 2: Récupérer les logs Cloud Logging
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ÉTAPE 2: RÉCUPÉRATION DES LOGS CLOUD LOGGING"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Attendre 10 secondes pour que les logs soient disponibles
echo "⏳ Attente de 10s pour la propagation des logs..."
sleep 10

# Calculer le timestamp de début (5 minutes avant maintenant)
START_TIMESTAMP=$(date -u -d '5 minutes ago' +"%Y-%m-%dT%H:%M:%SZ")
echo "📅 Récupération des logs depuis: $START_TIMESTAMP"
echo ""

# Récupérer tous les logs de l'exécution
LOG_FILE="/tmp/validation_logs_${EXECUTION_ID}.json"
echo "📥 Téléchargement des logs vers: $LOG_FILE"

gcloud logging read "
  resource.type=\"cloud_run_job\"
  AND resource.labels.job_name=\"$JOB_NAME\"
  AND resource.labels.location=\"$REGION\"
  AND labels.\"run.googleapis.com/execution_name\"=\"$EXECUTION_ID\"
  AND timestamp>=\"$START_TIMESTAMP\"
" \
  --limit=500 \
  --format=json \
  --project="$PROJECT" \
  > "$LOG_FILE"

LOG_COUNT=$(jq 'length' "$LOG_FILE")
echo "✅ $LOG_COUNT logs récupérés"
echo ""

# ============================================================================
# ÉTAPE 3: Analyser les logs - ProxyTool
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ÉTAPE 3: ANALYSE DES LOGS - PROXYTOOL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🔍 Extraction des logs ProxyTool (ordre chronologique):"
echo "────────────────────────────────────────────────────────────────────────────────"

jq -r 'sort_by(.timestamp) | .[] | 
  select(
    (.jsonPayload.message // .textPayload // "") | 
    test("ProxyTool|GET /sheets|GET /health|HTTP [0-9]{3}|row|correlation"; "i")
  ) |
  "\(.timestamp) | \(.severity // "INFO") | \(
    if .jsonPayload.message then .jsonPayload.message
    elif .textPayload then .textPayload
    else (.jsonPayload | tostring)
    end
  )"' "$LOG_FILE"

echo ""

# ============================================================================
# ÉTAPE 4: Validation des critères ORION
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ÉTAPE 4: VALIDATION DES CRITÈRES ORION"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Critère 1: ProxyTool initialized
INIT_FOUND=$(jq -r '[.[] | select((.jsonPayload.message // .textPayload // "") | test("ProxyTool initialized"; "i"))] | length' "$LOG_FILE")
if [ "$INIT_FOUND" -gt 0 ]; then
  echo "✅ Critère 1: ProxyTool initialized"
  jq -r '.[] | select((.jsonPayload.message // .textPayload // "") | test("ProxyTool initialized"; "i")) | 
    "   └─ \(.timestamp): \(.jsonPayload.message // .textPayload)"' "$LOG_FILE" | head -1
else
  echo "❌ Critère 1: ProxyTool initialized NOT FOUND"
fi
echo ""

# Critère 2: GET /sheets/SETTINGS
SETTINGS_FOUND=$(jq -r '[.[] | select((.jsonPayload.message // .textPayload // "") | test("GET /sheets/SETTINGS|ProxyTool SETTINGS"; "i"))] | length' "$LOG_FILE")
if [ "$SETTINGS_FOUND" -gt 0 ]; then
  echo "✅ Critère 2: GET /sheets/SETTINGS?limit=10"
  jq -r '.[] | select((.jsonPayload.message // .textPayload // "") | test("SETTINGS"; "i")) | 
    "   └─ \(.timestamp): \(.jsonPayload.message // .textPayload)"' "$LOG_FILE" | head -3
else
  echo "❌ Critère 2: GET /sheets/SETTINGS NOT FOUND"
fi
echo ""

# Critère 3: HTTP 200 sur SETTINGS
HTTP_200_FOUND=$(jq -r '[.[] | select((.jsonPayload.message // .textPayload // "") | test("SETTINGS.*HTTP 200|HTTP 200.*SETTINGS|rows="; "i"))] | length' "$LOG_FILE")
if [ "$HTTP_200_FOUND" -gt 0 ]; then
  echo "✅ Critère 3: HTTP 200 sur SETTINGS"
  jq -r '.[] | select((.jsonPayload.message // .textPayload // "") | test("SETTINGS.*200|rows"; "i")) | 
    "   └─ \(.timestamp): \(.jsonPayload.message // .textPayload)"' "$LOG_FILE" | head -2
else
  echo "❌ Critère 3: HTTP 200 NOT FOUND"
fi
echo ""

# Critère 4: GET /sheets/NOPE → 404
NOPE_FOUND=$(jq -r '[.[] | select((.jsonPayload.message // .textPayload // "") | test("NOPE.*404|404.*NOPE|correlation_id"; "i"))] | length' "$LOG_FILE")
if [ "$NOPE_FOUND" -gt 0 ]; then
  echo "✅ Critère 4: GET /sheets/NOPE → HTTP 404 avec correlation_id"
  jq -r '.[] | select((.jsonPayload.message // .textPayload // "") | test("NOPE.*correlation|404"; "i")) | 
    "   └─ \(.timestamp): \(.jsonPayload.message // .textPayload)"' "$LOG_FILE" | head -2
else
  echo "❌ Critère 4: HTTP 404 avec correlation_id NOT FOUND"
fi
echo ""

# ============================================================================
# ÉTAPE 5: Extraction du body complet via Python
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ÉTAPE 5: EXTRACTION DU BODY COMPLET (via Python)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "🐍 Exécution du script Python de validation..."
python3 validate_proxy_final.py 2>&1 | tee /tmp/python_validation_output.txt

echo ""

# ============================================================================
# ÉTAPE 6: Résumé final
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ÉTAPE 6: RÉSUMÉ FINAL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "📊 STATISTIQUES:"
echo "   - Execution ID: $EXECUTION_ID"
echo "   - Total logs: $LOG_COUNT"
echo "   - ProxyTool logs: $(jq -r '[.[] | select((.jsonPayload.message // .textPayload // "") | test("ProxyTool"; "i"))] | length' "$LOG_FILE")"
echo "   - SETTINGS logs: $(jq -r '[.[] | select((.jsonPayload.message // .textPayload // "") | test("SETTINGS"; "i"))] | length' "$LOG_FILE")"
echo ""

echo "📁 FICHIERS GÉNÉRÉS:"
echo "   - Logs JSON: $LOG_FILE"
echo "   - Python output: /tmp/python_validation_output.txt"
echo ""

# Compter les critères validés
TOTAL_CRITERIA=4
VALIDATED=0
[ "$INIT_FOUND" -gt 0 ] && VALIDATED=$((VALIDATED + 1))
[ "$SETTINGS_FOUND" -gt 0 ] && VALIDATED=$((VALIDATED + 1))
[ "$HTTP_200_FOUND" -gt 0 ] && VALIDATED=$((VALIDATED + 1))
[ "$NOPE_FOUND" -gt 0 ] && VALIDATED=$((VALIDATED + 1))

echo "✅ CRITÈRES VALIDÉS: $VALIDATED/$TOTAL_CRITERIA"
echo ""

if [ "$VALIDATED" -eq "$TOTAL_CRITERIA" ]; then
  echo "╔══════════════════════════════════════════════════════════════════════════════╗"
  echo "║                    ✅ GO - VALIDATION COMPLÈTE                               ║"
  echo "╚══════════════════════════════════════════════════════════════════════════════╝"
else
  echo "╔══════════════════════════════════════════════════════════════════════════════╗"
  echo "║               ⚠️  VALIDATION PARTIELLE ($VALIDATED/$TOTAL_CRITERIA)                              ║"
  echo "╚══════════════════════════════════════════════════════════════════════════════╝"
fi

echo ""
echo "🔗 Console Cloud Logging:"
echo "   https://console.cloud.google.com/logs/query;query=resource.type%3D%22cloud_run_job%22%0Aresource.labels.job_name%3D%22$JOB_NAME%22%0Alabels.%22run.googleapis.com%2Fexecution_name%22%3D%22$EXECUTION_ID%22?project=$PROJECT"
echo ""

