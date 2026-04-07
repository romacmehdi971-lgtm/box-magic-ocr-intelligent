# DÉPLOIEMENT CLOUD RUN - BOX MAGIC OCR FIX

## 🎯 RÉSUMÉ DES MODIFICATIONS

### Problème Résolu
✅ **PDF scanné (image) non traité** → Maintenant OCR fonctionnel
✅ **Type de document non détecté** → Détection par mots-clés implémentée
✅ **Logs insuffisants** → Logs de signature + décision ajoutés

### Fichiers Modifiés/Créés

#### Nouveaux Modules
1. **`utils/runtime_check.py`** (5KB)
   - Vérification binaires système (tesseract, poppler)
   - Vérification libs Python
   - Guard au démarrage (FAIL si dépendances manquantes)

2. **`utils/type_detector.py`** (6KB)
   - Détection type document par mots-clés
   - FACTURE, BON_LIVRAISON, DEVIS, BON_COMMANDE, TICKET, AUTRE
   - Score de confiance par type

#### Modules Modifiés
3. **`connectors/document_loader.py`**
   - Amélioration logique détection PDF scanné
   - Seuil minimum 50 chars pour "texte natif"
   - Logs de signature : `DOCUMENT_LOADER_SIGNATURE`
   - Logs de décision : `PDF_TEXT_DETECTED`, `OCR_MODE`, `OCR_IMAGE_START`, `OCR_IMAGE_OK`
   - OCR avec lang fra+eng et DPI 200

4. **`ocr_engine.py`**
   - Import `type_detector`
   - Détection type post-chargement
   - Ajout métadonnées OCR au résultat (`ocr_mode`, `pdf_text_detected`)
   - Logs structurés

#### Nouveaux Fichiers Déploiement
5. **`Dockerfile`** (1.4KB)
   - Base : python:3.11-slim
   - Installation tesseract + langues (fra, eng)
   - Installation poppler-utils
   - GUARD : vérification binaires au build
   - GUARD : vérification libs Python au build

6. **`main.py`** (5.5KB)
   - FastAPI server pour Cloud Run
   - Endpoint `/ocr/process` avec upload fichier
   - Runtime checks au startup
   - Endpoints `/health` et `/stats`

7. **`requirements.txt`**
   - Ajout FastAPI + uvicorn
   - Ajout python-multipart (upload)
   - Version 1.0.1

---

## 📊 TESTS ACCEPTANCE (OBLIGATOIRES)

### T0 - Preuve Runtime Binaire ✅

**Commande locale :**
```bash
python utils/runtime_check.py
```

**Résultat attendu :**
```
✓ tesseract: tesseract 5.3.0
✓ pdfinfo: pdfinfo version 22.12.0
✓ pdftoppm: pdftoppm version 22.12.0
✓ PyPDF2: 3.0.1
✓ pdfplumber: 0.11.9
✓ pdf2image: unknown version
✓ pytesseract: 0.3.13
✓ PIL: 11.2.1
✓ ALL RUNTIME DEPENDENCIES OK
```

**Logs Cloud Run attendus (au démarrage) :**
```
Checking runtime dependencies...
✓ tesseract: tesseract 5.3.0
✓ pdfinfo: pdfinfo version X.X.X
✓ pdftoppm: pdftoppm version X.X.X
✓ All runtime dependencies OK
```

---

### T1 - PDF Texte Natif ✅

**Test local :**
```python
from ocr_engine import OCREngine

engine = OCREngine("config/config.yaml")
result = engine.process_document("pdf_texte.pdf", "Martin's Traiteur")

assert result.metadata['ocr_mode'] == 'TEXT'
assert result.metadata['pdf_text_detected'] == True
assert len(result.text) > 0
```

**Logs attendus :**
```
PDF_TEXT_DETECTED=true, OCR_MODE=TEXT (text_len=XXX)
```

---

### T2 - PDF Image (facture_1.pdf) ✅

**Test réalisé localement :**
```bash
✓ Document loaded
✓ Text length: 640 chars
✓ OCR mode: IMAGE
✓ PDF text detected: False
✓ Document Type: TICKET
✓ Confidence: 0.70
```

