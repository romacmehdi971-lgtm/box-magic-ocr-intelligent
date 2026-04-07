#!/bin/bash
# ================================================================
# DÉPLOIEMENT OCR v1.5.0 - FIX CRITIQUE EXTRACTION
# ================================================================
# Correctifs :
# - FIX numéro de facture (frontière de mot)
# - FIX extraction montants (nettoyage amélioré)
# - Protection des montants pendant nettoyage
# ================================================================

set -e  # Arrêter si erreur

echo "================================================================"
echo "🚀 DÉPLOIEMENT OCR v1.5.0 - FIX CRITIQUE EXTRACTION"
echo "================================================================"
echo ""

# COMMANDE COMPLÈTE EN 1 SEULE LIGNE
cd ~/box-magic-ocr-intelligent && \
git fetch origin main && \
git reset --hard origin/main && \
echo "✅ Code mis à jour (commit f5d1675)" && \
echo "" && \
gcloud builds submit \
  --project=box-magique-gp-prod \
  --tag gcr.io/box-magique-gp-prod/box-magic-ocr-intelligent:v1.5.0-fix \
  --timeout=15m . && \
echo "✅ Build terminé !" && \
echo "" && \
gcloud run deploy box-magic-ocr-intelligent \
  --project=box-magique-gp-prod \
  --image=gcr.io/box-magique-gp-prod/box-magic-ocr-intelligent:v1.5.0-fix \
  --platform=managed \
  --region=us-central1 \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300s \
  --max-instances=10 \
  --set-env-vars=ENABLE_RUNTIME_DIAGNOSTICS=true,OCR_READ_ONLY=true \
  --quiet && \
echo "✅ Déploiement terminé !" && \
echo "" && \
SERVICE_URL=$(gcloud run services describe box-magic-ocr-intelligent \
  --project=box-magique-gp-prod \
  --region=us-central1 \
  --format="value(status.url)") && \
echo "================================================================" && \
echo "✅ DÉPLOIEMENT RÉUSSI !" && \
echo "================================================================" && \
echo "" && \
echo "🌐 Service URL : ${SERVICE_URL}" && \
echo "" && \
echo "🧪 Tests à effectuer :" && \
echo "   1. Invoice Genspark → N° N8WY0KFA0003, TTC 24.99 USD" && \
echo "   2. Weldom/BricoDia → Montants HT/TVA/TTC extraits" && \
echo "   3. Carrefour CB    → TTC 140.23 EUR" && \
echo "" && \
echo "📊 Logs Cloud Run :" && \
echo "   https://console.cloud.google.com/run/detail/us-central1/box-magic-ocr-intelligent/logs?project=box-magique-gp-prod" && \
echo "" && \
echo "================================================================"
