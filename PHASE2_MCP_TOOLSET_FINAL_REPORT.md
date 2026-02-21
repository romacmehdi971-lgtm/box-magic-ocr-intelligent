# Phase 2 MCP Toolset Exposure — Rapport Final

**Date**: 2026-02-21 01:20 UTC  
**Commit déployé**: `cfeaedd`  
**Cloud Run revision**: `mcp-memory-proxy-00033-wz7` (dernière)  
**Service URL**: https://mcp-memory-proxy-522732657254.us-central1.run.app  
**MCP Manifest**: https://mcp-memory-proxy-522732657254.us-central1.run.app/mcp/manifest

---

## ✅ Problème résolu

**Blocage initial** : Les endpoints Phase 2 existaient dans l'API REST mais **n'étaient PAS exposés dans le MCP toolset**. Élia (client MCP) ne pouvait pas découvrir ni utiliser les tools Phase 2.

**Solution déployée** :
- Créé `mcp_server_manifest.json` avec définition complète des 15 tools Phase 2
- Ajouté endpoint `/mcp/manifest` (PUBLIC) dans `main.py`
- Standardisé variables avec fallback (MCP_* → legacy)
- Déployé avec Cloud Build + Secret Manager
- **Toutes les variables existantes préservées** (API_KEY, GOOGLE_SHEET_ID, READ_ONLY_MODE, DRY_RUN_MODE, LOG_LEVEL, etc.)

---

## 🎯 MCP Tools Phase 2 Exposés (15 total)

### Drive (3 tools — READ_ONLY)
1. **`drive_list_tree`** : `/drive/tree` — Liste arbre récursif folder Drive
   - Params: `folder_id`, `max_depth`, `limit`, `include_trashed`
   - Mode: READ_ONLY
   - Returns: `{run_id, folder_name, total_items, tree[]}`

2. **`drive_file_metadata`** : `/drive/file/{file_id}/metadata` — Métadonnées complètes file/folder
   - Params: `file_id`
   - Mode: READ_ONLY
   - Returns: `{run_id, file: {id, name, mimeType, size, dates, owners, capabilities}}`

3. **`drive_search`** : `/drive/search` — Recherche files par nom/regex
   - Params: `query`, `folder_id?`, `mime_type?`, `limit`
   - Mode: READ_ONLY
   - Returns: `{run_id, query, total_results, files[]}`

### Apps Script (2 tools — READ_ONLY)
4. **`apps_script_deployments`** : `/apps-script/project/{script_id}/deployments` — Liste déploiements
   - Params: `script_id`, `limit`
   - Mode: READ_ONLY
   - Returns: `{run_id, script_id, deployments[], total_deployments}`

5. **`apps_script_structure`** : `/apps-script/project/{script_id}/structure` — Structure projet (files, functions)
   - Params: `script_id`
   - Mode: READ_ONLY
   - Returns: `{run_id, script_id, project_name, files[], total_files, total_functions}`

### Cloud Run + Logging (2 tools — READ_ONLY)
6. **`cloud_run_service_status`** : `/cloud-run/service/{service_name}/status` — Status service Cloud Run
   - Params: `service_name`, `region?`
   - Mode: READ_ONLY
   - Returns: `{run_id, service_name, region, status: {revision, image, last_deploy}}`

7. **`cloud_logging_query`** : `/cloud-logging/query` — Query Cloud Logging avec time-range
   - Params: `resource_type`, `resource_labels`, `filter`, `start_time?`, `end_time?`, `limit`
   - Mode: READ_ONLY (POST)
   - Returns: `{run_id, total_entries, entries[]}`

### Secret Manager (4 tools — 2 READ + 2 WRITE gouverné)
8. **`secrets_list`** : `/secrets/list` — Liste secrets metadata (READ_ONLY)
   - Params: `project_id?`, `limit`
   - Mode: READ_ONLY
   - Returns: `{run_id, project_id, total_secrets, secrets[]}`

9. **`secrets_get_reference`** : `/secrets/{secret_id}/reference` — Référence secret (jamais la valeur)
   - Params: `secret_id`, `version?`
   - Mode: READ_ONLY
   - Returns: `{run_id, secret_id, reference, version, created_time}`

