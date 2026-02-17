# 🔍 LOGS PRODUCTION - INSTRUCTIONS MANUELLES

**Date:** 2026-02-17 22:35 UTC  
**Status:** ⚠️ **Accès programmatique bloqué - Validation manuelle requise**

---

## ❌ PROBLÈME

Le service account `genspark-deploy-temp@box-magique-gp-prod.iam.gserviceaccount.com` utilisé pour le déploiement **n'a pas** les permissions nécessaires pour lire les logs Cloud Logging.

```
ERROR: PERMISSION_DENIED: Permission denied for all log views
```

---

## 🎯 OBJECTIF VALIDATION GO/NO-GO

Prouver que le job MCP production utilise **ProxyTool** pour appeler `/sheets/*` avec l'API Key.

**Critères GO:**
- ✅ Log `[ProxyTool] Initialized with proxy URL`
- ✅ Log `[ProxyTool] API Key loaded: YES` (valeur masquée)
- ✅ Log `[ProxyTool] GET /sheets/SETTINGS?limit=10`
- ✅ Log `[ProxyTool] Response: HTTP 200`
- ✅ (Optionnel) Log `[ProxyTool] GET /sheets/NOPE → HTTP 404, correlation_id`

---

## 📋 MÉTHODE 1 - Console Web GCP (Recommandé)

### Étape 1: Accéder à Cloud Logging

1. Ouvrir la console GCP: https://console.cloud.google.com
2. Sélectionner le projet: **box-magique-gp-prod** (ID: 522732657254)
3. Naviguer vers **Logging** → **Logs Explorer**

### Étape 2: Configurer le filtre

Dans l'éditeur de requête, copier-coller:

```
resource.type="cloud_run_job"
resource.labels.job_name="mcp-cockpit-iapf-healthcheck"
resource.labels.location="us-central1"
timestamp>="2026-02-17T22:18:30Z"
timestamp<="2026-02-17T22:25:00Z"
```

**OU** filtrer par texte:

```
resource.type="cloud_run_job"
resource.labels.job_name="mcp-cockpit-iapf-healthcheck"
"ProxyTool"
```

### Étape 3: Identifier l'exécution

Chercher les logs de l'exécution: **mcp-cockpit-iapf-healthcheck-89sx5**

**Timestamp d'exécution:**
- Start: 2026-02-17T22:19:03Z
- End: 2026-02-17T22:21:30Z (approx)

### Étape 4: Extraire les logs ProxyTool

Rechercher dans les logs les lignes contenant:
- `ProxyTool`
- `/sheets/SETTINGS`
- `limit=10`
- `HTTP 200`
- `correlation_id`

### Étape 5: Exporter en JSON

1. Cliquer sur **Actions** → **Download logs**
2. Format: **JSON**
3. Filtrer sur les logs contenant "ProxyTool"
4. Sauvegarder le fichier

---

## 📋 MÉTHODE 2 - Commande gcloud (Avec compte admin)

**Prérequis:** Compte GCP avec rôle `roles/logging.viewer` ou `roles/owner`.

```bash
# Se connecter avec compte admin
gcloud auth login

# Configurer le projet
gcloud config set project box-magique-gp-prod

# Récupérer les logs (JSON)
gcloud logging read \
  "resource.labels.job_name=mcp-cockpit-iapf-healthcheck AND \
   resource.labels.location=us-central1 AND \
   timestamp>=\"2026-02-17T22:18:30Z\" AND \
   timestamp<=\"2026-02-17T22:25:00Z\"" \
  --limit=200 \
  --format=json \
  --project=box-magique-gp-prod \
  > mcp_job_execution_89sx5_logs.json

# Filtrer sur ProxyTool
cat mcp_job_execution_89sx5_logs.json | \
  jq -r '.[] | select(.jsonPayload.message | contains("ProxyTool")) | 
    {timestamp: .timestamp, severity: .severity, message: .jsonPayload.message}'
```

