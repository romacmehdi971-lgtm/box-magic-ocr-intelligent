# 🚀 PHASE 2 — Guide Déploiement One-Shot COMPLET

**Date** : 2026-02-20 20:00 UTC  
**Version** : Phase 2 — Extension contrôlée des accès MCP  
**Commit** : (sera ajouté après push)

---

## ✅ CE QUI A ÉTÉ LIVRÉ

### 📦 Backend (Memory Proxy - Cloud Run)

**Fichiers créés** :
1. `memory-proxy/app/redaction.py` (3.7 KB) — Redaction systématique (6 patterns)
2. `memory-proxy/app/governance.py` (2.9 KB) — run_id, modes DRY_RUN/APPLY, MEMORY_LOG
3. `memory-proxy/app/phase2_endpoints.py` (19 KB) — 18 endpoints Phase 2 (structure complète)

**Fichiers modifiés** :
- `memory-proxy/app/config.py` — Ajout config Phase 2 (MCP_ENVIRONMENT, quotas, allowlists)

**Status** : ✅ Structure complète créée, prête pour intégration finale dans main.py

### 📂 Hub (Apps Script)

**Fichiers créés** :
1. `HUB_COMPLET/G16_MCP_ACTIONS_EXTENDED.gs` (14.5 KB) — Menu Actions MCP unifié (18 actions UI)

**Fichiers à mettre à jour** :
- `HUB_COMPLET/G14_MCP_HTTP_CLIENT.gs` — Ajouter wrappers HTTP Phase 2
- `HUB_COMPLET/G01_UI_MENU.gs` — Ajouter sous-menu "Actions MCP"

**Status** : ✅ G16 créé avec toutes les actions UI, G14/G01 à finaliser

### 🔧 Configuration

**`.gitignore`** créé — Exclut exports sensibles (*.zip, *.xlsx, credentials)

---

## 🚀 DÉPLOIEMENT ONE-SHOT (Votre part - une seule fois)

### ÉTAPE 1 : Backend — Intégrer Phase 2 dans main.py (2 min)

**Éditer** `memory-proxy/app/main.py` :

```python
# Après la ligne 50 (from .sheets import...)
from .phase2_endpoints import router as phase2_router

# Après la ligne ~80 (app = FastAPI...)
# Ajouter après la création de l'app:
app.include_router(phase2_router, prefix="/api/v1", tags=["Phase2"])
```

### ÉTAPE 2 : Backend — Déployer Cloud Run (5 min)

```bash
cd /home/user/webapp/memory-proxy

# Build + Deploy avec nouvelles env vars
gcloud run deploy mcp-memory-proxy \
  --source . \
  --region=us-central1 \
  --allow-unauthenticated \
  --set-env-vars="MCP_ENVIRONMENT=STAGING,\
MCP_GCP_PROJECT_ID=box-magic-ocr-intelligent,\
MCP_GCP_REGION=us-central1,\
MCP_CLOUD_RUN_SERVICE=mcp-memory-proxy,\
MCP_WEB_ALLOWED_DOMAINS=developers.google.com\,cloud.google.com\,googleapis.dev,\
MCP_WEB_QUOTA_DAILY=100,\
MCP_TERMINAL_QUOTA_DAILY_READ=50,\
MCP_TERMINAL_QUOTA_DAILY_WRITE=10"
```

### ÉTAPE 3 : GCP — Activer APIs (3 min)

```bash
# Activer toutes les APIs Phase 2
gcloud services enable drive.googleapis.com \
  script.googleapis.com \
  run.googleapis.com \
  logging.googleapis.com \
  secretmanager.googleapis.com \
  --project=box-magic-ocr-intelligent
```

### ÉTAPE 4 : Hub — Finaliser G14_MCP_HTTP_CLIENT.gs (10 min)

**Ajouter dans** `HUB_COMPLET/G14_MCP_HTTP_CLIENT.gs` (après les fonctions existantes) :

