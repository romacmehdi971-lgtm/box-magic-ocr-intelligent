#!/bin/bash
set -e

# Get IAM token
TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL="https://mcp-memory-proxy-522732657254.us-central1.run.app"
REVISION="mcp-memory-proxy-00014-5f5"

# Test the new revision directly
REVISION_URL="https://${REVISION}---mcp-memory-proxy-522732657254.us-central1.run.app"

echo "=== Testing new revision ${REVISION} ==="
echo "Revision URL: ${REVISION_URL}"
echo ""

# Test 1: /sheets/SETTINGS?limit=10
echo "=== Test 1: GET /sheets/SETTINGS?limit=10 ==="
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${REVISION_URL}/sheets/SETTINGS?limit=10")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo "HTTP Status: ${HTTP_STATUS}"
echo "Response:"
echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
echo ""

# Test 2: /sheets/MEMORY_LOG?limit=5
echo "=== Test 2: GET /sheets/MEMORY_LOG?limit=5 ==="
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${REVISION_URL}/sheets/MEMORY_LOG?limit=5")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo "HTTP Status: ${HTTP_STATUS}"
echo "Response:"
echo "$BODY" | jq '{row_count: .row_count, data_count: (.data | length)}' 2>/dev/null || echo "$BODY"
echo ""

# Test 3: /infra/whoami (verify version)
echo "=== Test 3: GET /infra/whoami ==="
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${REVISION_URL}/infra/whoami")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo "HTTP Status: ${HTTP_STATUS}"
echo "Response:"
echo "$BODY" | jq '{version: .version, revision_name: .revision_name, image_digest: .image_digest}' 2>/dev/null || echo "$BODY"
echo ""

echo "=== All tests completed ==="
