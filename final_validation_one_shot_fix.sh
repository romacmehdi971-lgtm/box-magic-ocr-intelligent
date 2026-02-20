#!/bin/bash
set -e
BASE_URL="https://mcp-memory-proxy-522732657254.us-central1.run.app"
API_KEY="kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "🔍 VALIDATION FINALE – v3.1.4-one-shot-fix – $TS"
echo ""
echo "=========================================="
echo "1) TEST VERSION CONSISTENCY"
echo "=========================================="
echo "✅ Test 1.1: GET / (root)"
curl -sS "$BASE_URL/" | jq -c '{service, version, status}' || echo "❌ FAIL"

echo ""
echo "✅ Test 1.2: GET /health"
curl -sS "$BASE_URL/health" | jq -c '{status, version}' || echo "❌ FAIL"

echo ""
echo "✅ Test 1.3: GET /infra/whoami (new P0 endpoint)"
curl -sS "$BASE_URL/infra/whoami" | jq -c '{version, revision, config: {read_only_mode, enable_actions, dry_run_mode}}' || echo "❌ FAIL"

echo ""
echo "✅ Test 1.4: GET /docs-json (contract includes /infra/whoami)"
DOCS=$(curl -sS "$BASE_URL/docs-json")
echo "$DOCS" | jq -r '.version' 
echo "$DOCS" | jq -r '.endpoints[] | select(.path=="/infra/whoami") | "✅ /infra/whoami found in docs-json"' || echo "❌ /infra/whoami MISSING from docs-json"

echo ""
echo "=========================================="
echo "2) TEST PAGINATION (LIMIT QUERY)"
echo "=========================================="
echo "✅ Test 2.1: GET /sheets/SETTINGS?limit=1"
curl -sS "$BASE_URL/sheets/SETTINGS?limit=1" \
  -H "X-API-Key: $API_KEY" | jq -c '{sheet_name, row_count, data_count: (.data|length)}' || echo "❌ FAIL"

echo ""
echo "✅ Test 2.2: GET /sheets/MEMORY_LOG?limit=5"
curl -sS "$BASE_URL/sheets/MEMORY_LOG?limit=5" \
  -H "X-API-Key: $API_KEY" | jq -c '{sheet_name, row_count, data_count: (.data|length)}' || echo "❌ FAIL"

echo ""
echo "✅ Test 2.3: GET /sheets/DRIVE_INVENTORY?limit=10"
curl -sS "$BASE_URL/sheets/DRIVE_INVENTORY?limit=10" \
  -H "X-API-Key: $API_KEY" | jq -c '{sheet_name, row_count, data_count: (.data|length)}' || echo "❌ FAIL"

echo ""
echo "✅ Test 2.4: GET /gpt/memory-log?limit=5"
curl -sS "$BASE_URL/gpt/memory-log?limit=5" \
  -H "X-API-Key: $API_KEY" | jq -c '{sheet, total_entries}' || echo "❌ FAIL"

echo ""
echo "=========================================="
echo "3) TEST READ_ONLY_MODE ENFORCEMENT"
echo "=========================================="
echo "✅ Test 3.1: POST /propose (should be blocked by middleware)"
RESPONSE=$(curl -sS -X POST "$BASE_URL/propose" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"entry_type":"DECISION","title":"Test","details":"Test"}')
echo "$RESPONSE" | jq -c 'if .detail | contains("disabled") or .detail | contains("READ_ONLY") then {status: "✅ BLOCKED", detail} else {status: "❌ NOT BLOCKED", detail} end'

echo ""
echo "=========================================="
echo "4) DEPLOYMENT INFO"
echo "=========================================="
gcloud run services describe mcp-memory-proxy --region=us-central1 --format="value(status.latestReadyRevisionName)" | xargs -I {} echo "Revision: {}"
gcloud run services describe mcp-memory-proxy --region=us-central1 --format="value(spec.template.spec.containers[0].image)" | xargs -I {} echo "Image: {}"

echo ""
echo "=========================================="
echo "✅ VALIDATION COMPLETED – $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "=========================================="
