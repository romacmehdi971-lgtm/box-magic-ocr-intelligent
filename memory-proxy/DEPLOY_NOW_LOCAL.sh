#!/bin/bash
# DÉPLOIEMENT IMMÉDIAT Phase 2 - Exécuter sur votre machine locale
# Ce script utilise vos credentials gcloud déjà configurés

set -e

PROJECT_ID="box-magique-gp-prod"
REGION="us-central1"
SERVICE_NAME="mcp-memory-proxy"

cd "$(dirname "$0")"

echo "🚀 Déploiement Phase 2 - START"
echo "Project: ${PROJECT_ID}"
echo "Service: ${SERVICE_NAME}"
echo "Region: ${REGION}"

# Obtenir le commit
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "a548b88")
IMAGE_TAG="phase2-${GIT_COMMIT}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}"

echo "Git Commit: ${GIT_COMMIT}"
echo "Image: ${IMAGE_NAME}"

# Build
echo ""
echo "📦 Step 1/3: Building Docker image..."
docker build --platform linux/amd64 -t "${IMAGE_NAME}" . || {
  echo "❌ Build failed"
  exit 1
}
echo "✅ Build OK"

# Push
echo ""
echo "⬆️  Step 2/3: Pushing to GCR..."
docker push "${IMAGE_NAME}" || {
  echo "❌ Push failed"
  exit 1
}
echo "✅ Push OK"

# Deploy
echo ""
echo "☁️  Step 3/3: Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_NAME}" \
  --platform managed \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --set-env-vars "MCP_ENVIRONMENT=STAGING,MCP_GCP_PROJECT_ID=${PROJECT_ID},MCP_GCP_REGION=${REGION},MCP_CLOUD_RUN_SERVICE=${SERVICE_NAME},READ_ONLY_MODE=false" || {
  echo "❌ Deploy failed"
  exit 1
}
echo "✅ Deploy OK"

# Verify
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --project "${PROJECT_ID}" --format 'value(status.url)')

echo ""
echo "🔍 Verification..."
echo "Service URL: ${SERVICE_URL}"

sleep 3

echo ""
echo "Testing /health..."
curl -s "${SERVICE_URL}/health" | jq '.' || echo "Health check failed"

echo ""
echo "Testing /openapi.json (routes count)..."
ROUTES_COUNT=$(curl -s "${SERVICE_URL}/openapi.json" | jq '.paths | keys | length')
echo "Routes available: ${ROUTES_COUNT}"

echo ""
echo "=========================================="
echo "✅ DÉPLOIEMENT TERMINÉ"
echo "=========================================="
echo "Commit déployé: ${GIT_COMMIT}"
echo "Image: ${IMAGE_NAME}"
echo "Service URL: ${SERVICE_URL}"
echo "Health: ${SERVICE_URL}/health"
echo "OpenAPI: ${SERVICE_URL}/openapi.json"
echo "Docs: ${SERVICE_URL}/docs"
echo "=========================================="
