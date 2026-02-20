#!/bin/bash
set -e

BASE_URL="https://mcp-memory-proxy-522732657254.us-central1.run.app"
API_KEY="kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "=================================================="
echo "TESTS DIRECTS BACKEND (sans cockpit MCP)"
echo "Timestamp: $TS"
echo "Base URL: $BASE_URL"
echo "=================================================="
echo ""

# Test 1: /infra/whoami
echo "TEST 1: GET /infra/whoami"
echo "----------------------------------------"
RESPONSE=$(curl -sS -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/infra/whoami")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

echo "HTTP Code: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: SUCCESS"
    echo "Response body:"
    echo "$BODY" | jq -C '.'
    echo ""
    echo "Version:" $(echo "$BODY" | jq -r '.version')
    echo "Revision:" $(echo "$BODY" | jq -r '.revision // "null"')
    echo "Config flags:" $(echo "$BODY" | jq -c '.config')
else
    echo "❌ Status: FAIL (HTTP $HTTP_CODE)"
    echo "Response body:"
    echo "$BODY"
fi
echo ""

# Test 2: /sheets/SETTINGS?limit=1
echo "TEST 2: GET /sheets/SETTINGS?limit=1"
echo "----------------------------------------"
RESPONSE=$(curl -sS -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/sheets/SETTINGS?limit=1" -H "X-API-Key: $API_KEY")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

echo "HTTP Code: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: SUCCESS"
    echo "Sheet name:" $(echo "$BODY" | jq -r '.sheet_name')
    echo "Row count:" $(echo "$BODY" | jq -r '.row_count')
    echo "Data count:" $(echo "$BODY" | jq -r '.data | length')
    echo "Data preview (first row):"
    echo "$BODY" | jq -C '.data[0]'
else
    echo "❌ Status: FAIL (HTTP $HTTP_CODE)"
    echo "Response body:"
    echo "$BODY" | jq -C '.'
fi
echo ""

# Test 3: /sheets/MEMORY_LOG?limit=5
echo "TEST 3: GET /sheets/MEMORY_LOG?limit=5"
echo "----------------------------------------"
RESPONSE=$(curl -sS -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/sheets/MEMORY_LOG?limit=5" -H "X-API-Key: $API_KEY")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

echo "HTTP Code: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: SUCCESS"
    echo "Sheet name:" $(echo "$BODY" | jq -r '.sheet_name')
    echo "Row count:" $(echo "$BODY" | jq -r '.row_count')
    echo "Data count:" $(echo "$BODY" | jq -r '.data | length')
    echo "First entry type:" $(echo "$BODY" | jq -r '.data[0].type // "N/A"')
else
    echo "❌ Status: FAIL (HTTP $HTTP_CODE)"
    echo "Response body:"
    echo "$BODY" | jq -C '.'
fi
echo ""

# Test 4: /sheets/DRIVE_INVENTORY?limit=10
echo "TEST 4: GET /sheets/DRIVE_INVENTORY?limit=10"
echo "----------------------------------------"
RESPONSE=$(curl -sS -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/sheets/DRIVE_INVENTORY?limit=10" -H "X-API-Key: $API_KEY")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

echo "HTTP Code: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: SUCCESS"
    echo "Sheet name:" $(echo "$BODY" | jq -r '.sheet_name')
    echo "Row count:" $(echo "$BODY" | jq -r '.row_count')
    echo "Data count:" $(echo "$BODY" | jq -r '.data | length')
else
    echo "❌ Status: FAIL (HTTP $HTTP_CODE)"
    echo "Response body:"
    echo "$BODY" | jq -C '.'
fi
echo ""

# Test 5: /sheets/SETTINGS (sans limit, pour comparaison)
echo "TEST 5: GET /sheets/SETTINGS (sans limit, pour comparaison)"
echo "----------------------------------------"
RESPONSE=$(curl -sS -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/sheets/SETTINGS" -H "X-API-Key: $API_KEY")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

echo "HTTP Code: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: SUCCESS"
    echo "Sheet name:" $(echo "$BODY" | jq -r '.sheet_name')
    echo "Row count:" $(echo "$BODY" | jq -r '.row_count')
    echo "Data count:" $(echo "$BODY" | jq -r '.data | length')
    echo "(devrait retourner toutes les lignes disponibles)"
else
    echo "❌ Status: FAIL (HTTP $HTTP_CODE)"
    echo "Response body:"
    echo "$BODY" | jq -C '.'
fi
echo ""

# Test 6: /docs-json pour vérifier le contract
echo "TEST 6: GET /docs-json (vérifier présence /infra/whoami)"
echo "----------------------------------------"
RESPONSE=$(curl -sS -w "\nHTTP_CODE:%{http_code}" "$BASE_URL/docs-json")
HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")

echo "HTTP Code: $HTTP_CODE"
if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Status: SUCCESS"
    WHOAMI_FOUND=$(echo "$BODY" | jq -r '.endpoints[] | select(.path=="/infra/whoami") | .path')
    if [ -n "$WHOAMI_FOUND" ]; then
        echo "✅ /infra/whoami trouvé dans le contract"
        echo "$BODY" | jq -C '.endpoints[] | select(.path=="/infra/whoami")'
    else
        echo "❌ /infra/whoami NON TROUVÉ dans le contract"
    fi
else
    echo "❌ Status: FAIL (HTTP $HTTP_CODE)"
fi
echo ""

echo "=================================================="
echo "FIN DES TESTS DIRECTS"
echo "=================================================="
