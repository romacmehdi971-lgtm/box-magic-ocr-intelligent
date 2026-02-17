#!/bin/bash

echo "=== VÉRIFICATION ARTIFACTS JOB MCP ==="
echo ""

# Vérifier si le job a écrit des artifacts quelque part
echo "🔍 Recherche d'artifacts du job (rapports, snapshots, audit logs)..."
echo ""

# Le job devrait écrire dans mcp_cockpit/reports/
echo "📁 Artifacts locaux (si présents):"
ls -lh mcp_cockpit/reports/ 2>&1 || echo "   Aucun artifact local (normal pour Cloud Run Job)"

echo ""
echo "💡 RAPPEL:"
echo "   Cloud Run Jobs sont éphémères et n'écrivent pas localement."
echo "   Les artifacts doivent être récupérés depuis:"
echo "   - Cloud Storage (si configuré)"
echo "   - Cloud Logging (logs applicatifs)"
echo "   - Sortie standard du job (stdout)"

echo ""
echo "🔍 Tentative de récupération stdout du job..."
gcloud run jobs executions describe mcp-cockpit-iapf-healthcheck-89sx5 \
  --region=us-central1 \
  --format='value(status.conditions[0].message)' 2>&1

