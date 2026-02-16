#!/bin/bash
#
# MCP Memory Proxy - Comprehensive Test Suite
# Date: 2026-02-15
# Tests all endpoints and validates functionality
#

set -e

# Configuration
SERVICE_URL="https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app"
SHEET_ID="1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Get auth token
echo "🔐 Getting authentication token..."
TOKEN=$(gcloud auth print-identity-token 2>/dev/null)
if [ -z "$TOKEN" ]; then
    echo -e "${RED}❌ Failed to get auth token${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Auth token obtained${NC}"
echo ""

# Test 1: Health Check (with auth)
echo "Test 1: Health Check"
echo "====================="
RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/health")
if echo "$RESPONSE" | grep -q '"status"'; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "$RESPONSE"
    ((TESTS_FAILED++))
fi
echo ""

# Test 2: Root Endpoint (with auth)
echo "Test 2: Root Endpoint"
echo "====================="
RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/")
if echo "$RESPONSE" | grep -q '"service"'; then
    echo -e "${GREEN}✅ Root endpoint passed${NC}"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Root endpoint failed${NC}"
    echo "$RESPONSE"
    ((TESTS_FAILED++))
fi
echo ""

# Test 3: List Sheets (requires auth)
echo "Test 3: List Sheets"
echo "==================="
RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/sheets")
if echo "$RESPONSE" | grep -q '"spreadsheet_id"'; then
    echo -e "${GREEN}✅ List sheets passed${NC}"
    SHEET_COUNT=$(echo "$RESPONSE" | jq -r '.total_sheets' 2>/dev/null || echo "unknown")
    echo "Total sheets: $SHEET_COUNT"
    echo "$RESPONSE" | jq '.sheets[0:3]' 2>/dev/null || echo "$RESPONSE"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ List sheets failed${NC}"
    echo "$RESPONSE"
    ((TESTS_FAILED++))
fi
echo ""

# Test 4: Get MEMORY_LOG Sheet (requires auth)
echo "Test 4: Get MEMORY_LOG Sheet"
echo "============================="
RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/sheets/MEMORY_LOG?limit=5")
if echo "$RESPONSE" | grep -q '"sheet_name"'; then
    echo -e "${GREEN}✅ Get MEMORY_LOG passed${NC}"
    ROW_COUNT=$(echo "$RESPONSE" | jq -r '.row_count' 2>/dev/null || echo "unknown")
    echo "Row count: $ROW_COUNT (limited to 5)"
    echo "$RESPONSE" | jq '.data[0:2]' 2>/dev/null || echo "$RESPONSE"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Get MEMORY_LOG failed${NC}"
    echo "$RESPONSE"
    ((TESTS_FAILED++))
fi
echo ""

# Test 5: Create Proposal (requires auth)
echo "Test 5: Create Memory Entry Proposal"
echo "====================================="
TIMESTAMP=$(date +%s)
PROPOSAL_DATA='{
  "entry_type": "DECISION",
  "title": "Test Proposal - Auto-generated",
  "details": "Automated test proposal created by test suite at timestamp: '"$TIMESTAMP"'",
  "source": "TEST_SUITE",
  "tags": ["test", "automated", "validation"]
}'

RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "$PROPOSAL_DATA" \
  "${SERVICE_URL}/propose")

if echo "$RESPONSE" | grep -q '"proposal_id"'; then
    echo -e "${GREEN}✅ Create proposal passed${NC}"
    PROPOSAL_ID=$(echo "$RESPONSE" | jq -r '.proposal_id' 2>/dev/null || echo "unknown")
    echo "Proposal ID: $PROPOSAL_ID"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Create proposal failed${NC}"
    echo "$RESPONSE"
    ((TESTS_FAILED++))
    PROPOSAL_ID=""
fi
echo ""

# Test 6: List Proposals (requires auth)
echo "Test 6: List Proposals"
echo "======================"
RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/proposals?status=PENDING")
if echo "$RESPONSE" | grep -q '"proposals"'; then
    echo -e "${GREEN}✅ List proposals passed${NC}"
    PENDING_COUNT=$(echo "$RESPONSE" | jq -r '.total_pending' 2>/dev/null || echo "unknown")
    echo "Pending proposals: $PENDING_COUNT"
    echo "$RESPONSE" | jq '.proposals[0:2]' 2>/dev/null || echo "$RESPONSE"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ List proposals failed${NC}"
    echo "$RESPONSE"
    ((TESTS_FAILED++))
fi
echo ""

# Test 7: Validate Proposal (requires auth)
# Only if we have a proposal ID from Test 5
if [ -n "$PROPOSAL_ID" ] && [ "$PROPOSAL_ID" != "unknown" ]; then
    echo "Test 7: Validate Proposal"
    echo "========================="
    VALIDATION_DATA='{
      "action": "approve",
      "comment": "Approved by automated test suite",
      "validator": "test_suite@automation.local"
    }'
    
    RESPONSE=$(curl -s -X POST \
      -H "Authorization: Bearer ${TOKEN}" \
      -H "Content-Type: application/json" \
      -d "$VALIDATION_DATA" \
      "${SERVICE_URL}/proposals/${PROPOSAL_ID}/validate")
    
    if echo "$RESPONSE" | grep -q '"status"'; then
        echo -e "${GREEN}✅ Validate proposal passed${NC}"
        echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ Validate proposal failed${NC}"
        echo "$RESPONSE"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${YELLOW}⚠️  Test 7: Skipped (no proposal ID from Test 5)${NC}"
fi
echo ""

# Test 8: Run Autonomous Audit (requires auth)
echo "Test 8: Run Autonomous Audit"
echo "============================="
RESPONSE=$(curl -s -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  "${SERVICE_URL}/audit")

if echo "$RESPONSE" | grep -q '"status"'; then
    echo -e "${GREEN}✅ Autonomous audit passed${NC}"
    CHANGES=$(echo "$RESPONSE" | jq -r '.changes_detected' 2>/dev/null || echo "unknown")
    echo "Changes detected: $CHANGES"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Autonomous audit failed${NC}"
    echo "$RESPONSE"
    ((TESTS_FAILED++))
fi
echo ""

# Test 9: Get Documentation (with auth)
echo "Test 9: Get Documentation"
echo "========================="
RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/docs-json")
if echo "$RESPONSE" | grep -q '"title"'; then
    echo -e "${GREEN}✅ Get documentation passed${NC}"
    ENDPOINT_COUNT=$(echo "$RESPONSE" | jq -r '.endpoints | length' 2>/dev/null || echo "unknown")
    echo "Total endpoints documented: $ENDPOINT_COUNT"
    echo "$RESPONSE" | jq '.endpoints[0:3]' 2>/dev/null || echo "$RESPONSE"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ Get documentation failed${NC}"
    echo "$RESPONSE"
    ((TESTS_FAILED++))
fi
echo ""

# Test 10: Close Day (requires auth) - COMMENTED OUT for safety
echo "Test 10: Close Day (Export Snapshot)"
echo "====================================="
echo -e "${YELLOW}⚠️  This test is COMMENTED OUT to avoid creating unnecessary exports${NC}"
echo -e "${YELLOW}⚠️  To run manually: curl -X POST -H 'Authorization: Bearer \$TOKEN' ${SERVICE_URL}/close-day${NC}"
echo ""

# Summary
echo "========================================"
echo "Test Summary"
echo "========================================"
echo -e "Tests Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Tests Failed: ${RED}${TESTS_FAILED}${NC}"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo "Total Tests: $TOTAL"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed${NC}"
    exit 1
fi
