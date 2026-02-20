#!/bin/bash
# Build and Deploy MCP Memory Proxy - Phase 2 Complete
# Date: 2026-02-20

set -e

# Configuration
PROJECT_ID="box-magique-gp-prod"
REGION="us-central1"
SERVICE_NAME="mcp-memory-proxy"
GIT_COMMIT=$(git rev-parse --short HEAD)
IMAGE_TAG="phase2-${GIT_COMMIT}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}"
IMAGE_LATEST="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "=========================================="
echo "MCP Memory Proxy - Phase 2 Deployment"
echo "=========================================="
echo "Project ID:     ${PROJECT_ID}"
echo "Region:         ${REGION}"
echo "Service:        ${SERVICE_NAME}"
echo "Git Commit:     ${GIT_COMMIT}"
echo "Image Tag:      ${IMAGE_TAG}"
echo "=========================================="

# Step 1: Build Docker image
echo ""
echo "Step 1/4: Building Docker image..."
docker build \
  --platform linux/amd64 \
  --build-arg GIT_COMMIT=${GIT_COMMIT} \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  -t ${IMAGE_NAME} \
  -t ${IMAGE_LATEST} \
  .

if [ $? -ne 0 ]; then
  echo "❌ Docker build failed"
  exit 1
fi
echo "✅ Docker image built successfully"

# Step 2: Push to Google Container Registry
echo ""
echo "Step 2/4: Pushing image to GCR..."
docker push ${IMAGE_NAME}
docker push ${IMAGE_LATEST}

if [ $? -ne 0 ]; then
  echo "❌ Docker push failed"
  exit 1
fi
echo "✅ Image pushed to GCR"

# Step 3: Deploy to Cloud Run
echo ""
echo "Step 3/4: Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --service-account mcp-proxy@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-env-vars "\
GOOGLE_CLOUD_PROJECT=${PROJECT_ID},\
GCP_PROJECT_ID=${PROJECT_ID},\
GCP_REGION=${REGION},\
MCP_ENVIRONMENT=STAGING,\
MCP_GCP_PROJECT_ID=${PROJECT_ID},\
MCP_GCP_REGION=${REGION},\
MCP_CLOUD_RUN_SERVICE=${SERVICE_NAME},\
MCP_WEB_ALLOWED_DOMAINS=googleapis.com;github.com;genspark.ai,\
MCP_WEB_QUOTA_DAILY=100,\
MCP_TERMINAL_QUOTA_DAILY_READ=50,\
MCP_TERMINAL_QUOTA_DAILY_WRITE=10,\
READ_ONLY_MODE=false,\
DRY_RUN_MODE=false" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --min-instances 0

if [ $? -ne 0 ]; then
  echo "❌ Cloud Run deployment failed"
  exit 1
fi
echo "✅ Deployed to Cloud Run"

# Step 4: Verify deployment
echo ""
echo "Step 4/4: Verifying deployment..."
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --format 'value(status.url)')

echo ""
echo "Testing /health endpoint..."
HEALTH_RESPONSE=$(curl -s "${SERVICE_URL}/health")
echo "Health Response: ${HEALTH_RESPONSE}"

echo ""
echo "Testing /openapi.json endpoint..."
OPENAPI_RESPONSE=$(curl -s "${SERVICE_URL}/openapi.json" | jq -r '.info.version, .paths | keys | length')
echo "OpenAPI Response: ${OPENAPI_RESPONSE}"

echo ""
echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE"
echo "=========================================="
echo "Service URL:    ${SERVICE_URL}"
echo "Git Commit:     ${GIT_COMMIT}"
echo "Image:          ${IMAGE_NAME}"
echo "Health:         ${SERVICE_URL}/health"
echo "OpenAPI:        ${SERVICE_URL}/openapi.json"
echo "Docs:           ${SERVICE_URL}/docs"
echo "=========================================="
echo ""
echo "Phase 2 Endpoints Available:"
echo "  - /drive/tree"
echo "  - /drive/file/{id}/metadata"
echo "  - /drive/search"
echo "  - /apps-script/project/{id}/deployments"
echo "  - /apps-script/project/{id}/structure"
echo "  - /cloud-run/service/{name}/status"
echo "  - /cloud-logging/query"
echo "  - /secrets/list"
echo "  - /secrets/{id}/reference"
echo "  - /secrets/create"
echo "  - /secrets/{id}/rotate"
echo "  - /web/search"
echo "  - /web/fetch"
echo "  - /terminal/run"
echo "=========================================="
