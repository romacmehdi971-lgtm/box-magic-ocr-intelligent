#!/bin/bash

echo "=== ANALYSE COMPLÈTE LOGS ProxyTool - Execution nx7kv ==="
echo ""

LOGS_FILE="/tmp/mcp_job_mcp-cockpit-iapf-healthcheck-nx7kv_logs.json"

echo "📊 Total logs: $(cat $LOGS_FILE | jq '. | length')"
echo ""

# Extraire TOUS les logs (textPayload ET jsonPayload)
echo "🔍 TOUS LES LOGS (chronologique inversé):"
echo "---"
cat $LOGS_FILE | jq -r '.[] | 
  if .textPayload then
    {timestamp, severity, log: .textPayload}
  elif .jsonPayload.message then
    {timestamp, severity, log: .jsonPayload.message}
  else
    {timestamp, severity, log: "N/A"}
  end' | tac

echo ""
echo "---"
echo ""

# Filtrer logs ProxyTool
echo "✅ LOGS ProxyTool UNIQUEMENT:"
echo "---"
cat $LOGS_FILE | jq -r '.[] | 
  select(.textPayload | contains("ProxyTool")) | 
  {timestamp, log: .textPayload}'

echo ""
echo "---"
echo ""

# Chercher API Key loaded
echo "🔑 API KEY STATUS:"
echo "---"
cat $LOGS_FILE | jq -r '.[] | 
  select(.textPayload | contains("API Key") or contains("MCP_PROXY")) | 
  {timestamp, log: .textPayload}'

echo ""
echo "---"
echo ""

# Chercher appels HTTP
echo "🌐 APPELS HTTP (GET/POST):"
echo "---"
cat $LOGS_FILE | jq -r '.[] | 
  select(.textPayload | contains("GET") or contains("POST") or contains("HTTP")) | 
  {timestamp, log: .textPayload}'

echo ""
echo "=== FIN ANALYSE ===" 

