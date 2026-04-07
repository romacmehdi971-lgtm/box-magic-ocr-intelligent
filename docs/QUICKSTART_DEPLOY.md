# 🚀 Quick Start - Push vers Container & Deploy

## 🎯 Méthode Ultra-Rapide (Recommandée)

### Option 1 : Script Automatique Interactif

```bash
# Depuis votre machine locale (pas le sandbox)
cd /path/to/box-magic-ocr-intelligent

# Lancer le script interactif
./setup_gcp.sh
```

Le script vous demandera :
1. ✅ Votre Project ID GCP
2. ✅ La région (défaut: europe-west1)
3. ✅ Le nom du service (défaut: box-magic-ocr-intelligent)
4. ✅ Si vous voulez déployer immédiatement

**Tout le reste est automatique !**

---

## 🎯 Méthode Manuelle (3 Commandes)

```bash
# 1. Configurer votre projet
export PROJECT_ID="votre-project-id"
gcloud config set project $PROJECT_ID

# 2. Build & Push (une seule commande)
gcloud builds submit --tag gcr.io/$PROJECT_ID/box-magic-ocr-intelligent .

# 3. Déployer sur Cloud Run
gcloud run deploy box-magic-ocr-intelligent \
  --image gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:latest \
  --platform managed \
  --region europe-west1 \
  --memory 2Gi \
  --allow-unauthenticated
```

**C'est tout ! Votre service est en ligne.**

---

## 📦 Ce qui se passe pendant le build

```
┌─────────────────────────────────────────────────────┐
│  1. Upload du code vers Google Cloud Build         │
│     • Dockerfile                                    │
│     • Code Python                                   │
│     • Configuration                                 │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│  2. Build de l'image Docker sur GCP                 │
│     • Stage 1: Build avec dépendances Python       │
│     • Stage 2: Runtime avec tesseract + poppler    │
│     • Vérification des binaires                    │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│  3. Push automatique vers Container Registry        │
│     • Image: gcr.io/PROJECT_ID/SERVICE_NAME:latest │
│     • Visible dans GCR                             │
└─────────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────────┐
│  4. Déploiement sur Cloud Run (si demandé)          │
│     • Service accessible via URL publique          │
│     • Auto-scaling configuré                       │
│     • Health check activé                          │
└─────────────────────────────────────────────────────┘
```

**Durée totale** : 5-10 minutes

---

## 🔍 Vérifier que tout fonctionne

### 1. Vérifier l'image dans GCR

```bash
# Lister les images
gcloud container images list --repository=gcr.io/$PROJECT_ID

# Voir les tags
gcloud container images list-tags gcr.io/$PROJECT_ID/box-magic-ocr-intelligent
```

### 2. Tester le service Cloud Run

```bash
# Récupérer l'URL
SERVICE_URL=$(gcloud run services describe box-magic-ocr-intelligent \
  --region europe-west1 \
  --format 'value(status.url)')

# Test health check
curl $SERVICE_URL/health

# Test root endpoint
curl $SERVICE_URL/

# Test OCR (avec un fichier)
curl -X POST $SERVICE_URL/ocr \
  -F "file=@facture_1.pdf" \
  -F "source_entreprise=auto-detect"
```

---

## ⚡ Si vous n'avez PAS gcloud localement

### Utiliser Cloud Shell (Navigateur)

1. **Ouvrir Cloud Shell** : https://console.cloud.google.com/?cloudshell=true

2. **Cloner le repo** :
   ```bash
   git clone https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent.git
   cd box-magic-ocr-intelligent
   ```

3. **Lancer le build** :
   ```bash
   gcloud builds submit --tag gcr.io/$GOOGLE_CLOUD_PROJECT/box-magic-ocr-intelligent .
   ```

4. **Déployer** :
   ```bash
   gcloud run deploy box-magic-ocr-intelligent \
     --image gcr.io/$GOOGLE_CLOUD_PROJECT/box-magic-ocr-intelligent:latest \
     --platform managed \
     --region europe-west1 \
     --memory 2Gi \
     --allow-unauthenticated
   ```

**Tout se fait dans le navigateur !**

---

## 🐳 Si vous voulez utiliser Docker local

```bash
# 1. Authentifier Docker avec GCR
gcloud auth configure-docker

# 2. Build localement
docker build -t gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:latest .

# 3. Test local (optionnel)
docker run -p 8080:8080 gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:latest

# 4. Push vers GCR
docker push gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:latest

# 5. Déployer sur Cloud Run
gcloud run deploy box-magic-ocr-intelligent \
  --image gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:latest \
  --platform managed \
  --region europe-west1 \
  --memory 2Gi \
  --allow-unauthenticated
```

---

## 📊 Tableau Récapitulatif des Méthodes

| Méthode | Avantages | Prérequis |
|---------|-----------|-----------|
| **Script `setup_gcp.sh`** | ✅ Ultra simple<br>✅ Interactif<br>✅ Tout automatisé | gcloud CLI |
| **Cloud Build** | ✅ Pas besoin Docker local<br>✅ Build sur GCP<br>✅ Plus rapide | gcloud CLI |
| **Docker Local** | ✅ Test avant push<br>✅ Contrôle total | Docker + gcloud CLI |
| **Cloud Shell** | ✅ Rien à installer<br>✅ Dans le navigateur | Compte GCP seulement |

---

## 🎯 Ma Recommandation

### Pour vous (utilisateur final) :

```bash
# Méthode la plus simple
./setup_gcp.sh
```

**Répondez aux 3 questions, le reste est automatique.**

---

## ❓ FAQ

### Q: Combien ça coûte ?

**Build** : ~$0.003 par minute (gratuit jusqu'à 120 min/jour)  
**Storage GCR** : ~$0.026 par GB/mois  
**Cloud Run** : Gratuit jusqu'à 2 millions de requêtes/mois  

**Coût estimé** : < $5/mois pour usage modéré

### Q: Puis-je build depuis ce sandbox ?

**Non**, le sandbox n'a pas accès à vos credentials GCP.

**Solutions** :
1. Cloner le repo sur votre machine locale
2. Utiliser Cloud Shell dans votre navigateur
3. Utiliser GitHub Actions (CI/CD)

### Q: Comment mettre à jour l'image ?

```bash
# Re-build et push
gcloud builds submit --tag gcr.io/$PROJECT_ID/box-magic-ocr-intelligent .

# Mettre à jour Cloud Run
gcloud run services update box-magic-ocr-intelligent \
  --image gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:latest \
  --region europe-west1
```

### Q: Comment voir les logs en production ?

```bash
# Logs Cloud Run
gcloud run services logs read box-magic-ocr-intelligent \
  --region europe-west1 \
  --limit 50

# Logs en temps réel
gcloud run services logs tail box-magic-ocr-intelligent \
  --region europe-west1
```

---

## ✅ Checklist de Déploiement

- [ ] Repository cloné localement (ou dans Cloud Shell)
- [ ] gcloud CLI installé et configuré
- [ ] Authentifié : `gcloud auth login`
- [ ] Project ID connu
- [ ] Script `setup_gcp.sh` exécuté OU commandes manuelles lancées
- [ ] Image visible dans GCR
- [ ] Service déployé sur Cloud Run
- [ ] URL du service récupérée
- [ ] Health check testé avec succès
- [ ] Test OCR avec facture_1.pdf fonctionnel

---

**Besoin d'aide ?** Tous les guides détaillés sont dans `PUSH_TO_CONTAINER.md` et `DEPLOYMENT_GUIDE.md`.
