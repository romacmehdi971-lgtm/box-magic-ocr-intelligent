# PHASE 2 — INSTRUCTIONS FINALES POUR ÉLIA
# Extension Contrôlée des Accès MCP (One-Shot)
**Date**: 2026-02-20  
**Durée estimée**: 35-45 minutes  
**Pré-requis**: Phase 1 validée (BLK-001/002/003 résolus)

---

## 🎯 OBJECTIF

Déployer Phase 2 "Extension contrôlée des accès" en one-shot :
- **18 endpoints MCP** (Drive, Apps Script, Cloud Run, Secrets, Web, Terminal)
- **READ_ONLY par défaut** + WRITE gouverné (DRY_RUN → APPLY)
- **Journalisation obligatoire** (MEMORY_LOG + run_id)
- **Redaction systématique** (secrets, emails, tokens, IDs)
- **Un seul GO** pour actions WRITE

---

## 📋 PLAN D'EXÉCUTION (5 ÉTAPES)

### ÉTAPE 1 : Configuration GCP (15 min)
### ÉTAPE 2 : Configuration Hub (10 min)
### ÉTAPE 3 : Déploiement Backend (5 min)
### ÉTAPE 4 : Tests & Validation (20 min)
### ÉTAPE 5 : Documentation & GO PROD (5 min)

---

## 🚀 ÉTAPE 1 : CONFIGURATION GCP (15 min)

### 1.1 Activer APIs GCP (2 min)

```bash
# Console GCP → APIs & Services → Enable APIs
# Ou via gcloud CLI:

gcloud services enable drive.googleapis.com --project=box-magique-gp-prod
gcloud services enable script.googleapis.com --project=box-magique-gp-prod
gcloud services enable run.googleapis.com --project=box-magique-gp-prod
gcloud services enable logging.googleapis.com --project=box-magique-gp-prod
gcloud services enable secretmanager.googleapis.com --project=box-magique-gp-prod
gcloud services enable cloudresourcemanager.googleapis.com --project=box-magique-gp-prod
gcloud services enable iamcredentials.googleapis.com --project=box-magique-gp-prod
```

**Vérification** :
```bash
gcloud services list --enabled --project=box-magique-gp-prod | grep -E 'drive|script|run|logging|secretmanager'
```
✅ Doit retourner 5 lignes.

---

### 1.2 Configurer Service Account Permissions (5 min)

**Service Account** : `mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com`

```bash
# 1. Drive Read-Only
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/drive.readonly"

# 2. Apps Script Reader
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/script.reader"

# 3. Cloud Run Viewer
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/run.viewer"

# 4. Cloud Logging Viewer
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/logging.viewer"

# 5. Secret Manager Accessor
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 6. Secret Manager Admin (pour create/rotate)
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.admin"
```

**Vérification** :
```bash
gcloud projects get-iam-policy box-magique-gp-prod \
  --flatten="bindings[].members" \
  --filter="bindings.members:mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com" \
  --format="table(bindings.role)"
```
✅ Doit retourner 6 roles.

---

### 1.3 Partager Folder Drive ARCHIVES (3 min)

1. **Ouvrir Drive** → Folder `ARCHIVES`
2. **Clic droit** → "Partager"
3. **Ajouter** : `mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com`
4. **Permission** : **Lecteur** (Read-only)
5. **Notification** : ❌ Désactiver
6. **Récupérer Folder ID** :
   - URL : `https://drive.google.com/drive/folders/1ABC123...`
   - Copier : `1ABC123...`

✅ Folder ID : `_____________________` (noter ici)

---

### 1.4 Créer Secret API Key (5 min)

```bash
# Générer API Key forte
API_KEY=$(openssl rand -hex 32)
echo "Generated API Key: $API_KEY"

# Créer secret
echo -n "$API_KEY" | \
  gcloud secrets create mcp-api-key \
  --project=box-magique-gp-prod \
  --replication-policy="automatic" \
  --labels="env=staging,service=mcp-proxy" \
  --data-file=-

# Récupérer reference
gcloud secrets versions list mcp-api-key --project=box-magique-gp-prod
```

**Output attendu** :
```
projects/box-magique-gp-prod/secrets/mcp-api-key/versions/1
```

✅ Secret Reference : `projects/box-magique-gp-prod/secrets/mcp-api-key/versions/latest`

---

## 📝 ÉTAPE 2 : CONFIGURATION HUB (10 min)

### 2.1 Ouvrir Apps Script Editor (1 min)

