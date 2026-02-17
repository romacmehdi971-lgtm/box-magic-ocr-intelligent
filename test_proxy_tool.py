#!/usr/bin/env python3
"""
Test script for MCP Proxy Tool
Tests HTTP client with X-API-Key authentication
"""
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp_cockpit.tools.proxy_tool import get_proxy_tool

def test_proxy_tool():
    """Test all proxy tool methods"""
    
    # Set API key from environment
    api_key = "kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE"
    os.environ["MCP_PROXY_API_KEY"] = api_key
    
    print("=" * 60)
    print("MCP PROXY TOOL - VALIDATION TESTS")
    print("=" * 60)
    print()
    
    # Initialize tool
    proxy = get_proxy_tool()
    print(f"✅ ProxyTool initialized")
    print(f"   Proxy URL: {proxy.proxy_url}")
    print(f"   API Key: {api_key[:10]}...{api_key[-10:]}")
    print()
    
    # Test 1: Health check
    print("TEST 1: Health check")
    result = proxy.health_check()
    print(f"   HTTP {result['http_status']}")
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   Status: {result['health'].get('status')}")
        print("   ✅ PASS")
    else:
        print(f"   Error: {result.get('error')}")
        print("   ❌ FAIL")
    print()
    
    # Test 2: List sheets
    print("TEST 2: List sheets")
    result = proxy.list_sheets()
    print(f"   HTTP {result['http_status']}")
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   Sheets count: {len(result.get('sheets', []))}")
        print(f"   First 3 sheets: {[s['name'] for s in result.get('sheets', [])[:3]]}")
        print("   ✅ PASS")
    else:
        print(f"   Error: {result.get('error')}")
        print(f"   Correlation ID: {result.get('correlation_id')}")
        print("   ❌ FAIL")
    print()
    
    # Test 3: Get sheet data (SETTINGS)
    print("TEST 3: Get sheet data (SETTINGS?limit=5)")
    result = proxy.get_sheet_data("SETTINGS", limit=5)
    print(f"   HTTP {result['http_status']}")
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   Sheet: {result.get('sheet_name')}")
        print(f"   Headers: {result.get('headers')}")
        print(f"   Row count: {result.get('row_count')}")
        print("   ✅ PASS")
    else:
        print(f"   Error: {result.get('error')}")
        print(f"   Correlation ID: {result.get('correlation_id')}")
        print("   ❌ FAIL")
    print()
    
    # Test 4: Get memory log
    print("TEST 4: Get MEMORY_LOG (limit=3)")
    result = proxy.get_memory_log(limit=3)
    print(f"   HTTP {result['http_status']}")
    print(f"   Success: {result['success']}")
    if result['success']:
        print(f"   Total entries: {result.get('total_entries')}")
        print(f"   Entries returned: {len(result.get('entries', []))}")
        if result.get('entries'):
            first_entry = result['entries'][0]
            print(f"   First entry: {first_entry.get('type')} - {first_entry.get('title', '')[:50]}")
        print("   ✅ PASS")
    else:
        print(f"   Error: {result.get('error')}")
        print(f"   Correlation ID: {result.get('correlation_id')}")
        print("   ❌ FAIL")
    print()
    
    # Test 5: Get hub status
    print("TEST 5: Get Hub status")
    result = proxy.get_hub_status()
    print(f"   HTTP {result['http_status']}")
    print(f"   Success: {result['success']}")
    if result['success']:
        status = result.get('status', {})
        print(f"   Status: {status.get('status')}")
        print(f"   Memory log entries: {status.get('memory_log_entries')}")
        print("   ✅ PASS")
    else:
        print(f"   Error: {result.get('error')}")
        print(f"   Correlation ID: {result.get('correlation_id')}")
        print("   ❌ FAIL")
    print()
    
    # Test 6: Get snapshot
    print("TEST 6: Get active snapshot")
    result = proxy.get_snapshot_active()
    print(f"   HTTP {result['http_status']}")
    print(f"   Success: {result['success']}")
    if result['success']:
        snapshot = result.get('snapshot', {})
        print(f"   Timestamp: {snapshot.get('generated_ts_iso')}")
        print(f"   Text length: {len(snapshot.get('snapshot_text', ''))} chars")
        print("   ✅ PASS")
    else:
        print(f"   Error: {result.get('error')}")
        print(f"   Correlation ID: {result.get('correlation_id')}")
        print("   ❌ FAIL")
    print()
    
    # Test 7: Invalid sheet (404 expected)
    print("TEST 7: Invalid sheet (404 expected)")
    result = proxy.get_sheet_data("NOPE", limit=1)
    print(f"   HTTP {result['http_status']}")
    print(f"   Success: {result['success']}")
    if result['http_status'] == 404:
        print(f"   Error (expected): {result.get('error')}")
        print(f"   Correlation ID: {result.get('correlation_id')}")
        print("   ✅ PASS (404 correctly returned)")
    else:
        print(f"   Expected HTTP 404, got {result['http_status']}")
        print("   ❌ FAIL")
    print()
    
    # Test 8: Invalid limit (422 expected)
    print("TEST 8: Invalid limit (422 expected)")
    result = proxy.get_sheet_data("SETTINGS", limit=0)
    print(f"   HTTP {result['http_status']}")
    print(f"   Success: {result['success']}")
    if result['http_status'] == 422:
        print(f"   Error (expected): {result.get('error')}")
        print("   ✅ PASS (422 validation error)")
    else:
        print(f"   Expected HTTP 422, got {result['http_status']}")
        print("   ❌ FAIL")
    print()
    
    print("=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_proxy_tool()