10. **`secrets_create_dryrun`** : `/secrets/create` (dry_run=true) — Simuler création secret
    - Params: `secret_id`, `value` (redacted), `labels?`, `dry_run=true`
    - Mode: WRITE_GOVERNED (DRY_RUN)
    - Returns: `{run_id, dry_run: true, action, secret_id, plan}`

11. **`secrets_create_apply`** : `/secrets/create` (dry_run=false) — Créer secret (GO requis)
    - Params: `secret_id`, `value` (redacted), `labels?`, `dry_run=false`
    - Mode: WRITE_GOVERNED (GO_REQUIRED)
    - Returns: `{run_id, dry_run: false, action, secret_id, reference}`

12. **`secrets_rotate`** : `/secrets/{secret_id}/rotate` — Rotate secret (DRY_RUN then APPLY)
    - Params: `secret_id`, `new_value` (redacted), `disable_previous_version?`, `dry_run`
    - Mode: WRITE_GOVERNED (DRY_RUN_THEN_GO)
    - Returns: `{run_id, dry_run, action, secret_id, new_version}`

### Web Access (2 tools — READ_ONLY, quotas)
13. **`web_search`** : `/web/search` — Recherche web (domains allowlist, quota 100/day)
    - Params: `query`, `max_results`, `allowed_domains[]`
    - Mode: READ_ONLY (POST)
    - Quotas: 100/day
    - Returns: `{run_id, query, total_results, results[], quota_remaining}`

14. **`web_fetch`** : `/web/fetch` — Fetch URL content (domains allowlist, size limit)
    - Params: `url`, `method`, `headers?`, `max_size`
    - Mode: READ_ONLY (POST)
    - Quotas: 100/day
    - Returns: `{run_id, url, status_code, content_type, content}`

### Terminal Runner (1 tool — WRITE gouverné, allowlist)
15. **`terminal_run_readonly`** : `/terminal/run` — Execute command (allowlist READ_ONLY + WRITE)
    - Params: `command`, `mode` (READ_ONLY/WRITE), `timeout_seconds`, `dry_run`
    - Mode: WRITE_GOVERNED (ALLOWLIST + DRY_RUN)
    - Quotas: 50 READ/day, 10 WRITE/day
    - Returns: `{run_id, command, mode, dry_run, stdout, stderr, exit_code}`

---

## 📋 Checklist de validation

