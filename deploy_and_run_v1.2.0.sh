#!/bin/bash
set -e

PROJECT="box-magique-gp-prod"
IMAGE="gcr.io/$PROJECT/mcp-cockpit:v1.2.0"
JOB_NAME="mcp-cockpit-iapf-healthcheck"
REGION="us-central1"

echo "=== DEPLOY & RUN v1.2.0 ==="
echo ""

# Deploy
echo "🚀 Deploying job..."
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

echo "✅ Deployed"
echo ""

# Execute
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "🎯 Executing job..."
echo "⏰ Start: $START_TIME"

EXECUTION=$(gcloud run jobs execute $JOB_NAME \
  --region=$REGION \
  --project=$PROJECT \
  --format='value(metadata.name)')

echo "✅ Execution: $EXECUTION"
echo ""

# Wait
echo "⏳ Waiting completion..."
for i in {1..36}; do
  STATUS=$(gcloud run jobs executions describe $EXECUTION \
    --region=$REGION \
    --project=$PROJECT \
    --format='value(status.conditions[0].type)')
  
  [[ "$STATUS" == "Completed" ]] && echo "✅ COMPLETED" && break
  sleep 5
done

echo ""
echo "⏳ Waiting log indexing (15s)..."
sleep 15

# Fetch logs
echo ""
echo "🔍 Fetching logs..."
gcloud logging read \
  "resource.type=\"cloud_run_job\" AND \
   resource.labels.job_name=\"$JOB_NAME\" AND \
   timestamp>=\"$START_TIME\"" \
  --limit=300 \
  --format=json \
  --project=$PROJECT \
  > /tmp/v1.2.0_logs.json

echo "✅ Logs: $(cat /tmp/v1.2.0_logs.json | jq '. | length') entries"
echo ""

# Display ProxyTool logs
echo "📊 LOGS ProxyTool:"
echo "===================="
cat /tmp/v1.2.0_logs.json | \
  jq -r '.[] | select(.textPayload | contains("ProxyTool")) | .textPayload' | \
  sort

echo ""
echo "=== DONE ===" 