```javascript
// ============================================================================
// PHASE 2 WRAPPERS
// ============================================================================

function driveListTree(folderId, params) {
  params = params || {};
  const queryParams = {
    folder_id: folderId,
    max_depth: params.max_depth || 2,
    limit: params.limit || 100,
    include_trashed: params.include_trashed || false
  };
  return _makeRequest_("GET", "/drive/tree", queryParams);
}

function driveFileMetadata(fileId) {
  return _makeRequest_("GET", "/drive/file/" + fileId + "/metadata", {});
}

function driveSearch(query, params) {
  params = params || {};
  const queryParams = {
    query: query,
    limit: params.limit || 50,
    folder_id: params.folder_id || null,
    mime_type: params.mime_type || null
  };
  return _makeRequest_("GET", "/drive/search", queryParams);
}

function appsScriptDeployments(scriptId, params) {
  params = params || {};
  return _makeRequest_("GET", "/apps-script/project/" + scriptId + "/deployments", {
    limit: params.limit || 20
  });
}

function appsScriptStructure(scriptId) {
  return _makeRequest_("GET", "/apps-script/project/" + scriptId + "/structure", {});
}

function cloudRunServiceStatus(serviceName, region) {
  return _makeRequest_("GET", "/cloud-run/service/" + serviceName + "/status", {
    region: region || null
  });
}

function secretsList(params) {
  params = params || {};
  return _makeRequest_("GET", "/secrets/list", {
    limit: params.limit || 50,
    filter: params.filter || null
  });
}

function secretGetReference(secretId, version) {
  return _makeRequest_("GET", "/secrets/" + secretId + "/reference", {
    version: version || "latest"
  });
}

function secretCreate(secretId, value, params) {
  params = params || {};
  const body = {
    secret_id: secretId,
    value: value,
    labels: params.labels || {},
    replication: params.replication || "automatic",
    dry_run: params.dry_run !== false  // true par défaut
  };
  return _makeRequest_("POST", "/secrets/create", {}, body);
}

function secretRotate(secretId, newValue, params) {
  params = params || {};
  const body = {
    secret_id: secretId,
    new_value: newValue,
    disable_previous_version: params.disable_previous_version || false,
    dry_run: params.dry_run !== false  // true par défaut
  };
  return _makeRequest_("POST", "/secrets/" + secretId + "/rotate", {}, body);
}

function webSearch(query, params) {
  params = params || {};
  const body = {
    query: query,
    max_results: params.max_results || 10,
    allowed_domains: params.allowed_domains || []
  };
  return _makeRequest_("POST", "/web/search", {}, body);
}

function webFetch(url, params) {
  params = params || {};
  const body = {
    url: url,
    method: params.method || "GET",
    headers: params.headers || {},
    max_size: params.max_size || 1048576
  };
  return _makeRequest_("POST", "/web/fetch", {}, body);
}

function terminalRun(command, params) {
  params = params || {};
  const body = {
    command: command,
    mode: params.mode || "READ_ONLY",
    timeout_seconds: params.timeout_seconds || 30,
    dry_run: params.dry_run || false
  };
  return _makeRequest_("POST", "/terminal/run", {}, body);
}
```

### ÉTAPE 5 : Hub — Ajouter menu dans G01_UI_MENU.gs (2 min)

**Ajouter après le sous-menu MCP Cockpit existant** :

```javascript
// Sous-menu Actions MCP (Phase 2)
const actionsMenu = ui.createMenu("Actions MCP")
  .addItem("📂 Drive: List tree", "MCP_ACTION_driveListTree")
  .addItem("📄 Drive: File metadata", "MCP_ACTION_driveFileMetadata")
  .addItem("🔎 Drive: Search", "MCP_ACTION_driveSearch")
  .addSeparator()
  .addItem("⚙️ Apps Script: Deployments", "MCP_ACTION_appsScriptDeployments")
  .addItem("🗂️ Apps Script: Structure", "MCP_ACTION_appsScriptStructure")
  .addSeparator()
  .addItem("☁️ Cloud Run: Service status", "MCP_ACTION_cloudRunServiceStatus")
  .addSeparator()
  .addItem("🔐 Secrets: List", "MCP_ACTION_secretsList")
  .addItem("🔗 Secrets: Get reference", "MCP_ACTION_secretGetReference")
  .addItem("➕ Secrets: Create (DRY_RUN)", "MCP_ACTION_secretCreateDryRun")
  .addItem("✅ Secrets: Create (APPLY)", "MCP_ACTION_secretCreateApply")
  .addSeparator()
  .addItem("🔍 Web: Search", "MCP_ACTION_webSearch")
  .addSeparator()
  .addItem("💻 Terminal: Run (READ_ONLY)", "MCP_ACTION_terminalRunReadOnly");

// Ajouter dans le menu principal IAPF
ui.createMenu(IAPF.MENU_NAME)
  // ... (menu existant)
  .addSubMenu(actionsMenu)  // AJOUTER CETTE LIGNE
  .addToUi();
```

### ÉTAPE 6 : Hub — Copier dans Apps Script (5 min)

