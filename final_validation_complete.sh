#!/bin/bash
set -e

PROJECT="box-magique-gp-prod"
IMAGE="gcr.io/$PROJECT/mcp-cockpit:v1.2.1"
JOB_NAME="mcp-cockpit-iapf-healthcheck"
REGION="us-central1"

echo "=== VALIDATION FINALE ORION - v1.2.1 ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Image: $IMAGE"
echo ""

# Deploy
echo "🚀 DEPLOYING JOB v1.2.1..."
gcloud run jobs deploy $JOB_NAME \
  --image=$IMAGE \
  --region=$REGION \
  --service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
  --set-env-vars="MCP_PROXY_API_KEY=kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE,ENVIRONMENT=PROD,USE_METADATA_AUTH=true" \
  --max-retries=0 \
  --task-timeout=600s \
  --memory=512Mi \
  --cpu=1 \
  --project=$PROJECT

echo "✅ DEPLOYED"
echo ""

# Execute
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "🎯 EXECUTING JOB..."
echo "Start time: $START_TIME"
echo ""

EXECUTION=$(gcloud run jobs execute $JOB_NAME \
  --region=$REGION \
  --project=$PROJECT \
  --format='value(metadata.name)')

echo "Execution: $EXECUTION"
echo ""

# Wait
echo "⏳ Waiting for completion..."
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
    exit 1
  fi
  
  sleep 5
done

echo ""
echo "⏳ Waiting for log indexing (20s)..."
sleep 20

# Fetch ALL logs
echo ""
echo "🔍 FETCHING LOGS..."
gcloud logging read \
  "resource.type=\"cloud_run_job\" AND \
   resource.labels.job_name=\"$JOB_NAME\" AND \
   timestamp>=\"$START_TIME\"" \
  --limit=500 \
  --format=json \
  --project=$PROJECT \
  > /tmp/final_validation_logs.json

LOGS_COUNT=$(cat /tmp/final_validation_logs.json | jq '. | length')
echo "✅ Logs retrieved: $LOGS_COUNT entries"
echo ""

# Display ALL logs chronologically
echo "=========================================="
echo "LOGS COMPLETS (chronologique):"
echo "=========================================="
cat /tmp/final_validation_logs.json | \
  jq -r '.[] | select(.textPayload) | {t: .timestamp, log: .textPayload}' | \
  jq -s 'sort_by(.t) | .[]' | \
  jq -r '.log'

echo ""
echo "=========================================="
echo "FILTRES SPÉCIFIQUES:"
echo "=========================================="

# ProxyTool logs
echo ""
echo "📊 LOGS ProxyTool:"
echo "---"
cat /tmp/final_validation_logs.json | \
  jq -r '.[] | select(.textPayload | contains("ProxyTool")) | .textPayload' | \
  sort

# SETTINGS logs
echo ""
echo "📊 LOGS /sheets/SETTINGS:"
echo "---"
cat /tmp/final_validation_logs.json | \
  jq -r '.[] | select(.textPayload | contains("SETTINGS")) | .textPayload' | \
  sort

# HTTP status logs
echo ""
echo "📊 LOGS HTTP Status:"
echo "---"
cat /tmp/final_validation_logs.json | \
  jq -r '.[] | select(.textPayload | contains("HTTP 200") or contains("HTTP 404")) | .textPayload' | \
  sort

echo ""
echo "=== VALIDATION COMPLETE ===" 

