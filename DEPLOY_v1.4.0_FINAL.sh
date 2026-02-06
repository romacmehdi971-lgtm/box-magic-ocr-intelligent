#!/bin/bash
# ================================================================
# DÉPLOIEMENT OCR v1.4.0 - EXTRACTION COMPLÈTE FINALE
# ================================================================
# Correctifs :
# - Nettoyage ULTRA-ROBUSTE du texte OCR
# - Validation STRICTE des numéros de facture
# - Patterns robustes pour montants HT/TVA/TTC
# ================================================================

set -e  # Arrêter si erreur

echo "================================================================"
echo "🚀 DÉPLOIEMENT OCR v1.4.0 - EXTRACTION COMPLÈTE FINALE"
echo "================================================================"
echo ""

# ÉTAPE 1 : Mettre à jour le code local
echo "📥 ÉTAPE 1/4 : Mise à jour du code local..."
cd ~/box-magic-ocr-intelligent
git fetch origin main
git reset --hard origin/main
echo "✅ Code mis à jour (commit 0e47e4a)"
echo ""

# ÉTAPE 2 : Build Docker
echo "🔨 ÉTAPE 2/4 : Build Docker..."
gcloud builds submit \
  --project=box-magique-gp-prod \
  --tag gcr.io/box-magique-gp-prod/box-magic-ocr-intelligent:v1.4.0-final \
  --timeout=15m .
echo "✅ Build terminé !"
echo ""

# ÉTAPE 3 : Déploiement Cloud Run
echo "☁️  ÉTAPE 3/4 : Déploiement Cloud Run..."
gcloud run deploy box-magic-ocr-intelligent \
  --project=box-magique-gp-prod \
  --image=gcr.io/box-magique-gp-prod/box-magic-ocr-intelligent:v1.4.0-final \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300s \
  --max-instances=10 \
  --set-env-vars=ENABLE_RUNTIME_DIAGNOSTICS=true,OCR_READ_ONLY=true \
  --quiet
echo "✅ Déploiement terminé !"
echo ""

# ÉTAPE 4 : Afficher l'URL du service
echo "🌐 ÉTAPE 4/4 : Service URL..."
SERVICE_URL=$(gcloud run services describe box-magic-ocr-intelligent \
  --project=box-magique-gp-prod \
  --region=us-central1 \
  --format="value(status.url)")

echo ""
echo "================================================================"
echo "✅ DÉPLOIEMENT TERMINÉ AVEC SUCCÈS !"
echo "================================================================"
echo ""
echo "🌐 Service URL : ${SERVICE_URL}"
echo ""
echo "🧪 Tests à effectuer :"
echo "   1. Invoice Genspark → N° N8WY0KFA0003, Date 2026-02-04, TTC 24.99 USD"
echo "   2. Weldom/BricoDia → N° facture + HT/TVA/TTC"
echo "   3. Carrefour CB    → TTC 140.23 EUR"
echo ""
echo "📊 Logs Cloud Run :"
echo "   https://console.cloud.google.com/run/detail/us-central1/box-magic-ocr-intelligent/logs?project=box-magique-gp-prod"
echo ""
echo "================================================================"
