#!/bin/bash
set -e

echo "=== CRITICAL FIX: Redeploy with ALL environment variables ==="

CURRENT_IMAGE="gcr.io/box-magique-gp-prod/mcp-memory-proxy:phase2-cfeaedd"

echo "📦 Using image: $CURRENT_IMAGE"
echo "🔐 Mounting secret: mcp-cockpit-sa-key:latest → /secrets/sa-key.json"
echo ""

gcloud run deploy mcp-memory-proxy \
    --project=box-magique-gp-prod \
    --region=us-central1 \
    --image="$CURRENT_IMAGE" \
    --service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
    --set-secrets="/secrets/sa-key.json=mcp-cockpit-sa-key:latest" \
    --set-env-vars="GOOGLE_SHEET_ID=1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ,GOOGLE_APPLICATION_CREDENTIALS=/secrets/sa-key.json,MCP_ENVIRONMENT=STAGING,MCP_GCP_PROJECT_ID=box-magique-gp-prod,MCP_GCP_REGION=us-central1,MCP_CLOUD_RUN_SERVICE=mcp-memory-proxy,MCP_WEB_ALLOWED_DOMAINS=developers.google.com;cloud.google.com;googleapis.dev,MCP_WEB_QUOTA_DAILY=100,MCP_TERMINAL_QUOTA_DAILY_READ=50,MCP_TERMINAL_QUOTA_DAILY_WRITE=10,GIT_COMMIT=cfeaedd,VERSION=3.0.7-phase2-mcp-tools,READ_ONLY_MODE=true,DRY_RUN_MODE=true,API_KEY=kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE,CLOUD_RUN_SERVICE=mcp-memory-proxy,LOG_LEVEL=INFO,GCP_PROJECT_ID=box-magique-gp-prod,GCP_REGION=us-central1,ENVIRONMENT=STAGING" \
    --memory=512Mi \
    --cpu=1 \
    --timeout=300s \
    --allow-unauthenticated \
    --quiet

echo ""
echo "✅ Redeployment completed with ALL variables!"
echo ""

# Verify
echo "🔍 Verification:"
gcloud run services describe mcp-memory-proxy \
    --project=box-magique-gp-prod \
    --region=us-central1 \
    --format='table(status.url,status.latestReadyRevisionName)'

echo ""
echo "🎯 Testing Drive endpoint..."
sleep 5
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/drive/file/1LwUZ67zVstl2tuogcdYYihPilUAXQai3/metadata" | jq
