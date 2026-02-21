#!/bin/bash
set -e

SHORT_SHA="1bc2201"
IMAGE="gcr.io/box-magique-gp-prod/mcp-memory-proxy:phase2-${SHORT_SHA}"

echo "🚀 Deploying Phase 3 with ALL env vars preserved (MERGE mode)"

gcloud run deploy mcp-memory-proxy \
    --project=box-magique-gp-prod \
    --region=us-central1 \
    --image="$IMAGE" \
    --service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
    --set-secrets="/secrets/sa-key.json=mcp-cockpit-sa-key:latest" \
    --set-env-vars="GOOGLE_SHEET_ID=1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ,GOOGLE_APPLICATION_CREDENTIALS=/secrets/sa-key.json,MCP_ENVIRONMENT=STAGING,MCP_GCP_PROJECT_ID=box-magique-gp-prod,MCP_GCP_REGION=us-central1,MCP_CLOUD_RUN_SERVICE=mcp-memory-proxy,MCP_WEB_ALLOWED_DOMAINS=developers.google.com;cloud.google.com;googleapis.dev,MCP_WEB_QUOTA_DAILY=100,MCP_TERMINAL_QUOTA_DAILY_READ=50,MCP_TERMINAL_QUOTA_DAILY_WRITE=10,GIT_COMMIT=${SHORT_SHA},VERSION=3.0.8-phase3-complete,READ_ONLY_MODE=true,DRY_RUN_MODE=true,API_KEY=kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE,CLOUD_RUN_SERVICE=mcp-memory-proxy,LOG_LEVEL=INFO,GCP_PROJECT_ID=box-magique-gp-prod,GCP_REGION=us-central1,ENVIRONMENT=STAGING" \
    --memory=512Mi \
    --cpu=1 \
    --timeout=300s \
    --allow-unauthenticated \
    --quiet

echo ""
echo "✅ Deployment complete"
gcloud run services describe mcp-memory-proxy \
    --project=box-magique-gp-prod \
    --region=us-central1 \
    --format='table(status.url,status.latestReadyRevisionName,metadata.generation)'
