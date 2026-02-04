#!/bin/bash
# 🎯 DEPLOY_TICKET_CB_SNIPER.sh
# Script de déploiement Cloud Shell pour TICKET CB enrichment

set -e

echo "🎯 TICKET CB SNIPER - Déploiement Cloud Run"
echo "==========================================="
echo ""

PROJECT_ID="box-magique-gp-prod"
SERVICE_NAME="box-magic-ocr-intelligent"
REGION="us-central1"
IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo "📋 Configuration:"
echo "  Project ID: ${PROJECT_ID}"
echo "  Service: ${SERVICE_NAME}"
echo "  Region: ${REGION}"
echo "  Image: ${IMAGE_TAG}"
echo ""

# Vérifier que nous sommes dans le bon répertoire
if [ ! -f "levels/ocr_level2.py" ]; then
    echo "❌ Erreur: Fichier levels/ocr_level2.py non trouvé"
    echo "   Assurez-vous d'être dans le répertoire box-magic-ocr-intelligent"
    exit 1
fi

echo "✅ Fichiers vérifiés"
echo ""

# Configurer le projet
echo "🔧 Configuration du projet GCP..."
gcloud config set project ${PROJECT_ID}
echo ""

# Build l'image avec Cloud Build
echo "🏗️  Build de l'image Docker avec Cloud Build..."
echo "   (Durée: ~5-10 minutes)"
gcloud builds submit --tag ${IMAGE_TAG} .

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors du build de l'image"
    exit 1
fi

echo ""
echo "✅ Image construite avec succès"
echo ""

# Update le service Cloud Run
echo "🚀 Mise à jour du service Cloud Run..."
gcloud run services update ${SERVICE_NAME} \
    --image ${IMAGE_TAG} \
    --region ${REGION} \
    --platform managed

if [ $? -ne 0 ]; then
    echo "❌ Erreur lors de la mise à jour du service"
    exit 1
fi

echo ""
echo "✅ Service mis à jour avec succès"
echo ""

# Récupérer l'URL du service
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo "==========================================="
echo "✅ DÉPLOIEMENT TERMINÉ"
echo "==========================================="
echo ""
echo "🌐 URL du service: ${SERVICE_URL}"
echo ""

# Tests automatiques
echo "🧪 Tests automatiques..."
echo ""

echo "Test 1: Health Check"
curl -s ${SERVICE_URL}/health | jq '.'
echo ""

echo ""
echo "📋 Tests manuels recommandés:"
echo ""
echo "# Test 2: TICKET Carrefour CB (doit être enrichi)"
echo "curl -X POST ${SERVICE_URL}/ocr \\"
echo "  -F \"file=@facture_1.pdf\" \\"
echo "  -F \"source_entreprise=auto-detect\" | jq '.fields | {mode_paiement, statut_paiement, fournisseur_siret, carte_last4}'"
echo ""
echo "# Test 3: FACTURE normale (pas d'enrichissement TICKET)"
echo "curl -X POST ${SERVICE_URL}/ocr \\"
echo "  -F \"file=@facture_2.pdf\" \\"
echo "  -F \"source_entreprise=auto-detect\" | jq '.document_type, .fields | keys'"
echo ""

echo "==========================================="
echo "✨ Prochaines étapes:"
echo ""
echo "1. Tester avec les fichiers réels (facture_1.pdf, facture_2.pdf)"
echo "2. Copier OCR__CLOUDRUN_INTEGRATION11_V2.gs dans Apps Script"
echo "3. Vérifier le mapping INDEX_GLOBAL"
echo "4. Activer en production"
echo ""
echo "📖 Documentation: PATCH_TICKET_CB_SNIPER.md"
echo "🔗 Pull Request: https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent/pull/3"
echo "==========================================="
