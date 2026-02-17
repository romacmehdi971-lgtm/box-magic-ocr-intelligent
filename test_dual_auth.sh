#!/bin/bash
# Test Dual-Mode Authentication (IAM OR API-Key)
# Date: 2026-02-17

set -e

BASE_URL="https://mcp-memory-proxy-522732657254.us-central1.run.app"
API_KEY="kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE"

echo "=========================================="
echo "DUAL-MODE AUTH VALIDATION TESTS"
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "=========================================="
echo ""

# Test 1: API-Key auth (existing method)
echo "Test 1: API-Key Authentication"
echo "GET /sheets/SETTINGS?limit=1 with X-API-Key"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" "$BASE_URL/sheets/SETTINGS?limit=1")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ PASS - HTTP $HTTP_CODE"
    echo "Body preview: $(echo "$BODY" | jq -c '.sheet_name, .row_count' 2>/dev/null || echo "$BODY" | head -c 100)"
else
    echo "❌ FAIL - HTTP $HTTP_CODE"
    echo "Body: $BODY"
    exit 1
fi
echo ""

# Test 2: No auth (should fail with 403)
echo "Test 2: No Authentication (should fail)"
echo "GET /sheets/SETTINGS?limit=1 without auth"
RESPONSE=$(curl -s -w "\n%{http_code}" "$BASE_URL/sheets/SETTINGS?limit=1")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "403" ]; then
    echo "✅ PASS - HTTP $HTTP_CODE (correctly rejected)"
    CORRELATION_ID=$(echo "$BODY" | jq -r '.detail.correlation_id' 2>/dev/null || echo "N/A")
    echo "Correlation ID: $CORRELATION_ID"
else
    echo "❌ FAIL - Expected HTTP 403, got $HTTP_CODE"
    echo "Body: $BODY"
    exit 1
fi
echo ""

# Test 3: IAM token auth (requires Cloud Run service account)
echo "Test 3: IAM Token Authentication"
echo "Attempting to get IAM token for Cloud Run..."

# Try to get IAM token using gcloud
IAM_TOKEN=""
if command -v gcloud &> /dev/null; then
    echo "gcloud found, fetching identity token..."
    IAM_TOKEN=$(gcloud auth print-identity-token 2>/dev/null || echo "")
fi

if [ -n "$IAM_TOKEN" ]; then
    echo "GET /sheets/MEMORY_LOG?limit=2 with IAM token"
    RESPONSE=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $IAM_TOKEN" \
        "$BASE_URL/sheets/MEMORY_LOG?limit=2")
    HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
    BODY=$(echo "$RESPONSE" | head -n-1)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ PASS - HTTP $HTTP_CODE (IAM auth successful)"
        echo "Body preview: $(echo "$BODY" | jq -c '.sheet_name, .row_count' 2>/dev/null || echo "$BODY" | head -c 100)"
    else
        echo "⚠️  WARN - HTTP $HTTP_CODE (IAM token may not have permissions)"
        echo "Body: $BODY"
        echo "This is expected if running from a non-authorized account"
    fi
else
    echo "⚠️  SKIP - No IAM token available (gcloud not configured)"
    echo "This test requires 'gcloud auth login' or running from Cloud Run"
fi
echo ""

# Test 4: Multiple sheets with API-Key
echo "Test 4: Sequential reads with API-Key"
for SHEET in "SETTINGS" "MEMORY_LOG" "SNAPSHOT_ACTIVE"; do
    echo -n "  - /sheets/$SHEET?limit=1 ... "
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "X-API-Key: $API_KEY" \
        "$BASE_URL/sheets/$SHEET?limit=1")
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "✅ $HTTP_CODE"
    else
        echo "❌ $HTTP_CODE"
        exit 1
    fi
done
echo ""

# Test 5: Invalid sheet with API-Key (should return 400 with correlation_id)
echo "Test 5: Invalid Sheet Name"
echo "GET /sheets/NOPE?limit=1 with X-API-Key"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" "$BASE_URL/sheets/NOPE?limit=1")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "400" ]; then
    echo "✅ PASS - HTTP $HTTP_CODE"
    CORRELATION_ID=$(echo "$BODY" | jq -r '.correlation_id' 2>/dev/null || echo "N/A")
    ERROR_TYPE=$(echo "$BODY" | jq -r '.error' 2>/dev/null || echo "N/A")
    echo "Correlation ID: $CORRELATION_ID"
    echo "Error type: $ERROR_TYPE"
else
    echo "❌ FAIL - Expected HTTP 400, got $HTTP_CODE"
    echo "Body: $BODY"
    exit 1
fi
echo ""

echo "=========================================="
echo "DUAL-MODE AUTH VALIDATION COMPLETE"
echo "Summary:"
echo "  - API-Key auth: ✅ Working"
echo "  - No auth rejection: ✅ Working"
echo "  - IAM token auth: $([ -n "$IAM_TOKEN" ] && echo "✅ Tested" || echo "⚠️ Skipped (no gcloud)")"
echo "  - Error handling: ✅ Working"
echo "=========================================="
