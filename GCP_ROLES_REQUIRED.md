# 🔐 RÔLES GCP REQUIS POUR LE DÉPLOIEMENT

**Compte de service** : `genspark-deploy-temp@box-magique-gp-prod.iam.gserviceaccount.com`  
**Projet GCP** : `box-magique-gp-prod`

---

## ✅ RÔLES OBLIGATOIRES À AJOUTER

### 1. Cloud Run Admin
```
roles/run.admin
```
**Permissions incluses** :
- `run.services.list`
- `run.services.get`
- `run.services.create`
- `run.services.update`
- `run.services.delete`
- `run.revisions.list`
- `run.revisions.get`

### 2. Cloud Build Editor
```
roles/cloudbuild.builds.editor
```
**Permissions incluses** :
- `cloudbuild.builds.create`
- `cloudbuild.builds.get`
- `cloudbuild.builds.list`

### 3. Artifact Registry Administrator
```
roles/artifactregistry.admin
```
**Permissions incluses** :
- `artifactregistry.repositories.create`
- `artifactregistry.repositories.get`
- `artifactregistry.repositories.list`
- `artifactregistry.repositories.uploadArtifacts`
- `artifactregistry.repositories.downloadArtifacts`

### 4. Storage Admin (pour Cloud Build)
```
roles/storage.admin
```
**Permissions incluses** :
- `storage.buckets.create`
- `storage.buckets.get`
- `storage.buckets.list`
- `storage.objects.create`
- `storage.objects.delete`

### 5. Service Account User
```
roles/iam.serviceAccountUser
```
**Permissions incluses** :
- `iam.serviceAccounts.actAs`

---

## 📝 COMMANDES D'AJOUT DES RÔLES

Exécutez ces commandes dans la **Cloud Shell** ou avec un compte ayant les permissions `Owner` :

```bash
# Variables
PROJECT_ID="box-magique-gp-prod"
SA_EMAIL="genspark-deploy-temp@box-magique-gp-prod.iam.gserviceaccount.com"

# Ajouter Cloud Run Admin
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/run.admin"

# Ajouter Cloud Build Editor
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/cloudbuild.builds.editor"

# Ajouter Artifact Registry Admin
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/artifactregistry.admin"

# Ajouter Storage Admin
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/storage.admin"

# Ajouter Service Account User
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/iam.serviceAccountUser"
```

---

## 🌐 VIA LA CONSOLE WEB GCP

1. Ouvrez : https://console.cloud.google.com/iam-admin/iam?project=box-magique-gp-prod
2. Trouvez le compte de service : `genspark-deploy-temp@box-magique-gp-prod.iam.gserviceaccount.com`
3. Cliquez sur **✏️ Modifier**
4. Cliquez sur **+ AJOUTER UN AUTRE RÔLE**
5. Ajoutez chacun des 5 rôles ci-dessus
6. Cliquez sur **ENREGISTRER**

---

## ⏱️ TEMPS D'ACTIVATION

**Propagation des permissions** : 1-3 minutes après l'ajout des rôles.

---

## ✅ VÉRIFICATION

Après l'ajout des rôles, vérifiez avec :

```bash
gcloud projects get-iam-policy box-magique-gp-prod \
  --flatten="bindings[].members" \
  --format="table(bindings.role)" \
  --filter="bindings.members:genspark-deploy-temp@box-magique-gp-prod.iam.gserviceaccount.com"
```

Vous devriez voir :

```
ROLE
roles/run.admin
roles/cloudbuild.builds.editor
roles/artifactregistry.admin
roles/storage.admin
roles/iam.serviceAccountUser
```

---

## 🚨 IMPORTANT

- **NE PAS** ajouter le rôle `Owner` ou `Editor` (trop permissif)
- Ces 5 rôles sont le **minimum requis** pour le déploiement
- Après le déploiement, vous pourrez **révoquer** ces rôles

---

## 📞 EN CAS DE PROBLÈME

Si vous n'avez pas les droits pour ajouter ces rôles :
1. Contactez l'**administrateur GCP** du projet
2. Envoyez-lui ce fichier avec les rôles requis
3. Demandez-lui d'ajouter les permissions au compte de service

---

**Date de création** : 2026-02-14  
**Version** : 1.0.0
