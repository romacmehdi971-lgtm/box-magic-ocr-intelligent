#!/bin/bash
set -euo pipefail

echo "=== EXTRACTION BODY COMPLET /sheets/SETTINGS ==="
echo ""

# Lire le fichier JSON complet
jq -r '.[] | 
  select(.timestamp >= "2026-02-18T00:41:04.476Z" and .timestamp <= "2026-02-18T00:41:05.000Z") |
  {
    timestamp: .timestamp,
    severity: .severity,
    message: (.jsonPayload.message // .textPayload),
    full_json: .jsonPayload
  }' /tmp/all_logs_k6hrg.json | jq -s '.'

echo ""
echo "=== RECHERCHE BODY DANS LES LOGS ==="

# Chercher dans tout le fichier des entrées avec "data" ou "body"
jq -r '.[] | 
  select(
    (.jsonPayload | tostring) | test("row_count|headers|data|body")
  ) |
  {
    timestamp: .timestamp,
    payload: .jsonPayload
  }' /tmp/all_logs_k6hrg.json | jq -s '.'

