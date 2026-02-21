#!/bin/bash

SERVICE_URL="https://mcp-memory-proxy-522732657254.us-central1.run.app"

echo "=========================================="
echo "PHASE 3 - 6 PREUVES CURL"
echo "=========================================="
echo ""

# Wait for service to be ready
sleep 5

echo "📋 Preuve 3: Cloud Logging Query"
echo "=========================================="
curl -s -X POST "$SERVICE_URL/cloud-logging/query" \
  -H "Content-Type: application/json" \
  -d '{
    "filter_str": "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"mcp-memory-proxy\"",
    "time_range_hours": 1,
    "limit": 5
  }' | jq '{ok, run_id, total_entries, filter}'

echo ""
echo ""

echo "📋 Preuve 4: Secrets List"
echo "=========================================="
curl -s "$SERVICE_URL/secrets/list?limit=5" | jq '{ok, run_id, total_secrets, secrets: (.secrets | map({name, create_time}))}'

echo ""
echo ""

echo "📋 Preuve 5: Secret Reference"
echo "=========================================="
curl -s "$SERVICE_URL/secrets/mcp-cockpit-sa-key/reference?version=latest" | jq '{ok, run_id, secret_id, version, state, value_provided, value}'

echo ""
echo ""

echo "📋 Preuve 6: Secret Create DRY_RUN"
echo "=========================================="
curl -s -X POST "$SERVICE_URL/secrets/create" \
  -H "Content-Type: application/json" \
  -d '{
    "secret_id": "test-secret-phase3-dryrun",
    "value": "test-value-123-phase3",
    "mode": "DRY_RUN"
  }' | jq '{ok, run_id, mode, result: {mode: .result.mode, action: .result.action, would_create: .result.would_create, actual_created: .result.actual_created, governance_note: .result.governance_note}}'

echo ""
echo ""

echo "📋 Manifest Check"
echo "=========================================="
curl -s "$SERVICE_URL/mcp/manifest" | jq '{name, version, environment, tools_count}'

echo ""
echo ""

echo "📋 Health Check"
echo "=========================================="
curl -s "$SERVICE_URL/health" | jq '{status, version}'

echo ""
echo "=========================================="
echo "✅ 6 PREUVES CURL COMPLÉTÉES"
echo "=========================================="
