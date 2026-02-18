#!/bin/bash
set -euo pipefail

echo "=== APPEL DIRECT ProxyTool /sheets/SETTINGS?limit=10 ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# Récupérer l'API Key depuis le job déployé
API_KEY=$(gcloud run jobs describe mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod \
  --format="value(spec.template.spec.containers[0].env[0].value)" 2>/dev/null | head -1)

if [ -z "$API_KEY" ]; then
  echo "❌ API Key not found in job config"
  exit 1
fi

PROXY_URL="https://mcp-memory-proxy-522732657254.us-central1.run.app"

echo "📡 Calling: $PROXY_URL/sheets/SETTINGS?limit=10"
echo "🔑 API Key: ${API_KEY:0:10}... (masked)"
echo ""

# Faire l'appel
RESPONSE=$(curl -s -w "\n%{http_code}" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  "$PROXY_URL/sheets/SETTINGS?limit=10")

# Séparer le body et le status code
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n -1)

echo "📊 HTTP STATUS: $HTTP_CODE"
echo ""
echo "📝 RESPONSE BODY:"
echo "$BODY" | jq '.'
echo ""

# Extraire les infos clés
ROW_COUNT=$(echo "$BODY" | jq -r '.row_count // empty')
HEADERS=$(echo "$BODY" | jq -r '.headers // empty')

echo "✅ VALIDATION:"
echo "  - HTTP Code: $HTTP_CODE"
echo "  - Row Count: $ROW_COUNT"
echo "  - Headers: $HEADERS"
echo ""

# Test NOPE aussi pour compléter
echo "=== APPEL DIRECT ProxyTool /sheets/NOPE?limit=1 ==="
RESPONSE_NOPE=$(curl -s -w "\n%{http_code}" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  "$PROXY_URL/sheets/NOPE?limit=1")

HTTP_CODE_NOPE=$(echo "$RESPONSE_NOPE" | tail -n1)
BODY_NOPE=$(echo "$RESPONSE_NOPE" | head -n -1)

echo "📊 HTTP STATUS: $HTTP_CODE_NOPE"
echo ""
echo "📝 RESPONSE BODY:"
echo "$BODY_NOPE" | jq '.'
echo ""

CORRELATION_ID=$(echo "$BODY_NOPE" | jq -r '.correlation_id // empty')

echo "✅ VALIDATION:"
echo "  - HTTP Code: $HTTP_CODE_NOPE"
echo "  - Correlation ID: $CORRELATION_ID"