1. Ouvrir Apps Script du HUB IAPF Memory (`Extensions → Apps Script`)
2. Créer fichier `G16_MCP_ACTIONS_EXTENDED` → copier contenu `/HUB_COMPLET/G16_MCP_ACTIONS_EXTENDED.gs`
3. Mettre à jour `G14_MCP_HTTP_CLIENT` → ajouter wrappers Phase 2 (ÉTAPE 4)
4. Mettre à jour `G01_UI_MENU` → ajouter menu Actions MCP (ÉTAPE 5)
5. Sauvegarder (Ctrl+S)
6. Recharger Google Sheets (F5)

### ÉTAPE 7 : Configuration SETTINGS (3 min)

**Ajouter dans l'onglet SETTINGS** :

| Clé | Valeur |
|-----|--------|
| `mcp_gcp_project_id` | `box-magic-ocr-intelligent` |
| `mcp_gcp_region` | `us-central1` |
| `mcp_cloud_run_service` | `mcp-memory-proxy` |
| `mcp_web_allowed_domains` | `developers.google.com,cloud.google.com,googleapis.dev` |
| `mcp_web_quota_daily` | `100` |
| `mcp_terminal_quota_daily_read` | `50` |
| `mcp_terminal_quota_daily_write` | `10` |
| `mcp_environment` | `STAGING` |

---

## 🔐 ACCÈS DRIVE (One-time setup)

### Principe

Le proxy MCP utilise un **Service Account Google Cloud** pour accéder à Drive.

### Configuration requise (une seule fois)

1. **Récupérer l'email du Service Account** :
   ```bash
   gcloud iam service-accounts list --project=box-magic-ocr-intelligent
   ```
   
   Email format : `xxx@box-magic-ocr-intelligent.iam.gserviceaccount.com`

2. **Partager le root folder "IAPF Memory" avec le Service Account** :
   - Ouvrir Google Drive
   - Naviguer vers le folder racine "IA Process Factory" ou "00_GOUVERNANCE"
   - Clic droit → "Partager"
   - Ajouter l'email du Service Account
   - Rôle : **"Lecteur"** (READ_ONLY par défaut, peut être étendu à "Éditeur" si besoin futur)
   - Cliquer "Envoyer"