**Exemple de sortie attendue:**

```json
{
  "timestamp": "2026-02-17T22:19:05.123456Z",
  "severity": "INFO",
  "message": "[ProxyTool] Initialized with proxy URL https://mcp-memory-proxy-522732657254.us-central1.run.app"
}
{
  "timestamp": "2026-02-17T22:19:05.234567Z",
  "severity": "INFO",
  "message": "[ProxyTool] API Key loaded: YES (43 chars, SHA256: 7da15d80...)"
}
{
  "timestamp": "2026-02-17T22:19:06.345678Z",
  "severity": "INFO",
  "message": "[ProxyTool] GET /sheets/SETTINGS?limit=10"
}
{
  "timestamp": "2026-02-17T22:19:06.456789Z",
  "severity": "INFO",
  "message": "[ProxyTool] Response: HTTP 200, body={\"http_status\":200,\"sheet_name\":\"SETTINGS\",\"row_count\":8,...}"
}
{
  "timestamp": "2026-02-17T22:19:07.567890Z",
  "severity": "INFO",
  "message": "[ProxyTool] GET /sheets/NOPE?limit=1"
}
{
  "timestamp": "2026-02-17T22:19:07.678901Z",
  "severity": "INFO",
  "message": "[ProxyTool] Response: HTTP 404, correlation_id=70fa1a7e-5a30-489d-b134-f1f5fcd55fea"
}
```

---

## 📋 MÉTHODE 3 - API REST Cloud Logging

**Endpoint:**
```
POST https://logging.googleapis.com/v2/entries:list
```

**Body:**
```json
{
  "resourceNames": ["projects/box-magique-gp-prod"],
  "filter": "resource.type=\"cloud_run_job\" AND resource.labels.job_name=\"mcp-cockpit-iapf-healthcheck\" AND resource.labels.location=\"us-central1\" AND timestamp>=\"2026-02-17T22:18:30Z\"",
  "orderBy": "timestamp desc",
  "pageSize": 200
}
```

**Headers:**
```
Authorization: Bearer $(gcloud auth print-access-token)
Content-Type: application/json
```

---

## 🔐 SOLUTION PERMANENTE - Ajouter Permission Logging

**Option A: Via Console Web**

1. IAM & Admin → IAM
2. Trouver `genspark-deploy-temp@box-magique-gp-prod.iam.gserviceaccount.com`
3. Cliquer **Edit principal**
4. Ajouter rôle: **Logs Viewer** (`roles/logging.viewer`)
5. Sauvegarder

**Option B: Via gcloud (avec compte admin)**

```bash
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:genspark-deploy-temp@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/logging.viewer"
```

**Permissions incluses dans `roles/logging.viewer`:**
- `logging.logEntries.list` ✅
- `logging.logs.list` ✅
- `logging.logServiceIndexes.list` ✅
- `resourcemanager.projects.get` ✅

---

## 📊 INFORMATIONS CONTEXTUELLES

### Job Execution Details

```yaml
Job Name: mcp-cockpit-iapf-healthcheck
Execution ID: mcp-cockpit-iapf-healthcheck-89sx5
Region: us-central1
Image: gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0
Digest: sha256:3f94debfdc606e6c3f0bceec9078578c4187e8f64ccb5258533a7582583724c8
Git Commit: bf414ac

Status: COMPLETED
Start Time: 2026-02-17T22:19:03Z
End Time: 2026-02-17T22:21:30Z (approx)
Duration: ~2m30s

Environment:
  MCP_PROXY_API_KEY: ***MASKED*** (43 chars)
  ENVIRONMENT: PROD
  USE_METADATA_AUTH: true
```

### ProxyTool Configuration

