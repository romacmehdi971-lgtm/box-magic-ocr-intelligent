#!/bin/bash
set -e

echo "════════════════════════════════════════════════════════════════════════════"
echo "  VALIDATION FINALE - AUDIT-SAFE v3.1.3"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

TOKEN=$(gcloud auth print-identity-token)
SERVICE_URL="https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app"

echo "Service URL: ${SERVICE_URL}"
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# PROOF 1: Version alignment
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PROOF 1: Version alignment across all endpoints"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo "GET /"
curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/" | jq '.version'

echo "GET /health"
curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/health" | jq '.version'

echo "GET /docs-json"
curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/docs-json" | jq '.version'

echo "GET /openapi.json"
curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/openapi.json" | jq '.info.version'

echo "GET /infra/whoami"
curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/infra/whoami" | jq '.version'

echo ""

# PROOF 2: Audit-safe flags
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PROOF 2: Audit-safe flags exposed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/whoami" | jq '.config'

echo ""

# PROOF 3: docs-json contract (GET only)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PROOF 3: docs-json contract (READ-ONLY endpoints only)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/docs-json" | jq '.endpoints[] | {method, path}'

echo ""

# PROOF 4: READ_ONLY_MODE enforcement (try POST)
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PROOF 4: READ_ONLY_MODE enforcement (POST blocked)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
  -X POST \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}' \
  "${SERVICE_URL}/propose" 2>&1)

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2)
BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')

echo "POST /propose → Status: ${HTTP_STATUS}"
echo "${BODY}" | jq '.'

echo ""

# PROOF 5: limit still works
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "PROOF 5: limit functionality (no regression)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

curl -s -H "Authorization: Bearer ${TOKEN}" "${SERVICE_URL}/sheets/SETTINGS?limit=2" | jq '{sheet_name, row_count, data_count: (.data | length)}'

echo ""

# Image digest
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "DEPLOYMENT INFO"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

REVISION=$(gcloud run services describe mcp-memory-proxy --region=us-central1 --format="value(status.traffic[0].revisionName)")
echo "Active revision: ${REVISION}"

IMAGE=$(gcloud run revisions describe "${REVISION}" --region=us-central1 --format="value(spec.containers[0].image)")
echo "Image: ${IMAGE}"

if [[ "${IMAGE}" =~ sha256:([a-f0-9]+) ]]; then
  DIGEST="${BASH_REMATCH[1]}"
  echo "Digest: sha256:${DIGEST}"
else
  echo "Digest: (extracting...)"
  gcloud container images describe "${IMAGE}" --format="value(image_summary.digest)" 2>&1 | grep -v WARNING
fi

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
