#!/bin/bash
set -e

echo "=== BUILD & DEPLOY MCP JOB v1.2.0 ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "Git commit: 99a6d97"
echo ""

PROJECT="box-magique-gp-prod"
IMAGE="gcr.io/$PROJECT/mcp-cockpit:v1.2.0"
JOB_NAME="mcp-cockpit-iapf-healthcheck"
REGION="us-central1"

# Step 1: Build image
echo "📦 Building Docker image v1.2.0..."
gcloud builds submit \
  --config=- \
  --project=$PROJECT \
  << EOF
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-f'
      - 'mcp_cockpit/Dockerfile.job'
      - '-t'
      - '$IMAGE'
      - '--label'
      - 'git_commit=99a6d97'
      - '--label'
      - 'version=1.2.0'
      - '.'
images:
  - '$IMAGE'
timeout: 1200s
EOF

echo ""
echo "✅ Image built successfully"
echo ""

# Step 2: Get image digest
echo "🔐 Image digest:"
DIGEST=$(gcloud container images describe $IMAGE \
  --format='value(image_summary.digest)')
echo "   $DIGEST"
echo ""

# Step 3: Deploy job
echo "🚀 Deploying job $JOB_NAME..."
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

echo ""
echo "✅ Job deployed successfully"
echo ""

# Step 4: Execute job
echo "🎯 Executing job to generate validation logs..."
START_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

EXECUTION=$(gcloud run jobs execute $JOB_NAME \
  --region=$REGION \
  --project=$PROJECT \
  --format='value(metadata.name)')

echo "✅ Execution started: $EXECUTION"
echo "⏰ Start time: $START_TIME"

# Wait for completion
echo ""
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
  fi
  
  sleep 5
done

echo ""
echo "💾 Execution: $EXECUTION"
echo "⏰ Start: $START_TIME"
echo "⏰ End: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# Wait for log indexing
echo "⏳ Waiting for log indexing (15s)..."
sleep 15

# Fetch logs
echo ""
echo "🔍 Fetching logs with ProxyTool validation..."
gcloud logging read \
  "resource.type=\"cloud_run_job\" AND \
   resource.labels.job_name=\"$JOB_NAME\" AND \
   timestamp>=\"$START_TIME\"" \
  --limit=200 \
  --format=json \
  --project=$PROJECT \
  > /tmp/mcp_job_v1.2.0_logs.json

LOGS_COUNT=$(cat /tmp/mcp_job_v1.2.0_logs.json | jq '. | length')
echo "✅ Logs retrieved: $LOGS_COUNT entries"
echo ""

# Display ProxyTool logs
echo "📊 LOGS ProxyTool:"
echo "---"
cat /tmp/mcp_job_v1.2.0_logs.json | \
  jq -r '.[] | 
    select(.textPayload | contains("ProxyTool")) | 
    {timestamp, log: .textPayload}' | head -20

echo ""
echo "=== BUILD & DEPLOY v1.2.0 COMPLETE ==="