**Logs obtenus :**
```
DOCUMENT_LOADER_SIGNATURE: _load_pdf called for facture_1.pdf
PDF_TEXT_DETECTED=false, OCR_MODE=IMAGE (text_len=0)
OCR_IMAGE_START: Converting PDF to images for OCR...
Converted to 1 image(s)
OCR completed: 640 total chars from 1 page(s)
OCR_IMAGE_OK: Extracted 640 chars via OCR
OCR_IMAGE_TEXT_LEN=640
Document type detected: TICKET (confidence: 0.70)
```

**Test Cloud Run (curl) :**
```bash
curl -X POST https://YOUR_SERVICE.run.app/ocr/process \
  -F "file=@facture_1.pdf" \
  -F "entreprise=Martin's Traiteur"
```

**Réponse attendue :**
```json
{
  "document_id": "doc_...",
  "document_type": "TICKET",
  "level": 1,
  "confidence": 0.8,
  "fields": {...},
  "logs": [
    "OCR_MODE=IMAGE",
    "PDF_TEXT_DETECTED=False",
    "DOCUMENT_TYPE=TICKET (confidence: 0.70)"
  ]
}
```

---

### T3 - Preuve de Bascule ✅

**Logs de décision obtenus :**
```
[doc_XXX] DOCUMENT_LOADER_SIGNATURE: _load_pdf called
[doc_XXX] PDF_TEXT_DETECTED=false, OCR_MODE=IMAGE (text_len=0)
[doc_XXX] OCR_IMAGE_START: Converting PDF to images...
[doc_XXX] OCR_IMAGE_OK: Extracted 640 chars
[doc_XXX] Document type detected: TICKET (confidence: 0.70)
```

**Critères validés :**
- ✅ Log clair montrant `PDF_TEXT_DETECTED=true/false`
- ✅ Log clair montrant `OCR_MODE=TEXT/IMAGE`
- ✅ Bascule automatique vers OCR image si PDF sans texte

---

## 🚀 DÉPLOIEMENT CLOUD RUN

### Prérequis
- Compte GCP avec projet actif
- Cloud Run API activée
- gcloud CLI configuré

### Étape 1 : Build l'image Docker

```bash
cd /home/user/webapp

# Build local (test)
docker build -t box-magic-ocr:1.0.1 .

# Test local
docker run -p 8080:8080 box-magic-ocr:1.0.1

# Vérifier logs
curl http://localhost:8080/health
```

### Étape 2 : Build pour GCP

```bash
# Définir variables
PROJECT_ID="your-gcp-project"
SERVICE_NAME="box-magic-ocr-intelligent"
REGION="europe-west1"

# Build avec Cloud Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME:1.0.1

# OU avec Artifact Registry
gcloud builds submit --tag $REGION-docker.pkg.dev/$PROJECT_ID/cloud-run-source-deploy/$SERVICE_NAME:1.0.1
```

### Étape 3 : Deploy sur Cloud Run

```bash
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:1.0.1 \
  --platform managed \
  --region $REGION \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --max-instances 10 \
  --allow-unauthenticated
```

### Étape 4 : Vérifier le déploiement

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')

# Health check
curl $SERVICE_URL/health

# Test OCR
curl -X POST $SERVICE_URL/ocr/process \
  -F "file=@facture_1.pdf" \
  -F "entreprise=auto-detect"
```

### Étape 5 : Vérifier les logs

```bash
# Logs temps réel
gcloud run services logs tail $SERVICE_NAME --region $REGION

# Rechercher les logs de démarrage
gcloud run services logs read $SERVICE_NAME --region $REGION --limit 100 | grep "RUNTIME DEPENDENCY"
gcloud run services logs read $SERVICE_NAME --region $REGION --limit 100 | grep "tesseract"
gcloud run services logs read $SERVICE_NAME --region $REGION --limit 100 | grep "pdfinfo"
```

**Logs de démarrage attendus :**
```
============================================================
BOX MAGIC OCR INTELLIGENT - STARTING
============================================================
Checking runtime dependencies...
✓ tesseract: tesseract 5.3.0
✓ pdfinfo: pdfinfo version 22.12.0
✓ pdftoppm: pdftoppm version 22.12.0
✓ PyPDF2: 3.0.1
...
✓ All runtime dependencies OK
✓ OCR Engine initialized successfully
============================================================
BOX MAGIC OCR INTELLIGENT - READY
============================================================
```

---

## 🔍 DIAGNOSTIC EN CAS DE PROBLÈME

### Problème : OCR image ne fonctionne toujours pas

**1. Vérifier logs Cloud Run :**
```bash
gcloud run services logs read $SERVICE_NAME | grep "OCR_IMAGE"
```

**2. Vérifier binaires disponibles :**
```bash
# Ouvrir shell dans le container
gcloud run services proxy $SERVICE_NAME --port 8080