1. **Ouvrir HUB Spreadsheet** (IAPF Memory Hub)
2. **Menu** : Extensions → Apps Script
3. **Vérifier fichiers existants** : G00 à G15

---

### 2.2 Ajouter Nouveaux Fichiers (5 min)

#### Fichier 1 : G16_MCP_ACTIONS_EXTENDED.gs

1. **Créer nouveau fichier** : Bouton "+" → Script file
2. **Nom** : `G16_MCP_ACTIONS_EXTENDED.gs`
3. **Copier contenu** depuis :
   ```
   GitHub: box-magic-ocr-intelligent/HUB_COMPLET/G16_MCP_ACTIONS_EXTENDED.gs
   ```
4. **Sauvegarder** (Ctrl+S)

#### Fichier 2 : G17_MCP_HTTP_CLIENT_EXTENDED.gs

1. **Créer nouveau fichier** : Bouton "+" → Script file
2. **Nom** : `G17_MCP_HTTP_CLIENT_EXTENDED.gs`
3. **Copier contenu** depuis :
   ```
   GitHub: box-magic-ocr-intelligent/HUB_COMPLET/G17_MCP_HTTP_CLIENT_EXTENDED.gs
   ```
4. **Sauvegarder** (Ctrl+S)

---

### 2.3 Modifier Fichiers Existants (2 min)

#### Modifier G01_UI_MENU.gs

1. **Ouvrir** : `G01_UI_MENU.gs`
2. **Chercher ligne** : `const mcpMenu = ui.createMenu("MCP Cockpit")`
3. **Ajouter APRÈS ligne 33** (avant `// --- Menu principal`) :

```javascript
// --- Sous-menu Actions MCP Phase 2 (18 endpoints)
const actionsMcpMenu = ui.createMenu("Actions MCP")
  .addItem("📁 Drive — List Tree", "MCP_ACTION_driveListTree")
  .addItem("📄 Drive — File Metadata", "MCP_ACTION_driveFileMetadata")
  .addItem("🔍 Drive — Search", "MCP_ACTION_driveSearch")
  .addSeparator()
  .addItem("📜 Apps Script — Deployments", "MCP_ACTION_appsScriptDeployments")
  .addItem("🏗️ Apps Script — Structure", "MCP_ACTION_appsScriptStructure")
  .addSeparator()
  .addItem("☁️ Cloud Run — Service Status", "MCP_ACTION_cloudRunServiceStatus")
  .addSeparator()
  .addItem("🔐 Secret Manager — List", "MCP_ACTION_secretsList")
  .addItem("🔑 Secret Manager — Get Reference", "MCP_ACTION_secretGetReference")
  .addItem("➕ Secret Manager — Create (DRY_RUN)", "MCP_ACTION_secretCreateDryRun")
  .addItem("✅ Secret Manager — Create (APPLY)", "MCP_ACTION_secretCreateApply")
  .addSeparator()
  .addItem("🌐 Web — Search", "MCP_ACTION_webSearch")
  .addSeparator()
  .addItem("💻 Terminal — Run (READ_ONLY)", "MCP_ACTION_terminalRunReadOnly");
```

4. **Modifier ligne 52** (avant `.addToUi()`) :

```javascript
  .addSubMenu(mcpMenu)
  .addSubMenu(actionsMcpMenu)  // <-- AJOUTER CETTE LIGNE
  .addSeparator()
  .addItem("Ouvrir LOGS", "IAPF_uiOpenLogs")
  .addToUi();
```

5. **Sauvegarder** (Ctrl+S)

---

### 2.4 Modifier appsscript.json (2 min)

1. **Ouvrir** : `appsscript.json` (panneau gauche)
2. **Remplacer** `oauthScopes` par :

```json
{
  "timeZone": "Europe/Paris",
  "dependencies": {},
  "exceptionLogging": "STACKDRIVER",
  "runtimeVersion": "V8",
  "oauthScopes": [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/script.projects.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/cloud-platform.read-only",
    "https://www.googleapis.com/auth/script.external_request"
  ]
}
```

3. **Sauvegarder** (Ctrl+S)

---

### 2.5 Ajouter Clés SETTINGS (2 min)

1. **Retour au Spreadsheet** : Onglet `SETTINGS`
2. **Ajouter 8 nouvelles lignes** :

