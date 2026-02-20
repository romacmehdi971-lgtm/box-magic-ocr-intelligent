#!/bin/bash
set -e

echo "════════════════════════════════════════════════════════════════════════════"
echo "  DIAGNOSTIC DE COHÉRENCE - MCP MEMORY PROXY"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""
echo "Timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# Get IAM token
TOKEN=$(gcloud auth print-identity-token)

# Liste des URLs potentielles
URLS=(
  "https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app"
  "https://mcp-memory-proxy-522732657254.us-central1.run.app"
)

echo "════════════════════════════════════════════════════════════════════════════"
echo "  1. IDENTIFICATION DU SERVICE CLOUD RUN"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

# Get service details
gcloud run services describe mcp-memory-proxy \
  --region=us-central1 \
  --format="table(
    metadata.name,
    status.url,
    status.traffic[0].revisionName,
    status.traffic[0].percent,
    spec.template.spec.serviceAccountName
  )" 2>&1 | head -20

echo ""
echo "--- Révision servante (100% traffic) ---"
ACTIVE_REVISION=$(gcloud run services describe mcp-memory-proxy \
  --region=us-central1 \
  --format="value(status.traffic[0].revisionName)" 2>&1)
echo "Révision: ${ACTIVE_REVISION}"

echo ""
echo "--- Image de la révision active ---"
IMAGE=$(gcloud run revisions describe "${ACTIVE_REVISION}" \
  --region=us-central1 \
  --format="value(spec.containers[0].image)" 2>&1)
echo "Image: ${IMAGE}"

echo ""
echo "--- Digest de l'image ---"
if [[ "${IMAGE}" =~ ^gcr\.io/.* ]]; then
  DIGEST=$(gcloud container images describe "${IMAGE}" \
    --format="value(image_summary.digest)" 2>&1 | grep -v "WARNING" || echo "digest-non-récupérable")
  echo "Digest: ${DIGEST}"
else
  echo "Image non GCR, digest non récupérable"
fi

echo ""
echo "--- Variables d'environnement ---"
gcloud run revisions describe "${ACTIVE_REVISION}" \
  --region=us-central1 \
  --format="table(spec.containers[0].env)" 2>&1 | head -20

echo ""
echo "════════════════════════════════════════════════════════════════════════════"
echo "  2. TESTS API SUR CHAQUE URL POTENTIELLE"
echo "════════════════════════════════════════════════════════════════════════════"
echo ""

for SERVICE_URL in "${URLS[@]}"; do
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  URL: ${SERVICE_URL}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  
  # Test GET /
  echo "--- GET / (root) ---"
  RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -H "Authorization: Bearer ${TOKEN}" \
    "${SERVICE_URL}/" 2>&1 || echo "CURL_ERROR")
  HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2 || echo "000")
  BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d' | head -10)
  echo "Status: ${HTTP_STATUS}"
  echo "${BODY}"
  echo ""
  
  # Test GET /health
  echo "--- GET /health ---"
  RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -H "Authorization: Bearer ${TOKEN}" \
    "${SERVICE_URL}/health" 2>&1 || echo "CURL_ERROR")
  HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2 || echo "000")
  BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
  echo "Status: ${HTTP_STATUS}"
  echo "${BODY}" | jq '.' 2>/dev/null || echo "${BODY}"
  echo ""
  
  # Test GET /docs-json
  echo "--- GET /docs-json (aperçu) ---"
  RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -H "Authorization: Bearer ${TOKEN}" \
    "${SERVICE_URL}/docs-json" 2>&1 || echo "CURL_ERROR")
  HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2 || echo "000")
  BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
  echo "Status: ${HTTP_STATUS}"
  if [ "${HTTP_STATUS}" = "200" ]; then
    echo "${BODY}" | jq '{info: .info, paths: (.paths | keys)}' 2>/dev/null || echo "${BODY}" | head -20
  else
    echo "${BODY}" | head -10
  fi
  echo ""
  
  # Test GET /infra/whoami
  echo "--- GET /infra/whoami ---"
  RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -H "Authorization: Bearer ${TOKEN}" \
    "${SERVICE_URL}/infra/whoami" 2>&1 || echo "CURL_ERROR")
  HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2 || echo "000")
  BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
  echo "Status: ${HTTP_STATUS}"
  echo "${BODY}" | jq '.' 2>/dev/null || echo "${BODY}"
  echo ""
  
  # Test GET /openapi.json
  echo "--- GET /openapi.json ---"
  RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    -H "Authorization: Bearer ${TOKEN}" \
    "${SERVICE_URL}/openapi.json" 2>&1 || echo "CURL_ERROR")
  HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS:" | cut -d: -f2 || echo "000")
  echo "Status: ${HTTP_STATUS}"
  if [ "${HTTP_STATUS}" = "200" ]; then
    BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS:/d')
    echo "${BODY}" | jq '{info: .info, paths: (.paths | keys)}' 2>/dev/null || echo "${BODY}" | head -20
  fi
  echo ""
  
done

echo "════════════════════════════════════════════════════════════════════════════"
echo "  FIN DU DIAGNOSTIC"
echo "════════════════════════════════════════════════════════════════════════════"
