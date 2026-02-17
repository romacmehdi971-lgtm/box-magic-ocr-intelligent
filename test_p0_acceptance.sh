#!/bin/bash
set -e

API_KEY="kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE"
BASE_URL="https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app"

echo "=== P0 ACCEPTANCE TESTS ==="
echo ""

echo "Test 1: OpenAPI Schema Public Access"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/openapi.json")
if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ GET /openapi.json → HTTP $HTTP_CODE (sans auth)"
else
  echo "❌ GET /openapi.json → HTTP $HTTP_CODE (ÉCHEC)"
  exit 1
fi
echo ""

echo "Test 2: OpenAPI Structure Validation"
SPEC=$(curl -s "$BASE_URL/openapi.json")
SERVER_URL=$(echo "$SPEC" | jq -r '.servers[0].url')
AUTH_TYPE=$(echo "$SPEC" | jq -r '.components.securitySchemes.APIKeyHeader.type')
AUTH_NAME=$(echo "$SPEC" | jq -r '.components.securitySchemes.APIKeyHeader.name')
GPT_PATHS=$(echo "$SPEC" | jq -r '.paths | keys[] | select(startswith("/gpt"))' | wc -l)

echo "  Server URL: $SERVER_URL"
echo "  Auth Type: $AUTH_TYPE"
echo "  Auth Header: $AUTH_NAME"
echo "  GPT Endpoints: $GPT_PATHS"

if [ "$SERVER_URL" = "$BASE_URL" ] && [ "$AUTH_TYPE" = "apiKey" ] && [ "$AUTH_NAME" = "X-API-Key" ] && [ "$GPT_PATHS" -ge 3 ]; then
  echo "✅ Structure OpenAPI valide"
else
  echo "❌ Structure OpenAPI invalide"
  exit 1
fi
echo ""

echo "Test 3: Endpoint /gpt/hub-status"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" "$BASE_URL/gpt/hub-status")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
STATUS=$(echo "$BODY" | jq -r '.status' 2>/dev/null)

if [ "$HTTP_CODE" = "200" ] && [ "$STATUS" = "healthy" ]; then
  echo "✅ GET /gpt/hub-status → HTTP $HTTP_CODE, status=$STATUS"
else
  echo "❌ GET /gpt/hub-status → HTTP $HTTP_CODE (ÉCHEC)"
  exit 1
fi
echo ""

echo "Test 4: Endpoint /gpt/snapshot-active"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: $API_KEY" "$BASE_URL/gpt/snapshot-active")
if [ "$HTTP_CODE" = "200" ]; then
  echo "✅ GET /gpt/snapshot-active → HTTP $HTTP_CODE"
else
  echo "❌ GET /gpt/snapshot-active → HTTP $HTTP_CODE (ÉCHEC)"
  exit 1
fi
echo ""

echo "Test 5: Endpoint /gpt/memory-log?limit=10"
RESPONSE=$(curl -s -w "\n%{http_code}" -H "X-API-Key: $API_KEY" "$BASE_URL/gpt/memory-log?limit=10")
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)
ENTRY_COUNT=$(echo "$BODY" | jq '.entries | length' 2>/dev/null)

if [ "$HTTP_CODE" = "200" ] && [ "$ENTRY_COUNT" -ge 1 ]; then
  echo "✅ GET /gpt/memory-log?limit=10 → HTTP $HTTP_CODE, entries=$ENTRY_COUNT"
else
  echo "❌ GET /gpt/memory-log?limit=10 → HTTP $HTTP_CODE (ÉCHEC)"
  exit 1
fi
echo ""

echo "=== RÉSULTAT FINAL ==="
echo "🟢 TOUS LES TESTS P0 PASSÉS"
echo ""
echo "Spec Canon OpenAPI: $BASE_URL/openapi.json"
echo "Backend Version: v2.0.0"
echo "Status: GO PRODUCTION"