| Clé | Valeur | Description |
|-----|--------|-------------|
| `mcp_api_key` | `projects/box-magique-gp-prod/secrets/mcp-api-key/versions/latest` | Secret reference |
| `mcp_gcp_project_id` | `box-magique-gp-prod` | Projet GCP |
| `mcp_gcp_region` | `us-central1` | Région GCP |
| `mcp_cloud_run_service_name` | `mcp-memory-proxy` | Nom service |
| `mcp_environment` | `STAGING` | Environnement |
| `mcp_allowed_domains` | `googleapis.com,github.com,genspark.ai` | Domaines allowlist |
| `mcp_web_quota` | `100` | Quota web/jour |
| `mcp_terminal_quota` | `20` | Quota terminal/jour |
| `archives_folder_id` | `[FOLDER_ID de l'étape 1.3]` | Folder ARCHIVES |

3. **Alternative automatique** : Apps Script Editor → Exécuter fonction `SETUP_addPhase2Settings()`

---

## 🔧 ÉTAPE 3 : DÉPLOIEMENT BACKEND (5 min)

### Option A : Via Console Cloud Run (Recommandé)

1. **Console GCP** → Cloud Run → Service `mcp-memory-proxy`
2. **Edit & Deploy New Revision**
3. **Variables d'environnement** → Ajouter :

```
MCP_ENVIRONMENT=STAGING
MCP_GCP_PROJECT_ID=box-magique-gp-prod
MCP_GCP_REGION=us-central1
MCP_CLOUD_RUN_SERVICE_NAME=mcp-memory-proxy
MCP_ARCHIVES_FOLDER_ID=[FOLDER_ID étape 1.3]
MCP_WEB_ALLOWED_DOMAINS=googleapis.com,github.com,genspark.ai
MCP_WEB_SEARCH_QUOTA=100
MCP_TERMINAL_QUOTA=20
```

4. **Deploy** (durée : ~3 min)

---

### Option B : Via gcloud CLI

```bash
cd /home/user/webapp/memory-proxy

# Deploy avec nouvelles variables
gcloud run services update mcp-memory-proxy \
  --region us-central1 \
  --project box-magique-gp-prod \
  --set-env-vars "MCP_ENVIRONMENT=STAGING,MCP_GCP_PROJECT_ID=box-magique-gp-prod,MCP_GCP_REGION=us-central1,MCP_ARCHIVES_FOLDER_ID=[FOLDER_ID],MCP_WEB_ALLOWED_DOMAINS=googleapis.com;github.com;genspark.ai,MCP_WEB_SEARCH_QUOTA=100,MCP_TERMINAL_QUOTA=20"
```

---

### Vérification Healthcheck

```bash
curl https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app/health
```

**Attendu** :
```json
{
  "status": "ok",
  "version": "3.0.5",
  "environment": "STAGING",
  "build_date": "2026-02-20T19:00:00Z",
  "apis_enabled": ["drive", "apps_script", "cloud_run", "logging", "secrets", "web", "terminal"]
}
```

✅ Health OK

---

## ✅ ÉTAPE 4 : TESTS & VALIDATION (20 min)

### 4.1 Test Menu UI (2 min)

1. **Recharger Spreadsheet** (F5)
2. **Menu IAPF Memory** → Vérifier sous-menu **"Actions MCP"**
3. **Compter entrées** : 14 items (Drive 3, Apps Script 2, Cloud Run 1, Secrets 4, Web 1, Terminal 1)

✅ Menu visible

---

### 4.2 Réautorisation OAuth (3 min)

1. **Menu** : Actions MCP → **Drive — Search**
2. **Popup Google OAuth** : "Le script demande de nouvelles autorisations"
3. **Cliquer** : "Examiner les autorisations"
4. **Sélectionner compte** : Votre compte Google
5. **Autoriser** toutes les permissions (Spreadsheets, Drive, Script, Cloud)

✅ OAuth autorisé

---

### 4.3 Tests Drive (5 min)

#### Test 1 : Drive List Tree

1. **Menu** : Actions MCP → **Drive — List Tree**
2. **Prompt** : Entrer Folder ID de ARCHIVES (étape 1.3)
3. **Résultat attendu** :
   ```
   ✅ MCP Drive — List Tree OK
   run_id: drive_tree_abc123...
   Folder: ARCHIVES
   Items: 45
   
   Voir MEMORY_LOG pour détails
   ```

✅ Drive List Tree OK  
run_id : `_______________`

#### Test 2 : Drive Search

1. **Menu** : Actions MCP → **Drive — Search**
2. **Prompt** : Entrer "IAPF"
3. **Résultat attendu** : Popup avec nb résultats + run_id

