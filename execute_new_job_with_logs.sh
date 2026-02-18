#!/bin/bash
set -e

echo "=== EXÉCUTION NOUVEAU JOB MCP AVEC CAPTURE LOGS ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

PROJECT="box-magique-gp-prod"
JOB_NAME="mcp-cockpit-iapf-healthcheck"
REGION="us-central1"

# Timestamp début
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "⏰ Start time: $START_TIME"
echo ""

# Exécuter le job
echo "🚀 Exécution du job $JOB_NAME..."
EXECUTION=$(gcloud run jobs execute $JOB_NAME \
  --region=$REGION \
  --project=$PROJECT \
  --format='value(metadata.name)')

echo "✅ Job started: $EXECUTION"
echo ""

# Attendre completion
echo "⏳ Attente completion (max 3 min)..."
for i in {1..36}; do
  STATUS=$(gcloud run jobs executions describe $EXECUTION \
    --region=$REGION \
    --project=$PROJECT \
    --format='value(status.conditions[0].type)')
  
  echo "[$(date +%H:%M:%S)] Status: $STATUS"
  
  if [[ "$STATUS" == "Completed" ]]; then
    echo "✅ JOB COMPLETED"
    break
  elif [[ "$STATUS" == "Failed" ]]; then
    echo "❌ JOB FAILED"
    break
  fi
  
  sleep 5
done

echo ""
echo "📊 Final execution status:"
gcloud run jobs executions describe $EXECUTION \
  --region=$REGION \
  --project=$PROJECT \
  --format='value(status.conditions[0].status,status.completionTime)'

echo ""
echo "💾 Execution name: $EXECUTION"
echo "⏰ Start: $START_TIME"
echo "⏰ End: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"

# Attendre 10s pour que les logs soient indexés
echo ""
echo "⏳ Attente indexation logs (10s)..."
sleep 10

echo ""
echo "🔍 Récupération logs de l'exécution $EXECUTION..."

# Récupérer les logs de cette exécution
gcloud logging read \
  "resource.type=\"cloud_run_job\" AND \
   resource.labels.job_name=\"$JOB_NAME\" AND \
   resource.labels.location=\"$REGION\" AND \
   timestamp>=\"$START_TIME\"" \
  --limit=300 \
  --format=json \
  --project=$PROJECT \
  > /tmp/mcp_job_${EXECUTION}_logs.json

LOGS_COUNT=$(cat /tmp/mcp_job_${EXECUTION}_logs.json | jq '. | length')
echo "✅ Logs récupérés: $LOGS_COUNT entrées"
echo ""

# Afficher les logs ProxyTool
echo "📊 Logs ProxyTool:"
echo "---"
cat /tmp/mcp_job_${EXECUTION}_logs.json | \
  jq -r '.[] | select(.jsonPayload.message | contains("ProxyTool")) | 
    {timestamp: .timestamp, severity: .severity, message: .jsonPayload.message}' \
  2>/dev/null || echo "Aucun log ProxyTool trouvé"

echo ""
echo "=== FIN EXÉCUTION & RÉCUPÉRATION LOGS ==="

