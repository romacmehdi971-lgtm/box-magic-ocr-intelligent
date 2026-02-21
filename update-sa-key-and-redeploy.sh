#!/bin/bash
set -e

echo "=== Phase 2 CRITICAL: Update SA Key to mcp-cockpit ==="

# Step 1: Verify the new SA key file exists
if [ ! -f "/tmp/mcp-cockpit-sa-key.json" ]; then
    echo "❌ ERROR: /tmp/mcp-cockpit-sa-key.json not found"
    echo "Please provide the service account JSON file first"
    exit 1
fi

# Step 2: Verify the client_email in the JSON
CLIENT_EMAIL=$(jq -r '.client_email' /tmp/mcp-cockpit-sa-key.json)
echo "📧 client_email found: $CLIENT_EMAIL"

if [ "$CLIENT_EMAIL" != "mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" ]; then
    echo "❌ ERROR: client_email mismatch!"
    echo "Expected: mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com"
    echo "Got: $CLIENT_EMAIL"
    exit 1
fi

# Step 3: Update the secret (new version)
echo "🔐 Updating secret mcp-cockpit-sa-key..."
gcloud secrets versions add mcp-cockpit-sa-key \
    --data-file=/tmp/mcp-cockpit-sa-key.json \
    --project=box-magique-gp-prod

echo "✅ Secret updated with new version"

# Step 4: Get current environment variables (MERGE, don't overwrite)
echo "📋 Fetching current Cloud Run environment variables..."
CURRENT_ENV=$(gcloud run services describe mcp-memory-proxy \
    --project=box-magique-gp-prod \
    --region=us-central1 \
    --format='value(spec.template.spec.containers[0].env)')

# Step 5: Parse current variables
echo "🔍 Current environment variables:"
echo "$CURRENT_ENV" | grep -E "name:|value:" | head -30

# Step 6: Redeploy Cloud Run with MERGE (preserve all existing vars)
echo "🚀 Redeploying Cloud Run service (MERGE mode, no variable overwrite)..."

# Get current image
CURRENT_IMAGE=$(gcloud run services describe mcp-memory-proxy \
    --project=box-magique-gp-prod \
    --region=us-central1 \
    --format='value(spec.template.spec.containers[0].image)')

echo "📦 Using image: $CURRENT_IMAGE"

# Redeploy with the updated secret mount (latest version)
# All env vars are preserved automatically by Cloud Run
gcloud run deploy mcp-memory-proxy \
    --project=box-magique-gp-prod \
    --region=us-central1 \
    --image="$CURRENT_IMAGE" \
    --service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
    --set-secrets="/secrets/sa-key.json=mcp-cockpit-sa-key:latest" \
    --memory=512Mi \
    --cpu=1 \
    --timeout=300s \
    --allow-unauthenticated \
    --quiet

echo ""
echo "✅ Deployment completed!"
echo ""

# Step 7: Verify the mounted secret
echo "🔍 Verifying mounted secret client_email..."
MOUNTED_EMAIL=$(gcloud run services describe mcp-memory-proxy \
    --project=box-magique-gp-prod \
    --region=us-central1 \
    --format=json | jq -r '.spec.template.metadata.annotations."run.googleapis.com/execution-environment"' || echo "checking...")

echo ""
echo "📊 Final Cloud Run status:"
gcloud run services describe mcp-memory-proxy \
    --project=box-magique-gp-prod \
    --region=us-central1 \
    --format='table(status.url,status.latestReadyRevisionName,metadata.generation)'

echo ""
echo "🎯 Next step: Verify client_email via health check"
echo "Run: curl -s https://mcp-memory-proxy-522732657254.us-central1.run.app/health | jq"