✅ Drive Search OK  
run_id : `_______________`

---

### 4.4 Tests Apps Script (3 min)

#### Test 1 : Apps Script Deployments

1. **Menu** : Actions MCP → **Apps Script — Deployments**
2. **Résultat attendu** : Liste déploiements avec run_id

✅ Apps Script Deployments OK  
run_id : `_______________`

---

### 4.5 Tests Secret Manager (5 min) — CRITICAL

#### Test 1 : List Secrets

1. **Menu** : Actions MCP → **Secret Manager — List**
2. **Vérifier popup** :
   ```
   ✅ MCP Secret Manager — List OK
   run_id: secrets_list_xyz...
   Projet: box-magique-gp-prod
   Secrets: 3
   
   ⚠️ Valeurs JAMAIS retournées (seulement métadonnées)
   ```

✅ Secrets List OK + Warning visible  
run_id : `_______________`

#### Test 2 : Get Reference

1. **Menu** : Actions MCP → **Secret Manager — Get Reference**
2. **Prompt** : Entrer "mcp-api-key"
3. **Vérifier popup** :
   ```
   Reference: projects/box-magique-gp-prod/secrets/mcp-api-key/versions/1
   ⚠️ Valeur: [REDACTED] (jamais retournée)
   ```

✅ Reference OK + [REDACTED]  
run_id : `_______________`

#### Test 3 : Create Secret DRY_RUN

1. **Menu** : Actions MCP → **Secret Manager — Create (DRY_RUN)**
2. **Prompt** : Entrer "test-secret-phase2"
3. **Vérifier popup** :
   ```
   Mode: DRY_RUN
   ⚠️ DRY_RUN: Secret 'test-secret-phase2' would be created (not applied)
   ```

✅ DRY_RUN OK + Message clair  
run_id : `_______________`

#### Test 4 : Create Secret APPLY

1. **Menu** : Actions MCP → **Secret Manager — Create (APPLY)**
2. **Prompt Secret ID** : Entrer "test-secret-phase2"
3. **Prompt Value** : Entrer "test_value_phase2_validation"
4. **Popup GO Confirmation** :
   ```
   ⚠️ WRITE_APPLY
   
   Domaine: Secret Manager
   Action: Create secret "test-secret-phase2"
   Env: STAGING
   
   Cette action créera le secret réellement.
   
   Continuer avec WRITE_APPLY?
   ```
5. **Cliquer** : YES
6. **Vérifier popup résultat** :
   ```
   ✅ MCP Secret Manager — Create APPLIED ✅
   Mode: APPLIED
   Reference: projects/.../secrets/test-secret-phase2/versions/1
   
   Stocker cette référence dans SETTINGS
   ```

✅ APPLY OK + GO Confirmation obligatoire  
run_id : `_______________`  
Secret Created ID : `test-secret-phase2`

---

### 4.6 Vérifier MEMORY_LOG (2 min)

1. **Onglet MEMORY_LOG**
2. **Vérifier dernières lignes** :
   - 1 ligne par action testée
   - Colonnes : timestamp, type (MCP_ACTION), title, details, author, source, tags, **run_id**

✅ MEMORY_LOG écrit pour toutes actions (8 lignes)

---

### 4.7 Vérifier Redaction (2 min)

1. **Onglet MEMORY_LOG** : Chercher patterns `[REDACTED]`, `[REDACTED_EMAIL]`, `[REDACTED_TOKEN]`
2. **Onglet LOGS_SYSTEM** : Vérifier aucun secret cleartext

✅ Aucun secret cleartext dans logs

---

## 📊 ÉTAPE 5 : DOCUMENTATION & GO PROD (5 min)

### 5.1 Remplir Checklist Validation (3 min)

1. **Ouvrir fichier** : `PHASE2_CHECKLIST_VALIDATION.md`
2. **Remplir Status** : ✅ OK / ❌ KO pour chaque critère (58 total)
3. **Calculer Score** :
   ```
   Score = (Nb OK / 58) * 100
   ```

✅ Score : `_____%` (minimum 90% = 52/58 pour GO PROD)

---

### 5.2 Décision GO / NO-GO PROD

| Condition | Score | Critères CRITICAL | Décision |
|-----------|-------|-------------------|----------|
| GO PROD | ≥ 90% | Tous ✅ | ✅ Bascule PROD |
| GO STAGING ONLY | 70-89% | 1-2 ❌ | ⏸️ Reste STAGING + fixes |
| NO-GO | < 70% | ≥ 3 ❌ | ❌ Rollback + audit |

