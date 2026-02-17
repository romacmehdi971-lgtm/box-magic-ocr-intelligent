#!/bin/bash

echo "=== MCP JOB EXECUTION LOGS (v1.1.0 - commit bf414ac) ==="
echo "Looking for ProxyTool usage and /sheets/* calls..."
echo ""

# Get logs for the latest execution
EXECUTION="mcp-cockpit-iapf-healthcheck-89sx5"

echo "📝 Execution: $EXECUTION"
echo ""

# Try to get logs (may fail due to permissions)
echo "🔍 Attempting to retrieve logs..."
gcloud logging read "resource.labels.job_name=mcp-cockpit-iapf-healthcheck AND resource.labels.location=us-central1 AND timestamp>=\"2026-02-17T22:19:00Z\"" \
  --limit=100 \
  --format='value(timestamp,severity,jsonPayload.message)' \
  --project=box-magique-gp-prod 2>&1 | head -80