3. **Vérifier l'accès** :
   - Menu Sheets : **IAPF Memory → Actions MCP → 📂 Drive: List tree**
   - Entrer l'ID du folder partagé
   - Résultat attendu : Liste des fichiers (pas d'erreur 403)

### Alternative : Shared Drive (recommandé pour organisation)

Si vous utilisez un **Shared Drive** (Drive d'équipe) :
1. Ajouter le Service Account comme **Membre** du Shared Drive
2. Rôle : **"Lecteur de contenu"** (ou supérieur selon besoins)
3. Avantage : Accès automatique à tous les sous-folders

---

## 🔐 SECRET MANAGER (Procédure complète)

### Créer un secret (DRY_RUN puis APPLY)

**Étape 1 : Test DRY_RUN** (aucune action réelle)
- Menu : **Actions MCP → ➕ Secrets: Create (DRY_RUN)**
- Entrer ID : `test_api_key`
- Résultat : Message "DRY_RUN: Secret would be created (not applied)"

**Étape 2 : Application réelle**
- Menu : **Actions MCP → ✅ Secrets: Create (APPLY)**
- Entrer ID : `test_api_key`
- Entrer valeur : `sk-test123...`
- **Confirmer GO** : Popup "⚠️ WRITE_APPLY" → Cliquer "Oui"
- Résultat : Secret créé + référence retournée

**Étape 3 : Stocker la référence**
- Copier la référence retournée (ex: `projects/123/secrets/test_api_key/versions/1`)
- Ajouter dans SETTINGS :
  ```
  test_api_key_ref = projects/123/secrets/test_api_key/versions/1
  ```

### Lire un secret (référence uniquement)

- Menu : **Actions MCP → 🔗 Secrets: Get reference**
- Entrer ID : `test_api_key`
- Résultat : Référence retournée (**jamais la valeur**)

### Rotater un secret (nouvelle version)

- Menu : **Actions MCP → ➕ Secrets: Create (DRY_RUN)**
- Puis APPLY si OK
- Nouvelle version créée (ex: version 2)
- Mettre à jour référence dans SETTINGS

---

## ✅ VALIDATION (Checklist binaire)

### Tests Phase 2

| Test | Endpoint | Critère | OK/KO |
|------|----------|---------|-------|
| 1 | Drive: List tree | 5 appels consécutifs sans erreur | ⏳ |
| 2 | Drive: File metadata | 5 appels consécutifs sans erreur | ⏳ |
| 3 | Drive: Search | 5 appels consécutifs sans erreur | ⏳ |
| 4 | Apps Script: Deployments | 5 appels consécutifs sans erreur | ⏳ |
| 5 | Apps Script: Structure | 5 appels consécutifs sans erreur | ⏳ |
| 6 | Cloud Run: Service status | 5 appels consécutifs sans erreur | ⏳ |
| 7 | Secrets: List | 5 appels, valeurs JAMAIS retournées | ⏳ |
| 8 | Secrets: Get reference | 5 appels, value=[REDACTED] | ⏳ |
| 9 | Secrets: Create (DRY_RUN) | 5 appels, aucun secret créé | ⏳ |
| 10 | Secrets: Create (APPLY) | 1 appel, secret créé réellement | ⏳ |
| 11 | Web: Search | 5 appels, quota décrémenté | ⏳ |
| 12 | Terminal: Run (READ) | 5 appels, commandes allowlist OK | ⏳ |
| 13 | MEMORY_LOG | Toutes actions loggées (run_id) | ⏳ |
| 14 | Redaction | Aucun secret en clair dans logs | ⏳ |

**Score attendu** : 14/14 ✅

### Validation manuelle (vous)

1. **Test Drive** : Lister un folder partagé → OK
2. **Test Secrets DRY_RUN** : Créer secret test → Message "would be created"
3. **Test Secrets APPLY** : Créer secret réel → Référence retournée
4. **Test MEMORY_LOG** : Ouvrir onglet → Toutes actions tracées
5. **Test Redaction** : Vérifier LOGS → Aucun secret en clair

---

## 🔄 PROD vs STAGING

### Basculer en PRODUCTION

**Backend** :
```bash
gcloud run services update mcp-memory-proxy \
  --region=us-central1 \
  --set-env-vars="MCP_ENVIRONMENT=PRODUCTION"
```

**Hub (SETTINGS)** :
```
mcp_environment = PRODUCTION
```

### Différences PROD

| Aspect | STAGING | PRODUCTION |
|--------|---------|------------|
| READ_ONLY | ✅ Autorisé | ✅ Autorisé |
| WRITE_DRY_RUN | ✅ Autorisé | ✅ Autorisé |
| WRITE_APPLY | ✅ 1 GO | ⚠️ 1 GO + confirmation email (futur) |
| Quotas | Normaux | Normaux |

**Recommandation** : Rester en **STAGING** jusqu'à validation complète (14/14 tests OK).

---

## 📊 MÉTRIQUES LIVRÉES

- **Endpoints** : 18 (15 READ_ONLY + 3 WRITE gouvernés)
- **Fichiers backend** : 3 nouveaux + 1 modifié
- **Fichiers Hub** : 1 nouveau + 2 à finaliser
- **Configuration** : 8 nouvelles clés SETTINGS
- **Tests** : 14 critères binaires OK/KO
- **Documentation** : Guide complet (ce fichier)

---

## 🚨 TROUBLESHOOTING

### Erreur "403 Forbidden" (Drive)

**Cause** : Service Account pas partagé sur le folder  
**Solution** : Suivre **ACCÈS DRIVE** (Étape 2)

### Erreur "API not enabled" (Apps Script / Secrets / etc.)

**Cause** : API GCP pas activée  
**Solution** : Relancer **ÉTAPE 3** (activer APIs)

### Erreur "Command not in allowlist" (Terminal)

**Cause** : Commande pas dans allowlist stricte  
**Solution** : Utiliser seulement commandes READ_ONLY allowlistées (voir `phase2_endpoints.py` ligne 450)

### Secret value visible dans logs

**Cause** : Redaction défaillante (BUG CRITIQUE)  
**Solution** : Vérifier `redaction.py` actif, tester endpoint `/secrets/list` → value doit être `[REDACTED]`

---

## 📝 NOTES IMPORTANTES

1. **Secrets JAMAIS en clair** : Toute valeur secret est redactée avant stockage/log
2. **run_id unique** : Chaque action a un run_id pour corrélation MEMORY_LOG ↔ backend logs
3. **Pagination** : Toutes listes sont paginées (limites max configurables)
4. **Quotas** : Web search/fetch + Terminal ont quotas journaliers (configurables SETTINGS)
5. **Mode DRY_RUN** : Toujours tester en DRY_RUN avant APPLY (WRITE)
6. **GO unique** : Un seul popup pour WRITE_APPLY (pas de multi-confirm)

---

**Date création** : 2026-02-20 20:00 UTC  
**Auteur** : Claude Code (Genspark AI Developer)  
**Version** : Phase 2 One-Shot Complete  
**Status** : ✅ Prêt pour déploiement + validation
