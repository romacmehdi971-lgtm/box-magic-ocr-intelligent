#!/bin/bash
set -e

echo "=== RÉCUPÉRATION LOGS PRODUCTION - VALIDATION FINALE ORION ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# Information job
echo "📦 Job: mcp-cockpit-iapf-healthcheck"
echo "🔍 Execution: mcp-cockpit-iapf-healthcheck-89sx5"
echo "⏰ Période: 2026-02-17T22:19:00Z → 2026-02-17T22:22:00Z"
echo ""

# Tentative 1: Récupération logs avec filtre ProxyTool
echo "🔍 Tentative 1: Logs contenant 'ProxyTool'..."
gcloud logging read \
  "resource.type=\"cloud_run_job\" AND \
   resource.labels.job_name=\"mcp-cockpit-iapf-healthcheck\" AND \
   resource.labels.location=\"us-central1\" AND \
   timestamp>=\"2026-02-17T22:19:00Z\" AND \
   timestamp<=\"2026-02-17T22:22:00Z\" AND \
   jsonPayload.message=~\"ProxyTool\"" \
  --limit=50 \
  --format=json \
  --project=box-magique-gp-prod 2>&1 | tee /tmp/logs_proxytool.json

echo ""
echo "📊 Analyse logs ProxyTool:"
cat /tmp/logs_proxytool.json | jq -r '.[] | select(.jsonPayload.message) | 
  {timestamp: .timestamp, message: .jsonPayload.message}' 2>/dev/null || \
  echo "❌ Erreur permission ou format JSON invalide"

echo ""
echo "---"
echo ""

# Tentative 2: Logs contenant '/sheets/SETTINGS'
echo "🔍 Tentative 2: Logs contenant '/sheets/SETTINGS'..."
gcloud logging read \
  "resource.type=\"cloud_run_job\" AND \
   resource.labels.job_name=\"mcp-cockpit-iapf-healthcheck\" AND \
   timestamp>=\"2026-02-17T22:19:00Z\" AND \
   jsonPayload.message=~\"/sheets/SETTINGS\"" \
  --limit=20 \
  --format=json \
  --project=box-magique-gp-prod 2>&1 | tee /tmp/logs_settings.json

echo ""
echo "📊 Analyse logs SETTINGS:"
cat /tmp/logs_settings.json | jq -r '.[] | select(.jsonPayload.message) | 
  {timestamp: .timestamp, message: .jsonPayload.message}' 2>/dev/null || \
  echo "❌ Erreur permission ou format JSON invalide"

echo ""
echo "---"
echo ""

# Tentative 3: Logs contenant 'HTTP 200' ou 'HTTP 404'
echo "🔍 Tentative 3: Logs contenant 'HTTP 200' ou 'HTTP 404'..."
gcloud logging read \
  "resource.type=\"cloud_run_job\" AND \
   resource.labels.job_name=\"mcp-cockpit-iapf-healthcheck\" AND \
   timestamp>=\"2026-02-17T22:19:00Z\" AND \
   (jsonPayload.message=~\"HTTP 200\" OR jsonPayload.message=~\"HTTP 404\")" \
  --limit=20 \
  --format=json \
  --project=box-magique-gp-prod 2>&1 | tee /tmp/logs_http.json

echo ""
echo "📊 Analyse logs HTTP:"
cat /tmp/logs_http.json | jq -r '.[] | select(.jsonPayload.message) | 
  {timestamp: .timestamp, message: .jsonPayload.message}' 2>/dev/null || \
  echo "❌ Erreur permission ou format JSON invalide"

echo ""
echo "=== FIN TENTATIVE RÉCUPÉRATION LOGS ==="