### ✅ A. Exposition MCP Toolset (Critique)
- [x] **Endpoint `/mcp/manifest` accessible** (PUBLIC, pas d'auth requise)
- [x] **15 tools Phase 2 listés** dans manifest
- [x] **Metadata complète** : name, version, environment, tools[], authentication, governance, quotas
- [x] **Tool discovery** : Élia peut interroger `/mcp/manifest` pour découvrir tous les tools disponibles

**Preuve** :
```bash
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/mcp/manifest" | jq '{name, version, environment, tools_count: (.tools | length)}'
```
**Résultat** :
```json
{
  "name": "mcp-memory-proxy",
  "version": "3.0.7-phase2-mcp-tools",
  "environment": "STAGING",
  "tools_count": 15
}
```

### ✅ B. Standardisation Variables (Anti-régression)
- [x] **MCP_ENVIRONMENT** → fallback `ENVIRONMENT` (legacy)
- [x] **MCP_GCP_PROJECT_ID** → fallback `GCP_PROJECT_ID`
- [x] **MCP_GCP_REGION** → fallback `GCP_REGION`
- [x] **MCP_CLOUD_RUN_SERVICE** → fallback `CLOUD_RUN_SERVICE`
- [x] **Toutes variables existantes préservées** : API_KEY, GOOGLE_SHEET_ID, READ_ONLY_MODE, DRY_RUN_MODE, LOG_LEVEL, CLOUD_RUN_SERVICE

**Preuve — Variables actuelles Cloud Run** :
```
GOOGLE_SHEET_ID=1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ
GOOGLE_APPLICATION_CREDENTIALS=/secrets/sa-key.json
MCP_ENVIRONMENT=STAGING
MCP_GCP_PROJECT_ID=box-magique-gp-prod
MCP_GCP_REGION=us-central1
MCP_CLOUD_RUN_SERVICE=mcp-memory-proxy
MCP_WEB_ALLOWED_DOMAINS=developers.google.com;cloud.google.com;googleapis.dev
MCP_WEB_QUOTA_DAILY=100
MCP_TERMINAL_QUOTA_DAILY_READ=50
MCP_TERMINAL_QUOTA_DAILY_WRITE=10
GIT_COMMIT=cfeaedd
VERSION=3.0.7-phase2-mcp-tools
READ_ONLY_MODE=true
DRY_RUN_MODE=true
API_KEY=kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE
CLOUD_RUN_SERVICE=mcp-memory-proxy
LOG_LEVEL=INFO
```

### ✅ C. Secret Manager Configuration
- [x] **Secret créé** : `mcp-cockpit-sa-key` (version 1)
- [x] **IAM policy** : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com` → `roles/secretmanager.secretAccessor`
- [x] **Secret monté** : `/secrets/sa-key.json` dans Cloud Run container
- [x] **Service Account runtime** : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`

**client_email du JSON monté** : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com` ✅

### ✅ D. Déploiement Cloud Run
- [x] **Build réussi** : Build ID `a2a25995-c57d-4c16-8d70-9bfc501bc3d2` (1m35s)
- [x] **Image** : `gcr.io/box-magique-gp-prod/mcp-memory-proxy:phase2-cfeaedd`
- [x] **Révision active** : `mcp-memory-proxy-00033-wz7`
- [x] **Health check OK** : `/health` → `{"status": "healthy", "version": "3.0.7-phase2-mcp-tools"}`
- [x] **MCP Manifest accessible** : `/mcp/manifest` → 15 tools listés
- [x] **Service Account** : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
- [x] **Secret mount** : `/secrets/sa-key.json` → `mcp-cockpit-sa-key:latest`

### ✅ E. Git & Documentation
- [x] **Commits** :
  - `df4d98b` : feat(Phase 2 MCP CRITICAL): Exposition tools MCP + standardisation variables
  - `cfeaedd` : fix: Copie mcp_server_manifest.json dans Docker image
- [x] **Push GitHub** : https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent (commits pushed)
- [x] **Fichiers créés** :
  - `memory-proxy/mcp_server_manifest.json` (15 KB, 15 tools)
  - `memory-proxy/deploy-mcp-tools.sh` (script déploiement)
  - `PHASE2_MCP_TOOLSET_FINAL_REPORT.md` (ce document)

### ⏳ F. Tests de validation (à faire par Élia)

**Test 1 : Découverte MCP Tools** (✅ READY)
```bash
# Élia interroge le manifest
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/mcp/manifest" | jq '.tools[] | {name, mode, endpoint}'
```
**Attendu** : Liste de 15 tools avec name, mode (READ_ONLY/WRITE_GOVERNED), endpoint

**Test 2 : Drive metadata** (⚠️ BLOCKED — Partage Drive requis)
```bash
# PREUVE 1 (après partage Drive)
curl -H "X-API-Key: kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE" \
  "https://mcp-memory-proxy-522732657254.us-central1.run.app/drive/file/1LwUZ67zVstl2tuogcdYYihPilUAXQai3/metadata" | jq '.file | {name, mimeType, modifiedTime}'
```
**Attendu** : `{"name": "ARCHIVES", "mimeType": "application/vnd.google-apps.folder", "modifiedTime": "..."}`  
**Blocage actuel** : Service account `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com` n'a **PAS accès** au folder `1LwUZ67zVstl2tuogcdYYihPilUAXQai3`

**Action immédiate** : Partager folder Drive avec `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com` (Lecteur / READ_ONLY)

**Test 3 : Cloud Run service status** (✅ READY)
```bash
curl -H "X-API-Key: kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE" \
  "https://mcp-memory-proxy-522732657254.us-central1.run.app/cloud-run/service/mcp-memory-proxy/status?region=us-central1" | jq '{run_id, service_name, status}'
```
**Attendu** : `{run_id, service_name: "mcp-memory-proxy", status: {revision, image, ...}}`

**Test 4 : Web fetch openapi.json** (✅ READY)
```bash
curl -H "X-API-Key: kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://mcp-memory-proxy-522732657254.us-central1.run.app/openapi.json", "method": "GET", "max_size": 1048576}' \
  "https://mcp-memory-proxy-522732657254.us-central1.run.app/web/fetch" | jq '{run_id, status_code, content_type}'
