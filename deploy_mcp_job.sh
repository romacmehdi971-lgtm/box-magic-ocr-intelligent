#!/bin/bash
set -e

echo "=== DEPLOYING MCP JOB WITH PROXY INTEGRATION ==="
echo ""
echo "📦 Image: gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0"
echo "🔐 Digest: sha256:3f94debfdc606e6c3f0bceec9078578c4187e8f64ccb5258533a7582583724c8"
echo "🏷️  Git commit: bf414ac"
echo ""

# Deploy Cloud Run Job
gcloud run jobs deploy mcp-cockpit-iapf-healthcheck \
  --image=gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0 \
  --region=us-central1 \
  --service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
  --set-env-vars="MCP_PROXY_API_KEY=kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE,ENVIRONMENT=PROD,USE_METADATA_AUTH=true" \
  --max-retries=0 \
  --task-timeout=600s \
  --memory=512Mi \
  --cpu=1

echo ""
echo "✅ Job deployed successfully"
echo ""

# Verify deployment
echo "📋 Job configuration:"
gcloud run jobs describe mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --format='value(metadata.name,metadata.labels,spec.template.spec.containers[0].image)'

echo ""
echo "🔍 Environment variables (masked):"
gcloud run jobs describe mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --format='value(spec.template.spec.containers[0].env)' | \
  grep -E "(MCP_PROXY_API_KEY|ENVIRONMENT|USE_METADATA_AUTH)" | \
  sed 's/kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE/**MASKED**/'

