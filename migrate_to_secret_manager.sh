#!/bin/bash
set -e

echo "=== MIGRATION MCP_PROXY_API_KEY → SECRET MANAGER ==="
echo "Date: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo ""

# Configuration
PROJECT="box-magique-gp-prod"
SECRET_NAME="mcp-proxy-api-key"
API_KEY="kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE"

echo "📦 Projet: $PROJECT"
echo "🔐 Secret: $SECRET_NAME"
echo "🔑 API Key: ***MASKED*** (43 chars)"
echo ""

# Étape 1: Vérifier si le secret existe déjà
echo "🔍 Vérification existence du secret..."
if gcloud secrets describe $SECRET_NAME --project=$PROJECT 2>/dev/null; then
    echo "✅ Secret '$SECRET_NAME' existe déjà"
    echo ""
    echo "📋 Détails du secret existant:"
    gcloud secrets describe $SECRET_NAME --project=$PROJECT
else
    echo "❌ Secret '$SECRET_NAME' n'existe pas - tentative de création..."
    echo ""
    
    # Étape 2: Créer le secret
    echo "🔐 Création du secret '$SECRET_NAME'..."
    echo -n "$API_KEY" | gcloud secrets create $SECRET_NAME \
        --data-file=- \
        --replication-policy=automatic \
        --project=$PROJECT 2>&1 || {
        
        echo ""
        echo "❌ ERREUR: Impossible de créer le secret"
        echo "   Raison probable: Permission 'secretmanager.secrets.create' manquante"
        echo ""
        echo "💡 SOLUTION (Admin GCP):"
        echo "   1. Créer le secret manuellement via Console:"
        echo "      https://console.cloud.google.com/security/secret-manager?project=$PROJECT"
        echo ""
        echo "   2. OU via gcloud (avec compte admin):"
        echo "      echo -n '$API_KEY' | gcloud secrets create $SECRET_NAME \\"
        echo "        --data-file=- \\"
        echo "        --replication-policy=automatic \\"
        echo "        --project=$PROJECT"
        echo ""
        exit 1
    }
fi

echo ""
echo "---"
echo ""

# Étape 3: Donner accès au service account MCP
echo "🔐 Configuration accès service account..."
SA_MCP="mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com"

echo "📝 Ajout de $SA_MCP comme Secret Accessor..."
gcloud secrets add-iam-policy-binding $SECRET_NAME \
    --member="serviceAccount:$SA_MCP" \
    --role="roles/secretmanager.secretAccessor" \
    --project=$PROJECT 2>&1 || {
    
    echo ""
    echo "⚠️  Avertissement: Impossible d'ajouter la permission IAM"
    echo "   Raison probable: Permission 'secretmanager.secrets.setIamPolicy' manquante"
    echo ""
    echo "💡 SOLUTION (Admin GCP):"
    echo "   gcloud secrets add-iam-policy-binding $SECRET_NAME \\"
    echo "     --member=\"serviceAccount:$SA_MCP\" \\"
    echo "     --role=\"roles/secretmanager.secretAccessor\" \\"
    echo "     --project=$PROJECT"
}

echo ""
echo "✅ Migration Secret Manager terminée"

