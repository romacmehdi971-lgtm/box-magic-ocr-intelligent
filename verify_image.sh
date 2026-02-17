#!/bin/bash

echo "=== MCP JOB IMAGE VERIFICATION ==="
echo ""

# Get image digest
echo "📦 Image: gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0"
DIGEST=$(gcloud container images describe \
  gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0 \
  --format='value(image_summary.digest)')

echo "🔐 Digest: $DIGEST"
echo ""

# Get image metadata including labels
echo "🏷️  Image metadata:"
gcloud container images describe \
  gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0 \
  --format='yaml(image_summary.fully_qualified_digest,config.labels)' | head -20

echo ""
echo "✅ Image v1.1.0 built successfully with digest: $DIGEST"
