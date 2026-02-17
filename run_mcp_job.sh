#!/bin/bash
set -e

echo "=== EXECUTING MCP JOB WITH PROXY INTEGRATION ==="
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# Execute the job
echo "🚀 Starting job execution..."
EXECUTION=$(gcloud run jobs execute mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --format='value(metadata.name)')

echo "📝 Execution: $EXECUTION"
echo ""

# Wait for completion (max 2 minutes)
echo "⏳ Waiting for job completion..."
for i in {1..24}; do
  STATUS=$(gcloud run jobs executions describe $EXECUTION \
    --region=us-central1 \
    --format='value(status.conditions[0].type)')
  
  echo "[$(date +%H:%M:%S)] Status: $STATUS"
  
  if [[ "$STATUS" == "Completed" ]]; then
    echo "✅ JOB COMPLETED"
    break
  fi
  
  sleep 5
done

echo ""
echo "📊 Final execution details:"
gcloud run jobs executions describe $EXECUTION \
  --region=us-central1 \
  --format='value(status.conditions[0].status,status.completionTime)'

echo ""
echo "💾 Execution name for logs: $EXECUTION"

