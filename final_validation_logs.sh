#!/bin/bash
set -e

echo "=== RÉCUPÉRATION LOGS PRODUCTION - VALIDATION FINALE ORION ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

PROJECT="box-magique-gp-prod"
JOB_NAME="mcp-cockpit-iapf-healthcheck"
EXECUTION="mcp-cockpit-iapf-healthcheck-89sx5"

echo "📦 Job: $JOB_NAME"
echo "🔍 Execution: $EXECUTION"
echo "⏰ Période: 2026-02-17T22:19:00Z → 2026-02-17T22:22:00Z"
echo ""

# Récupérer TOUS les logs du job execution
echo "🔍 Récupération logs complète du job execution..."
gcloud logging read \
  "resource.type=\"cloud_run_job\" AND \
   resource.labels.job_name=\"$JOB_NAME\" AND \
   resource.labels.location=\"us-central1\" AND \
   timestamp>=\"2026-02-17T22:19:00Z\" AND \
   timestamp<=\"2026-02-17T22:22:00Z\"" \
  --limit=300 \
  --format=json \
  --project=$PROJECT \
  > /tmp/mcp_job_89sx5_full_logs.json

echo "✅ Logs récupérés - $(cat /tmp/mcp_job_89sx5_full_logs.json | jq '. | length') entrées"
echo ""

# Analyse 1: Logs ProxyTool
echo "📊 ANALYSE 1 - Logs ProxyTool:"
echo "---"
cat /tmp/mcp_job_89sx5_full_logs.json | \
  jq -r '.[] | select(.jsonPayload.message | contains("ProxyTool")) | 
    {timestamp: .timestamp, severity: .severity, message: .jsonPayload.message}' \
  2>/dev/null | head -30

echo ""
echo "---"
echo ""

# Analyse 2: Logs /sheets/SETTINGS
echo "📊 ANALYSE 2 - Appels /sheets/SETTINGS:"
echo "---"
cat /tmp/mcp_job_89sx5_full_logs.json | \
  jq -r '.[] | select(.jsonPayload.message | contains("/sheets/SETTINGS")) | 
    {timestamp: .timestamp, message: .jsonPayload.message}' \
  2>/dev/null

echo ""
echo "---"
echo ""

# Analyse 3: HTTP 200
echo "📊 ANALYSE 3 - Réponses HTTP 200:"
echo "---"
cat /tmp/mcp_job_89sx5_full_logs.json | \
  jq -r '.[] | select(.jsonPayload.message | contains("HTTP 200")) | 
    {timestamp: .timestamp, message: .jsonPayload.message}' \
  2>/dev/null

echo ""
echo "---"
echo ""

# Analyse 4: HTTP 404
echo "📊 ANALYSE 4 - Réponses HTTP 404:"
echo "---"
cat /tmp/mcp_job_89sx5_full_logs.json | \
  jq -r '.[] | select(.jsonPayload.message | contains("HTTP 404")) | 
    {timestamp: .timestamp, message: .jsonPayload.message}' \
  2>/dev/null

echo ""
echo "---"
echo ""

# Analyse 5: correlation_id
echo "📊 ANALYSE 5 - Correlation IDs:"
echo "---"
cat /tmp/mcp_job_89sx5_full_logs.json | \
  jq -r '.[] | select(.jsonPayload.message | contains("correlation_id")) | 
    {timestamp: .timestamp, message: .jsonPayload.message}' \
  2>/dev/null | head -10

echo ""
echo "=== FIN RÉCUPÉRATION LOGS ==="
echo ""
echo "💾 Logs complets sauvegardés dans: /tmp/mcp_job_89sx5_full_logs.json"

