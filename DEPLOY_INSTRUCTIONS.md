# 🚀 DÉPLOIEMENT OCR1 FIX — INSTRUCTIONS

## ✅ CODE PRÊT
- **Commit**: `dfc3a69`
- **Branch**: `feature/ocr-intelligent-3-levels`
- **Pull Request**: https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent/pull/4

## 🔧 CORRECTIONS APPLIQUÉES
1. ✅ Détection FACTURE correcte (patterns pondérés)
2. ✅ Pas d'injection "Martin's Traiteur" (retourne UNKNOWN)
3. ✅ Texte normalisé (gère espaces PyPDF2)
4. ✅ Logging exhaustif (texte brut, scores, métadonnées)

---

## 🚀 OPTION 1 : DÉPLOIEMENT MANUEL (CLOUD SHELL)

### 1. Ouvrir Cloud Shell
```
https://console.cloud.google.com/?cloudshell=true&project=box-magique-gp-prod
```

### 2. Cloner le repo + checkout branch
```bash
git clone https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent.git
cd box-magic-ocr-intelligent
git checkout feature/ocr-intelligent-3-levels
git pull origin feature/ocr-intelligent-3-levels
```

### 3. Build & Deploy
```bash
PROJECT_ID="box-magique-gp-prod"
REGION="us-central1"
SERVICE_NAME="box-magic-ocr-intelligent"

# Build image
gcloud builds submit --project=${PROJECT_ID} \
  --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME}:ocr1-fix .

# Deploy
gcloud run deploy ${SERVICE_NAME} \
  --project=${PROJECT_ID} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME}:ocr1-fix \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --set-env-vars "ENABLE_RUNTIME_DIAGNOSTICS=true,OCR_READ_ONLY=true"
```

### 4. Vérifier
```bash
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
  --project=${PROJECT_ID} --region ${REGION} \
  --format 'value(status.url)')

echo "Service URL: ${SERVICE_URL}"
curl ${SERVICE_URL}/health
```

---

## 🤖 OPTION 2 : DÉPLOIEMENT AUTO (MERGER PR)

Si vous avez un CI/CD configuré (Cloud Build trigger) :

1. **Merger la PR** : https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent/pull/4
2. Le déploiement se fera **automatiquement**
3. Vérifier les logs Cloud Build

---

## 📊 VÉRIFICATION POST-DÉPLOIEMENT

### 1. Tester avec votre facture Genspark
```bash
curl -X POST ${SERVICE_URL}/ocr \
  -F "file=@/path/to/Invoice-N8WY0KFA-0003.pdf" \
  -F "source_entreprise=auto-detect"
```

### 2. Vérifier les logs
```bash
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=${SERVICE_NAME}" \
  --project=${PROJECT_ID} \
  --limit 50 \
  --format json
```

### 3. Attentes
- ✅ `document_type: FACTURE` (pas TICKET)
- ✅ `entreprise_source: UNKNOWN` (pas Martin's Traiteur)
- ✅ Logs montrent texte OCR brut
- ✅ Logs montrent scores de classification

---

## 🆘 EN CAS DE PROBLÈME

Si le déploiement échoue ou si les résultats ne sont pas corrects :

1. Vérifier les logs Cloud Build
2. Vérifier les logs Cloud Run
3. Me fournir les logs d'erreur

**Ne pas itérer sans diagnostic.**

---

**Version**: OCR1 v1.0.1-fix  
**Commit**: dfc3a69  
**Date**: 2026-02-06