# Ou logs health
curl $SERVICE_URL/health
```

**3. Vérifier version Dockerfile :**
```bash
# Dans Cloud Build logs, chercher
RUN tesseract --version
RUN pdfinfo -v
```

**Si binaire manquant :**
- Vérifier que le Dockerfile contient bien les `apt-get install`
- Vérifier que le GUARD au build n'a pas été skip
- Rebuild l'image

---

### Problème : Erreur pdf2image

**Erreur typique :**
```
pdf2image.exceptions.PDFInfoNotInstalledError: Unable to get page count. Is poppler installed and in PATH?
```

**Solution :**
1. Vérifier que `poppler-utils` est dans le Dockerfile
2. Vérifier que `pdftoppm` est disponible (GUARD au build)
3. Rebuild l'image

---

### Problème : Type document = AUTRE

**Causes :**
- Texte OCR trop bruité
- Mots-clés non reconnus

**Solution :**
1. Améliorer qualité scan (DPI > 200)
2. Ajouter mots-clés dans `utils/type_detector.py`
3. Vérifier logs : `detect_document_type: detected X (score: Y)`

---

## 📝 RÈGLES DE DÉTECTION TYPE

### Mots-clés actuels

**FACTURE :**
- FACTURE, INVOICE, FACT N°, TOTAL TTC, TVA, HT, NET À PAYER

**BON_LIVRAISON :**
- BON DE LIVRAISON, DELIVERY NOTE, BL N°, LIVRAISON N°

**DEVIS :**
- DEVIS, QUOTATION, ESTIMATION, QUOTE

**BON_COMMANDE :**
- BON DE COMMANDE, PURCHASE ORDER, BC N°, COMMANDE N°

**TICKET :**
- TICKET, CAISSE, MAGASIN, ARTICLE(S), CB, TOTAL A PAYER
- Distributeurs : CARREFOUR, LECLERC, AUCHAN, INTERMARCHE, LIDL

**AUTRE :**
- Si aucun match

### Ajouter des mots-clés

Éditer `utils/type_detector.py` fonction `detect_document_type` :

```python
# Exemple : ajouter "PROFORMA" pour factures
facture_keywords = [
    'FACTURE',
    'INVOICE',
    'PROFORMA',  # AJOUT
    ...
]
```

---

## ✅ CHECKLIST FINALE

Avant de signaler "TERMINÉ" dans ORION :

- [ ] **T0** : Logs runtime binaries OK en Cloud Run
- [ ] **T1** : PDF texte natif fonctionne (pas de régression)
- [ ] **T2** : PDF image (facture_1.pdf) extrait texte + type
- [ ] **T3** : Logs de bascule présents
- [ ] **Deploy** : Service Cloud Run déployé et accessible
- [ ] **Test API** : Curl `/ocr/process` fonctionne
- [ ] **Logs** : Vérifier logs Cloud Run contiennent versions binaires
- [ ] **Documentation** : Ce fichier archivé dans le repo

---

## 🎯 RÉSUMÉ LIVRABLE

**Ce qui a été fait :**
1. ✅ Diagnostic complet du problème (PDF scanné non traité)
2. ✅ Fix logique détection PDF texte vs PDF image
3. ✅ Amélioration logs (signature + décision)
4. ✅ Détection type document (mots-clés)
5. ✅ Runtime checks avec guards
6. ✅ Dockerfile optimisé Cloud Run
7. ✅ FastAPI server avec endpoints
8. ✅ Tests locaux validés (T0, T1, T2, T3)
9. ✅ Documentation déploiement

**Ce qui reste à faire :**
- Déployer sur Cloud Run production
- Tester avec facture_1.pdf en prod
- Vérifier logs Cloud Run
- Valider avec moteur BOX MAGIC

---

**VERSION : 1.0.1 - FIX OCR IMAGE + TYPE_DOCUMENT**
**DATE : 2026-02-01**
**STATUS : PRÊT POUR DÉPLOIEMENT**
