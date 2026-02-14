# 📋 INSTALLATION MCP DÉPLOIEMENT AUTOMATISÉ

**Date**: 2026-02-14  
**Version**: 1.0.0  
**Durée installation**: ~15 minutes

---

## ⚠️ IMPORTANT

Le workflow GitHub Actions `.github/workflows/deploy.yml` doit être créé **manuellement** dans le repository car GitHub bloque la création de workflows via push automatique.

---

## 🎯 ÉTAPES D'INSTALLATION

### 1. Créer le workflow GitHub Actions

**A) Via GitHub Web UI** (recommandé):

1. Aller sur https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent
2. Cliquer sur l'onglet **Actions**
3. Cliquer **New workflow**
4. Cliquer **set up a workflow yourself**
5. Nommer le fichier: `deploy.yml`
6. Copier-coller le contenu de `.github/workflows/deploy.yml` (voir ci-dessous)
7. Cliquer **Commit changes**

**B) Via Git local** (si permissions suffisantes):

```bash
cd /home/user/webapp
git checkout -b workflow/mcp-deploy
cp .github/workflows/deploy.yml /tmp/deploy.yml

# Pousser avec permissions workflow
git add .github/workflows/deploy.yml
git commit -m "feat(workflow): Add MCP deploy pipeline"
git push origin workflow/mcp-deploy

# Créer PR et merger via GitHub UI
```

### 2. Créer GitHub Personal Access Token

1. GitHub → **Settings** (votre profil)
2. **Developer settings** → **Personal access tokens** → **Tokens (classic)**
3. **Generate new token (classic)**
4. Nom: `MCP IAPF Deploy`
5. Expiration: `No expiration` (ou 1 an)
6. Scopes (cocher):
   - ✅ **repo** (Full control of private repositories)
   - ✅ **workflow** (Update GitHub Action workflows)
7. **Generate token**
8. **Copier le token** (ghp_xxxxxxxxxxxxxxxxxxxx)

### 3. Créer GCP Service Account

```bash
# Se connecter à GCP
gcloud auth login

# Définir le projet
export PROJECT_ID="box-magic-iapf"  # Remplacer par votre ID
gcloud config set project $PROJECT_ID

# Créer compte de service
gcloud iam service-accounts create mcp-deploy \
  --display-name="MCP Deploy Service Account" \
  --description="Service account for automated MCP deployments"

# Donner permissions Cloud Run
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:mcp-deploy@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# Donner permissions Cloud Build
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:mcp-deploy@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/cloudbuild.builds.editor"

# Donner permissions Storage (pour GCR)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:mcp-deploy@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Créer clé JSON
gcloud iam service-accounts keys create ~/mcp-deploy-key.json \
  --iam-account=mcp-deploy@${PROJECT_ID}.iam.gserviceaccount.com

# Afficher la clé (copier le contenu)
cat ~/mcp-deploy-key.json

# ⚠️ Supprimer après configuration GitHub
rm ~/mcp-deploy-key.json
```

### 4. Configurer GitHub Secrets

1. Repository → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret**:
   
   **Secret 1: GCP_SA_KEY**
   - Name: `GCP_SA_KEY`
   - Value: [Contenu complet de mcp-deploy-key.json]
   - Cliquer **Add secret**
   
   **Secret 2: GCP_PROJECT_ID**
   - Name: `GCP_PROJECT_ID`
   - Value: `box-magic-iapf` (votre Project ID)
   - Cliquer **Add secret**

### 5. Configurer Apps Script

1. Ouvrir **Google Sheets HUB ORION** (IAPF_MEMORY_HUB_V1)
2. **Extensions** → **Apps Script**
3. **Paramètres du projet** (⚙️ à gauche)
4. **Propriétés du script** → **Modifier les propriétés du script**
5. Ajouter les propriétés suivantes:

| Propriété | Valeur | Requis |
|-----------|--------|--------|
| `GITHUB_TOKEN` | ghp_xxxxxxxxxxxxxxxxxxxx | ✅ OUI |
| `GITHUB_OWNER` | romacmehdi971-lgtm | Optionnel |
| `GITHUB_REPO` | box-magic-ocr-intelligent | Optionnel |
| `GITHUB_BRANCH` | feature/ocr-intelligent-3-levels | Optionnel |
| `CLOUDRUN_URL` | https://box-magic-ocr-intelligent-*.run.app | Optionnel |
| `TARGET_VERSION` | 1.5.0 | Optionnel |

6. **Enregistrer les propriétés**

### 6. Copier le code MCP_Deploy.gs

1. Apps Script (même projet)
2. **+** (Nouveau fichier) → **Script**
3. Nommer: `MCP_Deploy`
4. Copier-coller le contenu de `MCP_Deploy.gs` depuis `MCP_DEPLOIEMENT_AUTOMATISE.md`
5. **Ctrl+S** (Enregistrer)
6. **Exécuter** la fonction `onOpen` une première fois
   - Autoriser les permissions demandées
7. Actualiser Google Sheets
8. Vérifier que le menu **IAPF Memory** contient: 🚀 Déploiement Automatisé

---

## ✅ VÉRIFICATION INSTALLATION

### Test 1: Configuration

