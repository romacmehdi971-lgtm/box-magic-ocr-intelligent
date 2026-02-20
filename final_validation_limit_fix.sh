#!/bin/bash
set -e

TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL="https://mcp-memory-proxy-522732657254.us-central1.run.app"

echo "=== Final Validation - Limit Fix v3.1.2 ==="
echo "Service URL: ${SERVICE_URL}"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# Proof 1: /infra/whoami
echo "=== Proof 1: GET /infra/whoami ==="
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SERVICE_URL}/infra/whoami")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo "HTTP Status: ${HTTP_STATUS}"
echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
echo ""

# Proof 2: /sheets/SETTINGS?limit=10
echo "=== Proof 2: GET /sheets/SETTINGS?limit=10 ==="
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SERVICE_URL}/sheets/SETTINGS?limit=10")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo "HTTP Status: ${HTTP_STATUS}"
echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
echo ""

# Proof 3: /sheets/MEMORY_LOG?limit=5
echo "=== Proof 3: GET /sheets/MEMORY_LOG?limit=5 ==="
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SERVICE_URL}/sheets/MEMORY_LOG?limit=5")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo "HTTP Status: ${HTTP_STATUS}"
echo "$BODY" | jq '{sheet_name, row_count, data_count: (.data | length), headers, first_row: .data[0]}' 2>/dev/null || echo "$BODY"
echo ""

# Proof 4: Test with limit=1
echo "=== Proof 4: GET /sheets/SETTINGS?limit=1 ==="
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SERVICE_URL}/sheets/SETTINGS?limit=1")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo "HTTP Status: ${HTTP_STATUS}"
echo "$BODY" | jq '{row_count, data_count: (.data | length), expected: "1 row + header"}' 2>/dev/null || echo "$BODY"
echo ""

# Proof 5: Test without limit
echo "=== Proof 5: GET /sheets/SETTINGS (no limit) ==="
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SERVICE_URL}/sheets/SETTINGS")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo "HTTP Status: ${HTTP_STATUS}"
echo "$BODY" | jq '{row_count, data_count: (.data | length)}' 2>/dev/null || echo "$BODY"
echo ""

echo "=== Validation complete ==="
