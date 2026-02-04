#!/bin/bash
# BOX MAGIC OCR INTELLIGENT - Cloud Run Deployment Script
# Usage: ./deploy.sh [PROJECT_ID] [REGION] [SERVICE_NAME]

set -e  # Exit on error

# Configuration
PROJECT_ID="${1:-your-gcp-project-id}"
REGION="${2:-europe-west1}"
SERVICE_NAME="${3:-box-magic-ocr-intelligent}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=========================================="
echo "BOX MAGIC OCR INTELLIGENT - Deployment"
echo "=========================================="
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service Name: ${SERVICE_NAME}"
echo "Image: ${IMAGE_NAME}"
echo "=========================================="

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI not found. Please install it first."
    exit 1
fi

# Authenticate if needed
echo "📋 Checking authentication..."
gcloud auth application-default print-access-token > /dev/null 2>&1 || {
    echo "🔐 Authentication required..."
    gcloud auth login
}

# Set project
echo "🔧 Setting project..."
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo "🔌 Enabling required APIs..."
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Build image
echo "🏗️  Building Docker image..."
gcloud builds submit --tag ${IMAGE_NAME} .

echo "✅ Image built successfully: ${IMAGE_NAME}"

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 1 \
    --timeout 300 \
    --max-instances 10 \
    --set-env-vars "ENABLE_RUNTIME_DIAGNOSTICS=true"

echo "=========================================="
echo "✅ Deployment completed successfully!"
echo "=========================================="

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Test endpoints:"
echo "  Health check: ${SERVICE_URL}/health"
echo "  Root: ${SERVICE_URL}/"
echo "  OCR: ${SERVICE_URL}/ocr (POST)"
echo "=========================================="
