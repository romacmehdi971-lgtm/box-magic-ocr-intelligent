# PHASE 2 — CONFIGURATION COMPLÈTE ONE-SHOT
# Extension Contrôlée des Accès MCP
**Date**: 2026-02-20  
**Version**: 1.0  
**Service**: mcp-memory-proxy  
**Environment**: STAGING (default) → PROD (après validation)

---

## 📋 TABLE DES MATIÈRES

1. [Variables d'Environnement](#1-variables-denvironnement)
2. [APIs GCP à Activer](#2-apis-gcp-à-activer)
3. [Service Account & Permissions](#3-service-account--permissions)
4. [Apps Script OAuth Scopes](#4-apps-script-oauth-scopes)
5. [SETTINGS Sheet Configuration](#5-settings-sheet-configuration)
6. [Drive Access Model](#6-drive-access-model)
7. [Secrets Manager Setup](#7-secrets-manager-setup)
8. [Web & Terminal Allowlists](#8-web--terminal-allowlists)

---

## 1️⃣ VARIABLES D'ENVIRONNEMENT

### Cloud Run Environment Variables

Configurer dans la console Cloud Run → Service `mcp-memory-proxy` → Edit & Deploy → Variables & Secrets :

```bash
# Core Settings
GOOGLE_CLOUD_PROJECT="box-magique-gp-prod"
GCP_PROJECT_ID="box-magique-gp-prod"
GCP_REGION="us-central1"
SERVICE_ACCOUNT_KEY_PATH="/app/sa-key.json"

# Environment
MCP_ENVIRONMENT="STAGING"  # STAGING | PROD
READ_ONLY_MODE="false"
DRY_RUN_MODE="false"  # Default for proxy (Hub manages DRY_RUN)

# API Configuration
API_KEY="[SECRET_REFERENCE]"  # See Section 7
MCP_API_KEY="[SECRET_REFERENCE]"

# Phase 2 Specific
MCP_GCP_PROJECT_ID="box-magique-gp-prod"
MCP_GCP_REGION="us-central1"
MCP_CLOUD_RUN_SERVICE_NAME="mcp-memory-proxy"
MCP_ARCHIVES_FOLDER_ID="[DRIVE_FOLDER_ID]"

# Web Access
MCP_WEB_ALLOWED_DOMAINS="googleapis.com,github.com,genspark.ai"
MCP_WEB_SEARCH_QUOTA="100"  # Per day
MCP_WEB_FETCH_QUOTA="50"   # Per day

# Terminal Access
MCP_TERMINAL_ALLOWED_COMMANDS="gcloud run services describe,gcloud run services list,gcloud logging read,gcloud secrets list,gsutil ls"
MCP_TERMINAL_QUOTA="20"  # Per day
```

### Environment Variables File (.env pour local dev)

```bash
# .env file (NEVER commit this)
GOOGLE_CLOUD_PROJECT=box-magique-gp-prod
GCP_PROJECT_ID=box-magique-gp-prod
GCP_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./sa-key.json

MCP_ENVIRONMENT=STAGING
MCP_API_KEY=dev_key_change_me
API_KEY=dev_key_change_me

MCP_GCP_PROJECT_ID=box-magique-gp-prod
MCP_GCP_REGION=us-central1
MCP_CLOUD_RUN_SERVICE_NAME=mcp-memory-proxy
MCP_ARCHIVES_FOLDER_ID=1ABC123...

MCP_WEB_ALLOWED_DOMAINS=googleapis.com,github.com
MCP_WEB_SEARCH_QUOTA=100
MCP_WEB_FETCH_QUOTA=50

MCP_TERMINAL_ALLOWED_COMMANDS="gcloud run services describe,gcloud run services list,gcloud logging read,gcloud secrets list,gsutil ls"
MCP_TERMINAL_QUOTA=20
```

---

## 2️⃣ APIS GCP À ACTIVER

### Console GCP → APIs & Services → Enable APIs

Activer les 7 APIs suivantes (copier/coller les IDs):

```bash
# 1. Google Drive API
gcloud services enable drive.googleapis.com --project=box-magique-gp-prod

# 2. Apps Script API
gcloud services enable script.googleapis.com --project=box-magique-gp-prod

# 3. Cloud Run Admin API
gcloud services enable run.googleapis.com --project=box-magique-gp-prod

# 4. Cloud Logging API
gcloud services enable logging.googleapis.com --project=box-magique-gp-prod

# 5. Secret Manager API
gcloud services enable secretmanager.googleapis.com --project=box-magique-gp-prod

# 6. Cloud Resource Manager API (pour IAM)
gcloud services enable cloudresourcemanager.googleapis.com --project=box-magique-gp-prod

# 7. IAM Service Account Credentials API
gcloud services enable iamcredentials.googleapis.com --project=box-magique-gp-prod
```

### Vérifier Activation

```bash
gcloud services list --enabled --project=box-magique-gp-prod | grep -E 'drive|script|run|logging|secretmanager'
```

Doit retourner 5 lignes.

---

## 3️⃣ SERVICE ACCOUNT & PERMISSIONS

### Service Account Existant

```
Service Account: mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com
```

### Roles IAM Requis (6 roles)

```bash
# 1. Drive Read-Only
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/drive.readonly"

# 2. Apps Script Projects Reader
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

# 5. Secret Manager Secret Accessor (READ)
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 6. Secret Manager Admin (WRITE - pour create/rotate)
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.admin"
```

### Vérifier Permissions

```bash
gcloud projects get-iam-policy box-magique-gp-prod \
  --flatten="bindings[].members" \
  --filter="bindings.members:mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com" \
  --format="table(bindings.role)"
```

Doit retourner 6 roles.

---

## 4️⃣ APPS SCRIPT OAUTH SCOPES

### Fichier appsscript.json

Ajouter les scopes suivants dans le fichier `appsscript.json` du projet Apps Script HUB :

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

### Scopes Expliqués

- `spreadsheets` : Lecture/écriture MEMORY_LOG, SETTINGS
- `script.projects.readonly` : Lecture structure Apps Script (pour audit)
- `drive.readonly` : Lecture Drive (list tree, metadata)
- `cloud-platform.read-only` : Lecture Cloud Run status
- `script.external_request` : Appels HTTP vers proxy

### Autorisation Utilisateur

Après ajout des scopes, l'utilisateur (Élia) devra réautoriser le script au premier lancement :

1. Menu IAPF Memory → Actions MCP → [n'importe quelle action]
2. Popup Google OAuth : "Le script demande de nouvelles autorisations"
3. Cliquer "Examiner les autorisations" → "Autoriser"

---

## 5️⃣ SETTINGS SHEET CONFIGURATION

### Nouvelles Clés SETTINGS (8 clés Phase 2)

Ajouter dans l'onglet `SETTINGS` du HUB :

| Clé | Valeur | Type | Description |
|-----|--------|------|-------------|
| `mcp_api_key` | `[SECRET_REFERENCE]` | SECRET | API Key pour authentifier Hub → Proxy |
| `mcp_gcp_project_id` | `box-magique-gp-prod` | STRING | Projet GCP |
| `mcp_gcp_region` | `us-central1` | STRING | Région GCP |
| `mcp_cloud_run_service_name` | `mcp-memory-proxy` | STRING | Nom service Cloud Run |
| `mcp_environment` | `STAGING` | STRING | STAGING \| PROD |
| `mcp_allowed_domains` | `googleapis.com,github.com,genspark.ai` | STRING | Domaines allowlist web |
| `mcp_web_quota` | `100` | INTEGER | Quota recherche web (per day) |
| `mcp_terminal_quota` | `20` | INTEGER | Quota terminal (per day) |

### Script Ajout Automatique (optionnel)

```javascript
function SETUP_addPhase2Settings() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const settingsSheet = ss.getSheetByName("SETTINGS");
  
  const newSettings = [
    ["mcp_api_key", "[SECRET_REFERENCE]", "API Key pour MCP Proxy"],
    ["mcp_gcp_project_id", "box-magique-gp-prod", "Projet GCP"],
    ["mcp_gcp_region", "us-central1", "Région GCP"],
    ["mcp_cloud_run_service_name", "mcp-memory-proxy", "Nom service Cloud Run"],
    ["mcp_environment", "STAGING", "STAGING | PROD"],
    ["mcp_allowed_domains", "googleapis.com,github.com,genspark.ai", "Domaines allowlist"],
    ["mcp_web_quota", "100", "Quota web search per day"],
    ["mcp_terminal_quota", "20", "Quota terminal per day"]
  ];
  
  const lastRow = settingsSheet.getLastRow();
  settingsSheet.getRange(lastRow + 1, 1, newSettings.length, 3).setValues(newSettings);
  
  SpreadsheetApp.getUi().alert("Phase 2 Settings ajoutés");
}
```

---

## 6️⃣ DRIVE ACCESS MODEL

### Modèle Recommandé : **Folder Share**

#### Étapes

1. **Récupérer email Service Account** :
   ```
   mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com
   ```

2. **Partager folder ARCHIVES** :
   - Ouvrir Google Drive → Folder `ARCHIVES`
   - Clic droit → "Partager"
   - Ajouter : `mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com`
   - Permission : **Lecteur** (Read-only)
   - ✅ Envoyer notification : NON

3. **Récupérer Folder ID** :
   - Ouvrir folder ARCHIVES dans Drive
   - URL : `https://drive.google.com/drive/folders/1ABC123...`
   - Copier ID : `1ABC123...`

4. **Ajouter dans SETTINGS** :
   ```
   Clé: archives_folder_id
   Valeur: 1ABC123...
   ```

### Test d'Accès

```javascript
function TEST_driveAccess() {
  const folderId = "1ABC123..."; // archives_folder_id
  const response = MCP_HTTP.driveListTree(folderId, {limit: 10});
  
  if (response.ok) {
    Logger.log("✅ Drive access OK - " + response.total_items + " items");
    return true;
  } else {
    Logger.log("❌ Drive access FAILED - " + response.error);
    return false;
  }
}
```

---

## 7️⃣ SECRETS MANAGER SETUP

### Créer API Key Secret

```bash
# Créer secret pour API Key
echo -n "YOUR_STRONG_API_KEY_HERE" | \
  gcloud secrets create mcp-api-key \
  --project=box-magique-gp-prod \
  --replication-policy="automatic" \
  --data-file=-

# Récupérer reference
gcloud secrets versions list mcp-api-key --project=box-magique-gp-prod

# Output:
# projects/box-magique-gp-prod/secrets/mcp-api-key/versions/1
```

### Ajouter Reference dans SETTINGS

```
Clé: mcp_api_key
Valeur: projects/box-magique-gp-prod/secrets/mcp-api-key/versions/latest
```

### Service Account Secret Accessor

Déjà configuré dans Section 3 (role `secretmanager.secretAccessor`).

### Test Lecture Secret

```bash
gcloud secrets versions access latest \
  --secret="mcp-api-key" \
  --project=box-magique-gp-prod \
  --impersonate-service-account=mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com
```

Doit retourner la clé API (redacted dans logs).

### Créer Secrets Supplémentaires (optionnel)

```bash
# Secret test pour validation Phase 2
echo -n "test_value_phase2" | \
  gcloud secrets create test-secret-phase2 \
  --project=box-magique-gp-prod \
  --replication-policy="automatic" \
  --labels="env=staging,service=mcp-proxy" \
  --data-file=-
```

---

## 8️⃣ WEB & TERMINAL ALLOWLISTS

### Web Allowed Domains

```bash
# Domaines autorisés pour web/search et web/fetch
MCP_WEB_ALLOWED_DOMAINS="googleapis.com,github.com,genspark.ai,docs.google.com,cloud.google.com"
```

**Test** : Tenter fetch vers `example.com` (doit échouer) puis vers `github.com` (doit réussir).

### Terminal Allowed Commands

```bash
# Commandes READ_ONLY autorisées
MCP_TERMINAL_ALLOWED_COMMANDS="gcloud run services describe,gcloud run services list,gcloud logging read,gcloud secrets list,gcloud secrets versions list,gsutil ls,gsutil du"

# Commandes WRITE autorisées (DRY_RUN/APPLY)
MCP_TERMINAL_ALLOWED_COMMANDS_WRITE="gcloud run services update,gcloud secrets create,gcloud secrets versions add"
```

**Validation** :
- ✅ `gcloud run services describe mcp-memory-proxy --region=us-central1` → OK
- ❌ `rm -rf /tmp` → Bloqué (not in allowlist)

### Quotas Configuration

```javascript
// Dans SETTINGS
mcp_web_quota: 100         // 100 recherches web par jour
mcp_terminal_quota: 20     // 20 commandes terminal par jour
```

---

## 🚀 DÉPLOIEMENT COMPLET

### 1. Build & Deploy Backend

```bash
cd /home/user/webapp/memory-proxy

# Build Docker image
docker build -t gcr.io/box-magique-gp-prod/mcp-memory-proxy:phase2 .

# Push to GCR
docker push gcr.io/box-magique-gp-prod/mcp-memory-proxy:phase2

# Deploy to Cloud Run
gcloud run deploy mcp-memory-proxy \
  --image gcr.io/box-magique-gp-prod/mcp-memory-proxy:phase2 \
  --platform managed \
  --region us-central1 \
  --project box-magique-gp-prod \
  --service-account mcp-proxy@box-magique-gp-prod.iam.gserviceaccount.com \
  --set-env-vars "$(cat .env.prod | tr '\n' ',' | sed 's/,$//')" \
  --allow-unauthenticated
```

### 2. Deploy Hub Apps Script

1. Ouvrir Apps Script Editor : Extensions → Apps Script
2. Ajouter fichiers :
   - `G16_MCP_ACTIONS_EXTENDED.gs`
   - `G17_MCP_HTTP_CLIENT_EXTENDED.gs`
3. Modifier `G01_UI_MENU.gs` (ajouter menu "Actions MCP")
4. Modifier `appsscript.json` (ajouter OAuth scopes)
5. Sauvegarder (Ctrl+S)
6. Déployer : Deploy → New Deployment → Execute as "Me" → Who has access "Anyone"

### 3. Ajouter Clés SETTINGS

Exécuter `SETUP_addPhase2Settings()` dans Apps Script Editor.

### 4. Valider Healthcheck

```bash
curl https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app/health
```

Attendu :
```json
{
  "status": "ok",
  "version": "3.0.5-phase2",
  "environment": "STAGING",
  "apis_enabled": ["drive", "apps_script", "cloud_run", "logging", "secrets", "web", "terminal"]
}
```

---

## 📊 CHECKLIST POST-DÉPLOIEMENT

- [ ] 7 APIs GCP activées (Section 2)
- [ ] 6 roles IAM configurés (Section 3)
- [ ] 5 OAuth scopes dans appsscript.json (Section 4)
- [ ] 8 clés SETTINGS ajoutées (Section 5)
- [ ] Folder ARCHIVES partagé avec SA (Section 6)
- [ ] Secret `mcp-api-key` créé + reference dans SETTINGS (Section 7)
- [ ] Allowlists web + terminal configurées (Section 8)
- [ ] Backend déployé + healthcheck OK
- [ ] Hub menu "Actions MCP" visible
- [ ] Test Drive access OK
- [ ] Test Secret Manager list OK (sans valeurs)
- [ ] MEMORY_LOG écrit pour chaque action

**Durée totale** : ~35 minutes

---

**Dernière mise à jour** : 2026-02-20 19:00 UTC  
**Auteur** : MCP Team  
**Contact** : GitHub box-magic-ocr-intelligent