```python
# mcp_cockpit/tools/proxy_tool.py
class ProxyTool:
    def __init__(self):
        self.proxy_url = "https://mcp-memory-proxy-522732657254.us-central1.run.app"
        self.api_key = os.environ.get("MCP_PROXY_API_KEY")
        
        logger.info(f"[ProxyTool] Initialized with proxy URL {self.proxy_url}")
        logger.info(f"[ProxyTool] API Key loaded: {'YES' if self.api_key else 'NO'}")
```

### Expected Log Patterns

**Pattern 1 - Initialization:**
```
[ProxyTool] Initialized with proxy URL https://mcp-memory-proxy-522732657254.us-central1.run.app
[ProxyTool] API Key loaded: YES
```

**Pattern 2 - GET Request:**
```
[ProxyTool] GET /sheets/SETTINGS?limit=10
[ProxyTool] Response: HTTP 200, body={...}
```

**Pattern 3 - Error Handling:**
```
[ProxyTool] GET /sheets/NOPE?limit=1
[ProxyTool] Response: HTTP 404, correlation_id=...
```

---

## ✅ CHECKLIST VALIDATION GO

Une fois les logs récupérés, vérifier:

- [ ] **Log ProxyTool initialization** présent
- [ ] **API Key loaded: YES** (valeur masquée dans logs)
- [ ] **GET /sheets/SETTINGS?limit=10** présent
- [ ] **Response: HTTP 200** confirmé
- [ ] **row_count** présent dans la réponse (valeur attendue: 8)
- [ ] (Optionnel) **GET /sheets/NOPE** → HTTP 404 avec correlation_id
- [ ] **Aucune erreur** de type `ConnectionError`, `401`, `403` sur les calls ProxyTool
- [ ] **API Key NON visible** en clair dans les logs (doit être masquée)

---

## 🚨 CRITÈRES NO-GO

Si les logs montrent:

- ❌ Aucune trace de `[ProxyTool]` → Code non déployé
- ❌ `API Key loaded: NO` → Variable d'environnement manquante
- ❌ `ConnectionError` ou `Timeout` → Proxy inaccessible
- ❌ `HTTP 401` ou `403` → API Key invalide ou non envoyée
- ❌ API Key visible en clair → Problème de masquage
- ❌ Erreur Python `ModuleNotFoundError: proxy_tool` → Build incorrect

---

## 📞 CONTACT & SUPPORT

**GitHub Repository:**
https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent

**Commits pertinents:**
- Code: `bf414ac` (MCP proxy tool integration + tests)
- Deploy: `6b4f7e8` (MCP job v1.1.0 production)

**Documentation:**
- `MCP_PROXY_DEPLOYMENT_FINAL.md` - Rapport de déploiement complet
- `MCP_PROXY_TOOL_DOC.md` - Documentation technique ProxyTool
- `test_mcp_integration.py` - Tests d'intégration (15/15 passed)

**Tests locaux:** 100% passed (15/15)
- Unit tests: 8/8 ✅
- Integration tests: 7/7 ✅

---

## 📝 NOTES IMPORTANTES

1. **Logs attendus dans Cloud Logging** (pas dans stdout/stderr du container)
2. **Filtrer sur `jsonPayload.message`** pour voir les logs applicatifs
3. **Execution ID exacte:** `mcp-cockpit-iapf-healthcheck-89sx5`
4. **Timezone:** Tous les timestamps sont en UTC
5. **Durée du job:** ~2m30s (2026-02-17 22:19:03 → 22:21:30)

---

## 🔄 PROCHAINES ÉTAPES

1. **Admin GCP** récupère les logs via Console Web ou gcloud (avec compte admin)
2. **Vérification** des patterns ProxyTool dans les logs
3. **Validation GO/NO-GO** selon la checklist ci-dessus
4. Si **GO** → Marquer le déploiement comme validé
5. Si **NO-GO** → Analyser les logs d'erreur et corriger

---

**Date:** 2026-02-17 22:35 UTC  
**Status:** ⏳ **En attente validation logs production**  
**Blocker:** Permissions `logging.logEntries.list` manquantes pour service account deploy
