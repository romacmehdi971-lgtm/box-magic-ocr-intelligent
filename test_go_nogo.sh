#!/bin/bash
# GO/NO-GO Test - Dual Auth + 404 for missing sheets
# Date: 2026-02-17

set -e

BASE_URL="https://mcp-memory-proxy-522732657254.us-central1.run.app"
API_KEY="kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE"

echo "=========================================="
echo "GO/NO-GO VALIDATION TESTS"
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "=========================================="
echo ""

# Test GO-1: API-Key auth → 200
echo "GO-1: GET /sheets/SETTINGS?limit=1 avec X-API-Key"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" "$BASE_URL/sheets/SETTINGS?limit=1")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP $HTTP_CODE"
echo "Body (first 200 chars): $(echo "$BODY" | head -c 200)"
echo ""

# Test GO-2: API-Key auth → 200 (autre sheet)
echo "GO-2: GET /sheets/MEMORY_LOG?limit=2 avec X-API-Key"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" "$BASE_URL/sheets/MEMORY_LOG?limit=2")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP $HTTP_CODE"
echo "Body (first 200 chars): $(echo "$BODY" | head -c 200)"
echo ""

# Test GO-3: IAM token auth → 200
echo "GO-3: GET /sheets/SNAPSHOT_ACTIVE?limit=1 avec IAM token"
IAM_TOKEN=$(gcloud auth print-identity-token 2>/dev/null || echo "")
if [ -n "$IAM_TOKEN" ]; then
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $IAM_TOKEN" \
        "$BASE_URL/sheets/SNAPSHOT_ACTIVE?limit=1")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)
    echo "HTTP $HTTP_CODE"
    echo "Body (first 200 chars): $(echo "$BODY" | head -c 200)"
else
    echo "SKIP - No IAM token (gcloud not configured)"
fi
echo ""

# Test NO-GO-1: No auth → 403
echo "NO-GO-1: GET /sheets/SETTINGS?limit=1 sans auth"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/sheets/SETTINGS?limit=1")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP $HTTP_CODE (expected 403)"
echo "Body (first 200 chars): $(echo "$BODY" | head -c 200)"
CORRELATION_ID=$(echo "$BODY" | jq -r '.detail.correlation_id' 2>/dev/null || echo "N/A")
echo "Correlation ID: $CORRELATION_ID"
echo ""

# Test NO-GO-2: Invalid API-Key → 403
echo "NO-GO-2: GET /sheets/MEMORY_LOG?limit=1 avec mauvaise API-Key"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: WRONG_KEY_12345" "$BASE_URL/sheets/MEMORY_LOG?limit=1")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP $HTTP_CODE (expected 403)"
echo "Body (first 200 chars): $(echo "$BODY" | head -c 200)"
CORRELATION_ID=$(echo "$BODY" | jq -r '.detail.correlation_id' 2>/dev/null || echo "N/A")
echo "Correlation ID: $CORRELATION_ID"
echo ""

# Test NO-GO-3: Sheet inexistant → 404 (NEW)
echo "NO-GO-3: GET /sheets/NOPE?limit=1 avec X-API-Key (sheet inexistant)"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" "$BASE_URL/sheets/NOPE?limit=1")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
echo "HTTP $HTTP_CODE (expected 404, NOT 400)"
echo "Body (first 300 chars): $(echo "$BODY" | head -c 300)"
CORRELATION_ID=$(echo "$BODY" | jq -r '.detail.correlation_id' 2>/dev/null || echo "N/A")
ERROR_TYPE=$(echo "$BODY" | jq -r '.detail.error' 2>/dev/null || echo "N/A")
echo "Correlation ID: $CORRELATION_ID"
echo "Error type: $ERROR_TYPE"
echo ""

echo "=========================================="
echo "GO/NO-GO SUMMARY"
echo "GO-1 (API-Key): $([ "$HTTP_CODE" = "200" ] && echo "✅ PASS" || echo "❌ FAIL")"
echo "GO-2 (API-Key): Expected 200"
echo "GO-3 (IAM): $([ -n "$IAM_TOKEN" ] && echo "Tested" || echo "Skipped")"
echo "NO-GO-1 (No auth): Expected 403"
echo "NO-GO-2 (Bad key): Expected 403"
echo "NO-GO-3 (Missing sheet): Expected 404"
echo "=========================================="
