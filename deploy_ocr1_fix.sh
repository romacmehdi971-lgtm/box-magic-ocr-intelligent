#!/bin/bash
set -e

PROJECT_ID="box-magique-gp-prod"
REGION="us-central1"
SERVICE_NAME="box-magic-ocr-intelligent"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:ocr1-fix-$(date +%Y%m%d-%H%M%S)"

echo "=========================================="
echo "🔧 OCR1 FIX DEPLOYMENT"
echo "=========================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo "Image: ${IMAGE_NAME}"
echo "Commit: $(git rev-parse --short HEAD)"
echo "=========================================="

# Build & push image
echo "🏗️  Building image..."
gcloud builds submit --project=${PROJECT_ID} --tag ${IMAGE_NAME} .

echo "✅ Image built: ${IMAGE_NAME}"

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
  --project=${PROJECT_ID} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --set-env-vars "ENABLE_RUNTIME_DIAGNOSTICS=true,OCR_READ_ONLY=true"

echo "=========================================="
echo "✅ DEPLOYMENT COMPLETE"
echo "=========================================="

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --project=${PROJECT_ID} --region ${REGION} --format 'value(status.url)')
echo "Service URL: ${SERVICE_URL}"
echo "Health check: ${SERVICE_URL}/health"
echo "=========================================="
