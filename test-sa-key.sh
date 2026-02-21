#!/bin/bash
# Quick test to verify the mounted SA key

echo "=== Testing mounted SA key ==="
echo ""

# Test via a simple curl to check if the service can read the mounted key
echo "1️⃣ Health check:"
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/health" | jq -r '.status, .version'

echo ""
echo "2️⃣ Testing Drive metadata endpoint (will reveal if SA key is correctly mounted):"
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/drive/file/1LwUZ67zVstl2tuogcdYYihPilUAXQai3/metadata" | jq -r 'if .detail then "❌ ERROR: " + .detail else "✅ SUCCESS: " + .name + " (mimeType: " + .mimeType + ")" end'

echo ""
echo "3️⃣ MCP Manifest check:"
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/mcp/manifest" | jq -r '.name, .version, .environment, ("Tools: " + (.tools_count | tostring))'

echo ""
echo "✅ Tests completed"
