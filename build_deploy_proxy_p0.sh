#!/bin/bash
set -euo pipefail

echo "╔══════════════════════════════════════════════════════════════════════════════╗"
echo "║           🔨 BUILD & DEPLOY PROXY P0 - Infrastructure + Memory Writer        ║"
echo "╚══════════════════════════════════════════════════════════════════════════════╝"
echo ""
echo "📅 Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "🔖 Version: v3.1.0-p0"
echo "📦 Project: box-magique-gp-prod"
echo ""

PROJECT="box-magique-gp-prod"
REGION="us-central1"
SERVICE="mcp-memory-proxy"
IMAGE_NAME="gcr.io/${PROJECT}/${SERVICE}:v3.1.0-p0"
GIT_COMMIT=$(git rev-parse --short HEAD)

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ÉTAPE 1: BUILD DOCKER IMAGE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🐳 Building: $IMAGE_NAME"
echo "📝 Git commit: $GIT_COMMIT"
echo ""

cd memory-proxy

# Build with Cloud Build
gcloud builds submit \
  --tag="$IMAGE_NAME" \
  --project="$PROJECT" \
  --timeout=10m \
  --substitutions="_GIT_COMMIT=$GIT_COMMIT,_VERSION=v3.1.0-p0" \
  .

cd ..

echo ""
echo "✅ Build complete"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ÉTAPE 2: DEPLOY TO CLOUD RUN"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🚀 Deploying to: $REGION/$SERVICE"
echo ""

# Get current env vars
GOOGLE_SHEET_ID=$(gcloud run services describe "$SERVICE" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format="value(spec.template.spec.containers[0].env[?(@.name=='GOOGLE_SHEET_ID')].value)" 2>/dev/null || echo "")

API_KEY=$(gcloud run services describe "$SERVICE" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format="value(spec.template.spec.containers[0].env[?(@.name=='API_KEY')].value)" 2>/dev/null || echo "")

# Deploy new revision
gcloud run services update "$SERVICE" \
  --image="$IMAGE_NAME" \
  --region="$REGION" \
  --project="$PROJECT" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --timeout=60s \
  --concurrency=80 \
  --max-instances=10 \
  --set-env-vars="ENVIRONMENT=production,API_VERSION=v3.1.0-p0,BUILD_VERSION=v3.1.0-p0,GIT_COMMIT_SHA=$GIT_COMMIT,LOG_LEVEL=INFO,GOOGLE_SHEET_ID=$GOOGLE_SHEET_ID,API_KEY=$API_KEY" \
  --service-account="mcp-cockpit@${PROJECT}.iam.gserviceaccount.com"

echo ""
echo "✅ Deployment complete"
echo ""

# Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format="value(status.url)")

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "ÉTAPE 3: VERIFY DEPLOYMENT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🌐 Service URL: $SERVICE_URL"
echo ""

# Get revision info
REVISION=$(gcloud run services describe "$SERVICE" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format="value(status.latestReadyRevisionName)")

echo "📦 Latest revision: $REVISION"
echo ""

# Get image digest
IMAGE_DIGEST=$(gcloud run revisions describe "$REVISION" \
  --region="$REGION" \
  --project="$PROJECT" \
  --format="value(spec.containers[0].image)" | grep -oP 'sha256:\S+' || echo "unknown")

echo "🔐 Image digest: $IMAGE_DIGEST"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 DEPLOYMENT SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Service: $SERVICE"
echo "Region: $REGION"
echo "Version: v3.1.0-p0"
echo "Commit: $GIT_COMMIT"
echo "Image: $IMAGE_NAME"
echo "Image Digest: $IMAGE_DIGEST"
echo "Revision: $REVISION"
echo "URL: $SERVICE_URL"
echo ""
echo "✅ P0 endpoints added:"
echo "   - GET /infra/whoami"
echo "   - POST /infra/logs/query"
echo "   - GET /infra/cloudrun/services"
echo "   - GET /infra/cloudrun/jobs"
echo "   - GET /infra/cloudrun/job/{name}/executions"
echo "   - POST /hub/memory_log/write"
echo ""
echo "📝 Next: Run validation tests"
echo ""

