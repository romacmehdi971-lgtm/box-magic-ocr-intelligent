#!/bin/bash
set -euo pipefail

PROJECT="box-magique-gp-prod"
REGION="us-central1"
JOB_NAME="mcp-cockpit-iapf-healthcheck"
EXECUTION_ID="mcp-cockpit-iapf-healthcheck-k6hrg"

echo "=== EXTRACTION LOGS VALIDATION FINALE v1.2.1 ==="
echo "Execution: $EXECUTION_ID"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# 1. Récupérer TOUS les logs de l'exécution
echo "📋 TOUS LES LOGS (ordre chronologique):"
echo "========================================"
gcloud logging read "
  resource.type=\"cloud_run_job\"
  AND resource.labels.job_name=\"$JOB_NAME\"
  AND resource.labels.location=\"$REGION\"
  AND labels.\"run.googleapis.com/execution_name\"=\"$EXECUTION_ID\"
" \
  --limit=500 \
  --format=json \
  --project="$PROJECT" \
  > /tmp/all_logs_k6hrg.json

# Trier par timestamp et afficher
jq -r 'sort_by(.timestamp) | .[] | 
  .timestamp + " | " + 
  (.severity // "INFO") + " | " +
  (
    if .jsonPayload.message then .jsonPayload.message
    elif .textPayload then .textPayload
    else (.jsonPayload | tostring)
    end
  )' /tmp/all_logs_k6hrg.json

echo ""
echo ""

# 2. Extraire spécifiquement les logs ProxyTool
echo "🔍 LOGS PROXYTOOL (filtrés):"
echo "============================"
jq -r 'sort_by(.timestamp) | .[] | 
  select(
    (.jsonPayload.message // .textPayload // "") | 
    test("ProxyTool|GET /sheets|HTTP [0-9]{3}|row_count"; "i")
  ) |
  .timestamp + " | " +
  (.severity // "INFO") + " | " +
  (
    if .jsonPayload.message then .jsonPayload.message
    elif .textPayload then .textPayload
    else (.jsonPayload | tostring)
    end
  )' /tmp/all_logs_k6hrg.json

echo ""
echo ""

# 3. Extraire l'appel /sheets/SETTINGS spécifiquement
echo "📊 APPEL /sheets/SETTINGS?limit=10 - DÉTAILS:"
echo "=============================================="
jq -r 'sort_by(.timestamp) | .[] | 
  select(
    (.jsonPayload.message // .textPayload // "") | 
    test("SETTINGS|row_count|headers"; "i")
  ) |
  {
    timestamp: .timestamp,
    severity: .severity,
    message: (.jsonPayload.message // .textPayload // ""),
    full_payload: .jsonPayload
  }' /tmp/all_logs_k6hrg.json

echo ""
echo ""

# 4. Chercher la réponse HTTP dans les logs
echo "🌐 RÉPONSE HTTP (code + body):"
echo "==============================="
jq -r 'sort_by(.timestamp) | .[] | 
  select(
    (.jsonPayload | tostring) | 
    test("200|row_count|headers|data"; "i")
  ) |
  {
    timestamp: .timestamp,
    http_status: (.jsonPayload.http_status // .jsonPayload.status // "N/A"),
    body_preview: (.jsonPayload | 
      if .body then .body 
      elif .data then .data
      elif .row_count then {row_count: .row_count, headers: .headers}
      else .
      end
    )
  }' /tmp/all_logs_k6hrg.json

echo ""
echo ""

# 5. Stats finales
TOTAL_LOGS=$(jq 'length' /tmp/all_logs_k6hrg.json)
PROXYTOOL_LOGS=$(jq '[.[] | select((.jsonPayload.message // .textPayload // "") | test("ProxyTool"; "i"))] | length' /tmp/all_logs_k6hrg.json)
SETTINGS_LOGS=$(jq '[.[] | select((.jsonPayload.message // .textPayload // "") | test("SETTINGS"; "i"))] | length' /tmp/all_logs_k6hrg.json)

echo "📈 STATISTIQUES:"
echo "================"
echo "Total logs: $TOTAL_LOGS"
echo "Logs ProxyTool: $PROXYTOOL_LOGS"
echo "Logs SETTINGS: $SETTINGS_LOGS"
echo ""
echo "✅ Fichier complet sauvegardé: /tmp/all_logs_k6hrg.json"

