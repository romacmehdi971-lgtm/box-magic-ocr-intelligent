#!/bin/bash
set -e

echo "=== MCP JOB IMAGE BUILD (Cloud Build) ==="
echo "Commit: bf414ac"
echo "Image: gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0"
echo ""

# Create cloudbuild.yaml for MCP job
cat > cloudbuild_mcp.yaml << 'EOF'
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-f'
      - 'mcp_cockpit/Dockerfile.job'
      - '-t'
      - 'gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0'
      - '--label'
      - 'git_commit=bf414ac'
      - '.'
images:
  - 'gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0'
timeout: 1200s
EOF

# Submit build
gcloud builds submit \
  --config=cloudbuild_mcp.yaml \
  --project=box-magique-gp-prod

echo ""
echo "✅ Build completed. Verifying image..."

# Verify image exists
gcloud container images describe \
  gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0 \
  --format='value(image_summary.digest)'
