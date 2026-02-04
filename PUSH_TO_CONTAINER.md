# 🚀 Guide : Push vers Container Registry

## Prérequis

1. **Compte Google Cloud Platform (GCP)** avec un projet actif
2. **gcloud CLI installé** sur votre machine locale
3. **Authentification configurée** : `gcloud auth login`

---

## 🎯 Méthode 1 : Google Cloud Build (RECOMMANDÉ)

Cette méthode build l'image **directement sur GCP** sans avoir besoin de Docker local.

### Étape 1 : Configurer votre projet GCP

```bash
# Définir votre Project ID
export PROJECT_ID="votre-project-id"

# Configurer gcloud
gcloud config set project $PROJECT_ID

# Vérifier la configuration
gcloud config get-value project
```

### Étape 2 : Activer les APIs nécessaires

```bash
# Activer Cloud Build API
gcloud services enable cloudbuild.googleapis.com

# Activer Container Registry API
gcloud services enable containerregistry.googleapis.com

# Activer Cloud Run API (pour déploiement)
gcloud services enable run.googleapis.com
```

### Étape 3 : Build & Push avec Cloud Build

```bash
# Depuis le répertoire du projet
cd /path/to/box-magic-ocr-intelligent

# Build et push en une seule commande
gcloud builds submit --tag gcr.io/$PROJECT_ID/box-magic-ocr-intelligent .
```

**Résultat** : 
- ✅ Image construite sur GCP
- ✅ Image poussée automatiquement vers `gcr.io/votre-project-id/box-magic-ocr-intelligent`
- ✅ Vérification des binaires (tesseract, poppler) pendant le build

### Étape 4 : Vérifier l'image

```bash
# Lister les images dans GCR
gcloud container images list --repository=gcr.io/$PROJECT_ID

# Voir les tags de l'image
gcloud container images list-tags gcr.io/$PROJECT_ID/box-magic-ocr-intelligent
```

---

## 🎯 Méthode 2 : Docker Local + Push Manuel

Si vous avez Docker installé localement et voulez build en local.

### Étape 1 : Configurer Docker pour GCR

```bash
# Authentifier Docker avec GCR
gcloud auth configure-docker
```

### Étape 2 : Build l'image localement

```bash
# Définir les variables
export PROJECT_ID="votre-project-id"
export IMAGE_NAME="gcr.io/$PROJECT_ID/box-magic-ocr-intelligent"
export TAG="latest"

# Build l'image
docker build -t $IMAGE_NAME:$TAG .

# Vérifier l'image
docker images | grep box-magic-ocr
```

### Étape 3 : Tester localement (optionnel)

```bash
# Lancer le container en local
docker run -p 8080:8080 $IMAGE_NAME:$TAG

# Tester l'API
curl http://localhost:8080/health
```

### Étape 4 : Push vers GCR

```bash
# Push l'image
docker push $IMAGE_NAME:$TAG

# Vérifier le push
gcloud container images list-tags gcr.io/$PROJECT_ID/box-magic-ocr-intelligent
```

---

## 🎯 Méthode 3 : Script Automatisé (Plus Simple)

Utilisez le script de déploiement fourni.

### Utilisation du script deploy.sh

```bash
# Rendre le script exécutable (déjà fait)
chmod +x deploy.sh

# Lancer le déploiement complet (build + push + deploy)
./deploy.sh votre-project-id europe-west1 box-magic-ocr-intelligent
```

**Ce script fait automatiquement** :
1. ✅ Active les APIs nécessaires
2. ✅ Build l'image avec Cloud Build
3. ✅ Push vers GCR
4. ✅ Déploie sur Cloud Run
5. ✅ Affiche l'URL du service

---

## 🔍 Vérifications Post-Push

### 1. Vérifier que l'image existe dans GCR

```bash
# Lister toutes les images
gcloud container images list --repository=gcr.io/$PROJECT_ID

# Voir les détails de l'image
gcloud container images describe gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:latest
```

### 2. Tester l'image depuis GCR (optionnel)

```bash
# Pull l'image depuis GCR
docker pull gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:latest

# Lancer le container
docker run -p 8080:8080 gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:latest

# Tester
curl http://localhost:8080/health
```

---

## 🚀 Déploiement sur Cloud Run

Une fois l'image dans GCR, déployez sur Cloud Run :

