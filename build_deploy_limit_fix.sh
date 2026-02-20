#!/bin/bash
set -e

VERSION="v3.1.2-limit-fix"
PROJECT_ID="box-magique-gp-prod"
REGION="us-central1"
SERVICE_NAME="mcp-memory-proxy"
IMAGE="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${VERSION}"
GIT_COMMIT=$(git rev-parse --short HEAD)

echo "=== Building MCP Memory Proxy ${VERSION} ==="
echo "Git commit: ${GIT_COMMIT}"

# Build and push
cd memory-proxy
docker build --platform linux/amd64 -t "${IMAGE}" .
docker push "${IMAGE}"

echo "=== Deploying to Cloud Run ==="
gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE}" \
  --region="${REGION}" \
  --platform=managed \
  --allow-unauthenticated \
  --set-env-vars="VERSION=${VERSION},GIT_COMMIT=${GIT_COMMIT}" \
  --timeout=60 \
  --memory=512Mi \
  --cpu=1 \
  --max-instances=10

echo "=== Deployment complete ==="
gcloud run services describe "${SERVICE_NAME}" --region="${REGION}" --format="value(status.url)"
