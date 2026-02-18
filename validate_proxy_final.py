#!/usr/bin/env python3
"""
VALIDATION FINALE ORION - ProxyTool /sheets/SETTINGS?limit=10
Date: 2026-02-18T00:44:30Z
"""
import json
import os
from mcp_cockpit.tools.proxy_tool import ProxyTool

def main():
    print("=" * 70)
    print("VALIDATION FINALE - ProxyTool /sheets/SETTINGS?limit=10")
    print("=" * 70)
    print()
    
    # Initialiser ProxyTool
    proxy = ProxyTool()
    
    # TEST 1: GET /sheets/SETTINGS?limit=10
    print("📡 TEST 1: GET /sheets/SETTINGS?limit=10")
    print("-" * 70)
    result = proxy.get_sheet_data("SETTINGS", limit=10)
    
    print(f"✅ Success: {result['success']}")
    print(f"📊 HTTP Status: {result['http_status']}")
    print(f"🔢 Row Count: {result.get('body', {}).get('row_count', 'N/A')}")
    print()
    print("📝 HEADERS:")
    headers = result.get('body', {}).get('headers', [])
    print(f"   {headers}")
    print()
    print("📦 BODY COMPLET:")
    print(json.dumps(result.get('body', {}), indent=2, ensure_ascii=False))
    print()
    print("=" * 70)
    print()
    
    # TEST 2: GET /sheets/NOPE?limit=1 (404 expected)
    print("📡 TEST 2: GET /sheets/NOPE?limit=1 (404 attendu)")
    print("-" * 70)
    result_nope = proxy.get_sheet_data("NOPE", limit=1)
    
    print(f"❌ Success: {result_nope['success']}")
    print(f"📊 HTTP Status: {result_nope['http_status']}")
    print(f"🔗 Correlation ID: {result_nope.get('correlation_id', 'N/A')}")
    print(f"⚠️  Error: {result_nope.get('error', 'N/A')}")
    print()
    print("📦 BODY COMPLET:")
    print(json.dumps(result_nope.get('body', {}), indent=2, ensure_ascii=False))
    print()
    print("=" * 70)
    print()
    
    # SYNTHÈSE
    print("✅ SYNTHÈSE VALIDATION ORION")
    print("=" * 70)
    print(f"✓ ProxyTool initialized: {proxy.proxy_url}")
    print(f"✓ GET /sheets/SETTINGS?limit=10 → HTTP {result['http_status']}")
    print(f"✓ Row count: {result.get('body', {}).get('row_count', 'N/A')}")
    print(f"✓ GET /sheets/NOPE?limit=1 → HTTP {result_nope['http_status']}")
    print(f"✓ Correlation ID: {result_nope.get('correlation_id', 'N/A')}")
    print()
    print("🎯 CRITÈRES ORION:")
    print(f"   [{'✓' if result['http_status'] == 200 else '✗'}] HTTP 200 sur SETTINGS")
    print(f"   [{'✓' if result.get('body', {}).get('row_count') == 8 else '✗'}] row_count = 8")
    print(f"   [{'✓' if result_nope['http_status'] == 404 else '✗'}] HTTP 404 sur NOPE")
    print(f"   [{'✓' if result_nope.get('correlation_id') else '✗'}] correlation_id présent")
    print()
    print("=" * 70)

if __name__ == "__main__":
    # Set env vars
    os.environ["PROXY_URL"] = "https://mcp-memory-proxy-522732657254.us-central1.run.app"
    os.environ["MCP_PROXY_API_KEY"] = "kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE"
    
    main()