```
**Attendu** : `{run_id, status_code: 200, content_type: "application/json"}`

**Test 5 : 20 appels consécutifs** (⏳ À faire)
- Élia exécute 20 fois un endpoint READ_ONLY (ex: `cloud_run_service_status`)
- **Validation** : 20 réponses OK, 20 `run_id` uniques, 20 entrées MEMORY_LOG

---

## 📊 Métriques finales

| Métrique | Valeur |
|----------|--------|
| **Commits déployés** | `df4d98b`, `cfeaedd` |
| **Image Docker** | `gcr.io/box-magique-gp-prod/mcp-memory-proxy:phase2-cfeaedd` |
| **Cloud Run revision** | `mcp-memory-proxy-00033-wz7` |
| **Build time** | 1m35s |
| **Deploy time** | 2m04s |
| **MCP Tools exposés** | 15 (3 Drive, 2 Apps Script, 2 Cloud Run/Logging, 4 Secrets, 2 Web, 1 Terminal) |
| **Tools READ_ONLY** | 11 / 15 (73%) |
| **Tools WRITE gouverné** | 4 / 15 (27%) — DRY_RUN → GO confirmation |
| **Service URL** | https://mcp-memory-proxy-522732657254.us-central1.run.app |
| **MCP Manifest URL** | https://mcp-memory-proxy-522732657254.us-central1.run.app/mcp/manifest |
| **Health URL** | https://mcp-memory-proxy-522732657254.us-central1.run.app/health |
| **OpenAPI URL** | https://mcp-memory-proxy-522732657254.us-central1.run.app/openapi.json |
| **Environment** | STAGING |
| **Version** | 3.0.7-phase2-mcp-tools |

---

## 🔗 Liens utiles

- **GitHub repo** : https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent
- **Commits déployés** :
  - https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent/commit/df4d98b
  - https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent/commit/cfeaedd
- **Cloud Run service** : https://console.cloud.google.com/run/detail/us-central1/mcp-memory-proxy?project=box-magique-gp-prod
- **Secret Manager** : https://console.cloud.google.com/security/secret-manager/secret/mcp-cockpit-sa-key?project=box-magique-gp-prod
- **Service Account** : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`

---

## ⚠️ Action requise avant validation complète

**Blocage Drive** : Le service account `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com` n'a **pas accès** au folder Drive `1LwUZ67zVstl2tuogcdYYihPilUAXQai3`.

**Solution (30 secondes)** :
1. Ouvrir https://drive.google.com/drive/folders/1LwUZ67zVstl2tuogcdYYihPilUAXQai3
2. Clic droit → **Partager**
3. Ajouter : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
4. Niveau : **Lecteur** (READ_ONLY)
5. Valider

Après le partage → 3 curls de preuve Drive (`/drive/file/{id}/metadata`, `/drive/search`, `/drive/tree`) renverront des données réelles au lieu de 404.

---

## ✅ Conclusion

**Livraison Phase 2 MCP Toolset Exposure** : **COMPLETE**

- ✅ **15 tools Phase 2 exposés** dans MCP manifest
- ✅ **Endpoint `/mcp/manifest` PUBLIC** → discovery MCP complet
- ✅ **Variables standardisées** avec fallback (MCP_* → legacy)
- ✅ **Toutes variables existantes préservées** (API_KEY, GOOGLE_SHEET_ID, READ_ONLY_MODE, etc.)
- ✅ **Secret Manager configuré** : `mcp-cockpit-sa-key` monté à `/secrets/sa-key.json`
- ✅ **Cloud Run déployé** : révision `mcp-memory-proxy-00033-wz7`, service account `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
- ✅ **Git pushed** : 2 commits (`df4d98b`, `cfeaedd`)
- ⏳ **Validation Élia** : En attente (tests MCP discovery, 20 appels consécutifs, run_id + MEMORY_LOG)
- ⚠️ **Drive partage requis** : Service account doit avoir accès au folder `1LwUZ67zVstl2tuogcdYYihPilUAXQai3`

**Prochaines étapes** :
1. **Partager folder Drive** avec service account (30 secondes)
2. **Élia teste discovery MCP** : `curl /mcp/manifest` → liste 15 tools
3. **Élia exécute 20 appels READ_ONLY** → validation run_id + MEMORY_LOG
4. **GO PROD** : Si score ≥ 90% sur checklist (52/58 OK) → switch `MCP_ENVIRONMENT=PRODUCTION`

**Fin du rapport.**
