#!/bin/bash
set -e

echo "════════════════════════════════════════════════════════════════════════════"
echo "  TESTS DIRECTS ENDPOINTS AVEC ?limit="
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL="https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app"

echo "URL de test: ${SERVICE_URL}"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# Test 1: /sheets/SETTINGS?limit=1
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 1: GET /sheets/SETTINGS?limit=1"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SERVICE_URL}/sheets/SETTINGS?limit=1" 2>&1)
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
echo "Status HTTP: ${HTTP_STATUS}"
if [ "${HTTP_STATUS}" = "200" ]; then
  echo "${BODY}" | jq '{sheet_name, row_count, data_count: (.data | length)}' 2>/dev/null || echo "${BODY}"
else
  echo "ERREUR:"
  echo "${BODY}" | head -20
fi
echo ""

# Test 2: /sheets/MEMORY_LOG?limit=5
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 2: GET /sheets/MEMORY_LOG?limit=5"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SERVICE_URL}/sheets/MEMORY_LOG?limit=5" 2>&1)
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
echo "Status HTTP: ${HTTP_STATUS}"
if [ "${HTTP_STATUS}" = "200" ]; then
  echo "${BODY}" | jq '{sheet_name, row_count, data_count: (.data | length)}' 2>/dev/null || echo "${BODY}"
else
  echo "ERREUR:"
  echo "${BODY}" | head -20
fi
echo ""

# Test 3: /sheets/DRIVE_INVENTORY?limit=10
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 3: GET /sheets/DRIVE_INVENTORY?limit=10"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SERVICE_URL}/sheets/DRIVE_INVENTORY?limit=10" 2>&1)
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
echo "Status HTTP: ${HTTP_STATUS}"
if [ "${HTTP_STATUS}" = "200" ]; then
  echo "${BODY}" | jq '{sheet_name, row_count, data_count: (.data | length)}' 2>/dev/null || echo "${BODY}"
else
  echo "ERREUR:"
  echo "${BODY}" | head -20
fi
echo ""

# Test 4: /gpt/memory_log?limit=3 (alternative endpoint)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 4: GET /gpt/memory-log?limit=3"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SERVICE_URL}/gpt/memory-log?limit=3" 2>&1)
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
echo "Status HTTP: ${HTTP_STATUS}"
if [ "${HTTP_STATUS}" = "200" ]; then
  echo "${BODY}" | jq 'if type == "object" then {count: (.entries | length)} else {type: type} end' 2>/dev/null || echo "${BODY}" | head -20
else
  echo "ERREUR:"
  echo "${BODY}" | head -20
fi
echo ""

# Test 5: Sans limit pour comparaison
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 5: GET /sheets/SETTINGS (sans limit)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SERVICE_URL}/sheets/SETTINGS" 2>&1)
HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
echo "Status HTTP: ${HTTP_STATUS}"
if [ "${HTTP_STATUS}" = "200" ]; then
  echo "${BODY}" | jq '{sheet_name, row_count, data_count: (.data | length)}' 2>/dev/null || echo "${BODY}"
else
  echo "ERREUR:"
  echo "${BODY}" | head -20
fi
echo ""

echo "════════════════════════════════════════════════════════════════════════════"