```bash
# Déployer sur Cloud Run
gcloud run deploy box-magic-ocr-intelligent \
  --image gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:latest \
  --platform managed \
  --region europe-west1 \
  --memory 2Gi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10 \
  --allow-unauthenticated \
  --set-env-vars "ENABLE_RUNTIME_DIAGNOSTICS=true"

# Récupérer l'URL du service
gcloud run services describe box-magic-ocr-intelligent \
  --region europe-west1 \
  --format 'value(status.url)'
```

---

## 📊 Commandes Utiles

### Gestion des images GCR

```bash
# Lister toutes les images
gcloud container images list

# Voir les tags d'une image
gcloud container images list-tags gcr.io/$PROJECT_ID/box-magic-ocr-intelligent

# Supprimer une image spécifique
gcloud container images delete gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:TAG

# Supprimer toutes les vieilles images (garder les 3 dernières)
gcloud container images list-tags gcr.io/$PROJECT_ID/box-magic-ocr-intelligent \
  --limit=999 --sort-by=~TIMESTAMP --format='get(digest)' | tail -n +4 | \
  xargs -I {} gcloud container images delete gcr.io/$PROJECT_ID/box-magic-ocr-intelligent@{} --quiet
```

### Gestion Cloud Run

```bash
# Lister tous les services Cloud Run
gcloud run services list --region europe-west1

# Voir les logs d'un service
gcloud run services logs read box-magic-ocr-intelligent --region europe-west1

# Mettre à jour un service avec une nouvelle image
gcloud run services update box-magic-ocr-intelligent \
  --image gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:TAG \
  --region europe-west1
```

---

## 🔐 Permissions Nécessaires

Votre compte GCP doit avoir les rôles suivants :

- **Cloud Build Editor** : Pour builder les images
- **Storage Admin** : Pour pousser vers GCR (GCR utilise Cloud Storage)
- **Cloud Run Admin** : Pour déployer sur Cloud Run
- **Service Account User** : Pour utiliser les service accounts

### Attribuer les permissions

```bash
# Obtenir votre email GCP
gcloud config get-value account

# Attribuer les rôles nécessaires
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:votre-email@example.com" \
  --role="roles/cloudbuild.builds.editor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:votre-email@example.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:votre-email@example.com" \
  --role="roles/run.admin"
```

---

## ⚠️ Troubleshooting

### Problème : "Permission denied"

```bash
# Solution : Vérifier les permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:$(gcloud config get-value account)"
```

### Problème : "API not enabled"

```bash
# Solution : Activer toutes les APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  run.googleapis.com
```

### Problème : "Docker authentication failed"

```bash
# Solution : Reconfigurer l'authentification Docker
gcloud auth configure-docker
```

### Problème : "Build timeout"

```bash
# Solution : Augmenter le timeout du build
gcloud builds submit --tag gcr.io/$PROJECT_ID/box-magic-ocr-intelligent \
  --timeout=20m .
```

---

## 📝 Résumé - Commandes Rapides

```bash
# Setup initial
export PROJECT_ID="votre-project-id"
gcloud config set project $PROJECT_ID
gcloud services enable cloudbuild.googleapis.com containerregistry.googleapis.com run.googleapis.com

# Build & Push (Méthode recommandée)
gcloud builds submit --tag gcr.io/$PROJECT_ID/box-magic-ocr-intelligent .

# Vérifier
gcloud container images list-tags gcr.io/$PROJECT_ID/box-magic-ocr-intelligent

# Déployer sur Cloud Run
gcloud run deploy box-magic-ocr-intelligent \
  --image gcr.io/$PROJECT_ID/box-magic-ocr-intelligent:latest \
  --platform managed \
  --region europe-west1 \
  --memory 2Gi \
  --allow-unauthenticated

# Obtenir l'URL
gcloud run services describe box-magic-ocr-intelligent \
  --region europe-west1 \
  --format 'value(status.url)'
```

---

## ✅ Checklist Finale

- [ ] gcloud CLI installé et configuré
- [ ] Authentifié avec `gcloud auth login`
- [ ] Project ID configuré
- [ ] APIs activées (Cloud Build, Container Registry, Cloud Run)
- [ ] Image buildée et pushée vers GCR
- [ ] Image visible dans GCR : `gcloud container images list`
- [ ] Service déployé sur Cloud Run
- [ ] URL du service récupérée et testée

---

**Besoin d'aide ?** Consultez la [documentation officielle Google Cloud](https://cloud.google.com/build/docs/build-push-docker-image).