**Votre Score** : `_____%`  
**Critères CRITICAL KO** : `____` / 15  
**Décision** : ☐ GO PROD  ☐ GO STAGING  ☐ NO-GO

---

### 5.3 Bascule PROD (si GO) (2 min)

Si score ≥ 90% ET tous critères CRITICAL = ✅ :

1. **Cloud Run** : Edit Service → Variable `MCP_ENVIRONMENT=PROD` → Deploy
2. **SETTINGS Sheet** : Modifier `mcp_environment` → `PROD`
3. **Notifier équipe** : "Phase 2 GO PROD validé"

✅ PROD activé

---

## 🎉 LIVRAISON COMPLÈTE

### Fichiers GitHub

- ✅ `HUB_COMPLET/G16_MCP_ACTIONS_EXTENDED.gs` (512 lignes)
- ✅ `HUB_COMPLET/G17_MCP_HTTP_CLIENT_EXTENDED.gs` (450 lignes)
- ✅ `HUB_COMPLET/G01_UI_MENU.gs` (modifié, menu Actions MCP)
- ✅ `memory-proxy/app/phase2_endpoints.py` (619 lignes)
- ✅ `memory-proxy/app/governance.py` (150 lignes)
- ✅ `memory-proxy/app/redaction.py` (100 lignes)
- ✅ `PHASE2_SPEC_ENDPOINTS_MCP.md` (28 KB spec complète)
- ✅ `PHASE2_RESUME_EXECUTIF.md` (19 KB résumé)
- ✅ `PHASE2_CONFIG_ONESHOT.md` (14 KB config)
- ✅ `PHASE2_CHECKLIST_VALIDATION.md` (16 KB checklist)
- ✅ `PHASE2_INSTRUCTIONS_FINALES.md` (ce fichier)

### Métriques Phase 2

- **18 endpoints** : Drive 4, Apps Script 4, Cloud Run 3, Secrets 4, Web 2, Terminal 1
- **READ_ONLY** : 15/18 endpoints (83%)
- **WRITE gouverné** : 3/18 endpoints (DRY_RUN → APPLY avec GO)
- **Run_id traçable** : 100% des actions
- **Redaction** : 100% des logs (secrets, emails, tokens, IDs)
- **Pagination** : Drive ≤200, Apps Script ≤50, Logging ≤1000
- **Quotas** : Web 100/jour, Terminal 20/jour

### Secrets Créés

| Secret ID | Type | Reference | Usage |
|-----------|------|-----------|-------|
| `mcp-api-key` | API Key | `projects/.../secrets/mcp-api-key/versions/latest` | Auth Hub → Proxy |
| `test-secret-phase2` | Test | `projects/.../secrets/test-secret-phase2/versions/1` | Validation Phase 2 |

Stocker ces références dans `SETTINGS` Sheet.

---

## 📞 SUPPORT

### En Cas de Problème

1. **Logs Backend** : Cloud Run → Logs → Filter "ERROR"
2. **Logs Hub** : LOGS_SYSTEM + ERRORS sheets
3. **MEMORY_LOG** : Dernières actions avec run_id
4. **GitHub Issues** : box-magic-ocr-intelligent/issues

### Contacts

- **Phase 2 Lead** : MCP Team
- **GitHub** : https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent
- **Checklist** : PHASE2_CHECKLIST_VALIDATION.md

---

## ✅ CHECKLIST FINALE

- [ ] **Étape 1** : GCP configuré (APIs, SA, Drive, Secrets) — 15 min
- [ ] **Étape 2** : Hub configuré (G16, G17, SETTINGS) — 10 min
- [ ] **Étape 3** : Backend déployé (Cloud Run + vars) — 5 min
- [ ] **Étape 4** : Tests validés (8 actions, MEMORY_LOG OK) — 20 min
- [ ] **Étape 5** : Score ≥ 90% + GO PROD décision — 5 min

**Total** : 35-45 minutes  
**Score final** : `_____%` / 100%  
**Status** : ☐ STAGING  ☐ PROD  ☐ ROLLBACK

---

**Bravo Élia ! Phase 2 terminée. MCP opérationnel avec accès contrôlé à 6 domaines Google. 🎉**

---

**Dernière mise à jour** : 2026-02-20 19:30 UTC  
**Version** : 1.0 Final  
**Auteur** : MCP Phase 2 Team
