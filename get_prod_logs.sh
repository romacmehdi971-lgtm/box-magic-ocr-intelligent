#!/bin/bash

echo "=== TENTATIVE RÉCUPÉRATION LOGS PRODUCTION ==="
echo "Job: mcp-cockpit-iapf-healthcheck"
echo "Execution: mcp-cockpit-iapf-healthcheck-89sx5"
echo "Date: 2026-02-17T22:18:30Z → 2026-02-17T22:25:00Z"
echo ""

# Commande exacte demandée
echo "🔍 Exécution commande gcloud logging read..."
gcloud logging read \
  "resource.labels.job_name=mcp-cockpit-iapf-healthcheck AND \
   resource.labels.location=us-central1 AND \
   timestamp>=\"2026-02-17T22:18:30Z\"" \
  --limit=200 \
  --format=json \
  --project=box-magique-gp-prod 2>&1 | tee /tmp/gcloud_logs_output.txt

echo ""
echo "📊 Résultat de la commande:"
cat /tmp/gcloud_logs_output.txt | head -50