1. Google Sheets → Menu **IAPF Memory**
2. Cliquer **⚙️ Configuration Déploiement**
3. Vérifier:
   - ✅ GitHub Token: Configuré
   - ✅ GitHub Owner: romacmehdi971-lgtm
   - ✅ GitHub Repo: box-magic-ocr-intelligent
   - ✅ Cloud Run URL: https://...

### Test 2: Analyse Changements

1. Menu **IAPF Memory** → **🚀 Déploiement Automatisé**
2. Lire le dialogue
3. Vérifier:
   - Nombre de fichiers modifiés
   - Nombre de commits en attente
   - Estimation durée
4. **Cliquer NO** (ne pas déployer encore)
5. ✅ Si dialogue s'affiche correctement = Installation OK

### Test 3: Workflow GitHub (optionnel)

1. GitHub Repository → **Actions**
2. **MCP Deploy Pipeline** doit apparaître
3. Cliquer **Run workflow**
4. Sélectionner:
   - Branch: `feature/ocr-intelligent-3-levels`
   - Deploy type: `git_push`
   - Message: `Test MCP deploy`
5. **Run workflow**
6. Attendre 1-2 min
7. Vérifier: ✅ Success (checkmark vert)

---

## 🎯 PREMIER DÉPLOIEMENT

**⚠️ IMPORTANT**: Faire un déploiement test sur branche de développement avant production !

### Déploiement Test

1. Google Sheets HUB
2. Menu **IAPF Memory** → **🚀 Déploiement Automatisé**
3. **Lire attentivement** le dialogue
4. **Confirmer YES**
5. **Attendre** 2-3 minutes
6. **Lire le rapport final**:
   - ✅ Git Push: XXs
   - ✅ Apps Script: XXs
   - ✅ Cloud Run: XXs (ou ⏭️ Non requis)
   - URLs déployées
7. **Vérifier MEMORY_LOG**:
   - Nouvelle ligne `DEPLOY_SUCCESS`
   - JSON avec détails complets
8. **Vérifier SNAPSHOT_ACTIVE**:
   - Type: `POST_DEPLOY`
   - Timestamp récent

### Déploiement Production

**Après validation test**:

1. Merger la branche `feature/ocr-intelligent-3-levels` → `main`
2. Créer Pull Request avec validation
3. Après merge, refaire déploiement depuis `main`

---

## 🔧 TROUBLESHOOTING

### Erreur: "GITHUB_TOKEN not configured"

**Solution**:
1. Apps Script → Paramètres → Propriétés
2. Ajouter `GITHUB_TOKEN` avec valeur Personal Access Token
3. Enregistrer et réessayer

### Erreur: "Workflow not found"

**Solution**:
1. Vérifier que `.github/workflows/deploy.yml` existe dans le repo
2. Si absent, créer manuellement via GitHub Web UI (voir Étape 1)

### Erreur: "GCP authentication failed"

**Solution**:
1. Vérifier secret `GCP_SA_KEY` dans GitHub
2. Vérifier que Service Account a les permissions:
   - `roles/run.admin`
   - `roles/cloudbuild.builds.editor`
   - `roles/storage.admin`
3. Régénérer clé si nécessaire

### Erreur: "Cloud Run health check failed"

**Solution**:
1. Vérifier logs Cloud Run:
   ```bash
   gcloud run services logs read box-magic-ocr-intelligent --region us-central1
   ```
2. Vérifier que `/health` endpoint répond
3. Corriger Dockerfile si nécessaire

### Erreur: "Apps Script timeout"

**Solution**:
- Google Apps Script a limite 6 min par exécution
- Si Cloud Run deploy > 6 min, le script timeout
- Utiliser déploiement en 2 étapes:
  1. `deploy_type: git_push` (rapide)
  2. `deploy_type: cloud_run` (séparé)

---

## 📚 DOCUMENTATION COMPLÈTE

Consultez `MCP_DEPLOIEMENT_AUTOMATISE.md` pour:
- Architecture détaillée
- Code JavaScript complet
- Workflow GitHub Actions
- Alternatives (semi-auto, manuel)
- Logs et monitoring
- Règles de sécurité

---

## 🔗 LIENS UTILES

- **Repository**: https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent
- **GitHub Actions**: https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent/actions
- **Cloud Run Console**: https://console.cloud.google.com/run
- **Apps Script Editor**: https://script.google.com
- **GCP IAM**: https://console.cloud.google.com/iam-admin

---

## ✅ CHECKLIST FINALE

- [ ] Workflow GitHub Actions créé
- [ ] GitHub Personal Access Token créé et configuré
- [ ] GCP Service Account créé avec permissions
- [ ] GitHub Secrets configurés (GCP_SA_KEY, GCP_PROJECT_ID)
- [ ] Apps Script Properties configurées (GITHUB_TOKEN minimum)
- [ ] Code MCP_Deploy.gs copié dans Apps Script
- [ ] Menu IAPF Memory contient bouton 🚀 Déploiement Automatisé
- [ ] Configuration testée (⚙️ Configuration Déploiement)
- [ ] Déploiement test réussi
- [ ] Logs MEMORY_LOG vérifiés
- [ ] Snapshot POST_DEPLOY créé
- [ ] Documentation lue et comprise

---

**Installation complétée le**: ___________________  
**Installé par**: ___________________  
**Statut**: ✅ / ⚠️ / ❌ (encercler)  
**Notes**: ___________________________________________
