#!/bin/bash

echo "=== ANALYSE DES PERMISSIONS ==="
echo ""

# Service account actuel
SA=$(gcloud config get-value account)
echo "🔑 Service Account actuel:"
echo "   $SA"
echo ""

# Vérifier les IAM bindings du projet
echo "📋 Rôles IAM du service account:"
gcloud projects get-iam-policy box-magique-gp-prod \
  --flatten="bindings[].members" \
  --filter="bindings.members:$SA" \
  --format="table(bindings.role)" 2>&1 | head -20

echo ""
echo "⚠️  PERMISSIONS REQUISES MANQUANTES:"
echo "   - logging.logEntries.list (pour gcloud logging read)"
echo "   - logging.logs.list (pour lister les logs)"
echo ""
echo "💡 SOLUTION:"
echo "   Ajouter le rôle 'roles/logging.viewer' au service account:"
echo ""
echo "   gcloud projects add-iam-policy-binding box-magique-gp-prod \\"
echo "     --member=\"serviceAccount:$SA\" \\"
echo "     --role=\"roles/logging.viewer\""

