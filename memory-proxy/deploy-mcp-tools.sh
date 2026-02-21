#!/bin/bash
# Phase 2 MCP Toolset Exposure - Deploy Script
# Date: 2026-02-20
# Objectif: Exposer endpoints Phase 2 dans MCP manifest SANS écraser les variables

set -e

echo "=== Phase 2 MCP Toolset Exposure - Deploy ==="
echo ""

# Get commit SHA
export SHORT_SHA=$(git rev-parse --short HEAD)
export NEW_VERSION="3.0.7-phase2-mcp-tools"

echo "Commit to deploy: $SHORT_SHA"
echo "New version: $NEW_VERSION"
echo ""

# Build image
echo "Step 1/3: Cloud Build..."
gcloud builds submit \
  --config=cloudbuild.yaml \
  --substitutions=SHORT_SHA=${SHORT_SHA} \
  --project=box-magique-gp-prod

echo ""
echo "Step 2/3: Deploy to Cloud Run (preserving ALL env vars)..."
echo ""

# Deploy with ALL existing env vars preserved
gcloud run deploy mcp-memory-proxy \
  --image "gcr.io/box-magique-gp-prod/mcp-memory-proxy:phase2-${SHORT_SHA}" \
  --platform managed \
  --region us-central1 \
  --project box-magique-gp-prod \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300s \
  --allow-unauthenticated \
  --service-account="mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --set-secrets="/secrets/sa-key.json=mcp-cockpit-sa-key:latest" \
  --set-env-vars="GOOGLE_SHEET_ID=1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ,GOOGLE_APPLICATION_CREDENTIALS=/secrets/sa-key.json,MCP_ENVIRONMENT=STAGING,MCP_GCP_PROJECT_ID=box-magique-gp-prod,MCP_GCP_REGION=us-central1,MCP_CLOUD_RUN_SERVICE=mcp-memory-proxy,MCP_WEB_ALLOWED_DOMAINS=developers.google.com;cloud.google.com;googleapis.dev,MCP_WEB_QUOTA_DAILY=100,MCP_TERMINAL_QUOTA_DAILY_READ=50,MCP_TERMINAL_QUOTA_DAILY_WRITE=10,GIT_COMMIT=${SHORT_SHA},VERSION=${NEW_VERSION},READ_ONLY_MODE=true,DRY_RUN_MODE=true,API_KEY=kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE,CLOUD_RUN_SERVICE=mcp-memory-proxy,LOG_LEVEL=INFO"

echo ""
echo "Step 3/3: Health check & MCP manifest verification..."
echo ""

# Wait for deployment
sleep 5

# Health check
echo "Health check:"
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/health" | jq '.'

echo ""
echo "MCP Manifest check:"
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/mcp/manifest" | jq '{name, version, environment, tools_count: (.tools | length)}'

echo ""
echo "=== Deploy SUCCESS ==="
echo "Revision deployed: check Cloud Run console"
echo "MCP manifest available at: https://mcp-memory-proxy-522732657254.us-central1.run.app/mcp/manifest"
echo ""
