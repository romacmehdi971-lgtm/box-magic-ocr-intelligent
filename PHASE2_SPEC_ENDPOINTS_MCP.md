# 🚀 PHASE 2 — Spécification Endpoints MCP (Extension contrôlée)

**Date** : 2026-02-20  
**Version** : Phase 2 — Extension observabilité et actions gouvernées  
**Source** : IAPF_HUB_EXPORT__20260220_150058.zip  
**Status** : ✅ Phase 1 validée (BLK-001/002/003 résolus)

---

## 🎯 OBJECTIF PHASE 2

Exposer via le proxy MCP les endpoints manquants (Drive / Apps Script / Cloud Run / Secrets / Web / Terminal) avec un cadre **sécurisé**, **gouverné** et **traçable**.

**Principes non négociables** :
- ✅ **READ_ONLY par défaut** partout
- ✅ **Journalisation obligatoire** (MEMORY_LOG + LOGS) avec `run_id` unique
- ✅ **Pagination + limites** partout (anti payload géant)
- ✅ **Redaction systématique** (tokens, secrets, emails, IDs sensibles)
- ✅ **Mode DRY_RUN** disponible pour toute action WRITE
- ✅ **Validation gouvernée** : un seul GO, pas 30 confirmations
- ✅ **Aucun secret en clair** dans le Hub : Secret Manager uniquement

---

## 📋 TABLE DES MATIÈRES

1. [A) Google Drive (Priorité 1)](#a-google-drive-priorit%C3%A9-1)
2. [B) Apps Script (Priorité 2)](#b-apps-script-priorit%C3%A9-2)
3. [C) Cloud Run + Cloud Logging (Priorité 3)](#c-cloud-run--cloud-logging-priorit%C3%A9-3)
4. [D) Secret Manager (Priorité 4 — Gouverné)](#d-secret-manager-priorit%C3%A9-4--gouvern%C3%A9)
5. [E) Web Access (Observabilité)](#e-web-access-observabilit%C3%A9)
6. [F) Terminal / Command Runner (Option)](#f-terminal--command-runner-option)
7. [Journalisation & Gouvernance](#journalisation--gouvernance)
8. [Redaction & Sécurité](#redaction--s%C3%A9curit%C3%A9)

---

## A) Google Drive (Priorité 1)

### Objectif
Vérifier présence + dates des fichiers de gouvernance et des artifacts **sans UI Drive**.

### Endpoints

#### 1. `GET /drive/tree`
**Description** : Liste récursive d'un folder avec contrôle de profondeur  
**Gouvernance** : READ_ONLY  
**Params** :
- `folder_id` (required, string) : ID du folder Drive
- `max_depth` (optional, int, default=2, max=5) : Profondeur récursive max
- `limit` (optional, int, default=100, max=500) : Nombre max d'items par niveau
- `include_trashed` (optional, bool, default=false) : Inclure fichiers dans corbeille

**Response** :
```json
{
  "ok": true,
  "run_id": "drive_tree_1708617600_abc123",
  "folder_id": "1ABC...",
  "folder_name": "ARCHIVES",
  "total_items": 42,
  "tree": [
    {
      "id": "file123",
      "name": "IAPF_HUB_EXPORT__20260220.zip",
      "mimeType": "application/zip",
      "size": 198432,
      "modifiedTime": "2026-02-20T11:00:00Z",
      "parents": ["1ABC..."],
      "depth": 1,
      "path": "/ARCHIVES/IAPF_HUB_EXPORT__20260220.zip"
    }
  ],
  "truncated": false,
  "pagination": {
    "next_page_token": null
  }
}
```

**Limites** :
- Max 500 items par niveau
- Max profondeur 5
- Timeout 30s

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Drive — Tree listing`
- Details : `folder_id=..., depth=..., items=...`
- Tags : `MCP;DRIVE;READ`

---

#### 2. `GET /drive/file/{file_id}/metadata`
**Description** : Métadonnées complètes d'un fichier  
**Gouvernance** : READ_ONLY  
**Params** :
- `file_id` (required, string) : ID du fichier Drive

**Response** :
```json
{
  "ok": true,
  "run_id": "drive_meta_1708617601_xyz789",
  "file": {
    "id": "file123",
    "name": "SETTINGS.xlsx",
    "mimeType": "application/vnd.google-apps.spreadsheet",
    "size": 45678,
    "createdTime": "2026-01-15T10:00:00Z",
    "modifiedTime": "2026-02-20T09:30:00Z",
    "owners": [{"emailAddress": "[REDACTED]"}],
    "parents": ["folder456"],
    "capabilities": {
      "canEdit": true,
      "canDownload": true,
      "canDelete": true
    },
    "md5Checksum": "abc123def456...",
    "version": 42
  }
}
```

**Redaction** : `owners.emailAddress`, `lastModifyingUser.emailAddress`, `sharingUser.emailAddress`

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Drive — File metadata`
- Details : `file_id=..., name=..., size=...`
- Tags : `MCP;DRIVE;READ`

---

#### 3. `GET /drive/search`
**Description** : Recherche par nom/regex (borné)  
**Gouvernance** : READ_ONLY  
**Params** :
- `query` (required, string) : Nom ou regex (max 100 chars)
- `folder_id` (optional, string) : Limiter à un folder
- `mime_type` (optional, string) : Filtrer par type (ex: `application/pdf`)
- `modified_after` (optional, ISO8601) : Modifié après date
- `limit` (optional, int, default=50, max=200) : Nombre max résultats
- `page_token` (optional, string) : Token pagination

**Response** :
```json
{
  "ok": true,
  "run_id": "drive_search_1708617602_qwe456",
  "query": "IAPF_HUB_EXPORT",
  "total_results": 15,
  "files": [
    {
      "id": "file789",
      "name": "IAPF_HUB_EXPORT__20260220.zip",
      "mimeType": "application/zip",
      "size": 198432,
      "modifiedTime": "2026-02-20T11:00:00Z",
      "parents": ["folder_archives"]
    }
  ],
  "next_page_token": "token123..."
}
```

**Limites** :
- Max 200 résultats par page
- Query max 100 chars
- Timeout 15s

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Drive — Search`
- Details : `query=..., results=..., folder_id=...`
- Tags : `MCP;DRIVE;READ;SEARCH`

---

#### 4. `GET /drive/file/{file_id}/content` (Option)
**Description** : Lire contenu fichier (MD/JSON/TXT uniquement, borné taille)  
**Gouvernance** : READ_ONLY  
**Params** :
- `file_id` (required, string) : ID du fichier
- `max_size` (optional, int, default=1MB, max=5MB) : Taille max lecture

**Response** :
```json
{
  "ok": true,
  "run_id": "drive_content_1708617603_aaa111",
  "file_id": "file999",
  "name": "README.md",
  "mimeType": "text/markdown",
  "size": 4567,
  "content": "# IAPF Memory\n\n...",
  "truncated": false
}
```

**Limites** :
- Seulement `text/plain`, `text/markdown`, `application/json`
- Max 5MB
- Si trop grand : truncated=true + premiers 1MB

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Drive — Read content`
- Details : `file_id=..., name=..., size=...`
- Tags : `MCP;DRIVE;READ;CONTENT`

---

## B) Apps Script (Priorité 2)

### Objectif
Éviter "mauvaise version déployée", diagnostiquer **sans UI**.

### Endpoints

#### 1. `GET /apps-script/project/{script_id}/deployments`
**Description** : Liste deployments (id, version, url, lastUpdate)  
**Gouvernance** : READ_ONLY  
**Params** :
- `script_id` (required, string) : ID projet Apps Script
- `limit` (optional, int, default=20, max=50) : Nombre max deployments

**Response** :
```json
{
  "ok": true,
  "run_id": "apps_deploy_1708617604_bbb222",
  "script_id": "AKfycbx...",
  "deployments": [
    {
      "deployment_id": "AKfycby...",
      "version_number": 42,
      "description": "HUB IAPF v3 - Patch BLK-001/002/003",
      "web_app_url": "https://script.google.com/...",
      "created_time": "2026-02-20T10:30:00Z",
      "updated_time": "2026-02-20T11:00:00Z",
      "entry_points": [
        {"entry_point_type": "WEB_APP", "web_app_url": "https://..."}
      ]
    }
  ],
  "total_deployments": 5
}
```

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Apps Script — List deployments`
- Details : `script_id=..., count=...`
- Tags : `MCP;APPS_SCRIPT;READ;DEPLOYMENTS`

---

#### 2. `GET /apps-script/project/{script_id}/structure`
**Description** : Structure projet (liste fichiers + lastUpdate)  
**Gouvernance** : READ_ONLY  
**Params** :
- `script_id` (required, string) : ID projet Apps Script

**Response** :
```json
{
  "ok": true,
  "run_id": "apps_struct_1708617605_ccc333",
  "script_id": "AKfycbx...",
  "project_name": "IAPF HUB Memory",
  "files": [
    {
      "name": "G00_BOOTSTRAP",
      "type": "SERVER_JS",
      "size": 2048,
      "lastModified": "2026-02-20T10:00:00Z",
      "function_count": 3
    },
    {
      "name": "appsscript",
      "type": "JSON",
      "size": 875
    }
  ],
  "total_files": 18,
  "total_functions": 127
}
```

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Apps Script — Project structure`
- Details : `script_id=..., files=..., functions=...`
- Tags : `MCP;APPS_SCRIPT;READ;STRUCTURE`

---

#### 3. `GET /apps-script/project/{script_id}/logs`
**Description** : Logs/executions Apps Script  
**Gouvernance** : READ_ONLY  
**Params** :
- `script_id` (required, string) : ID projet
- `start_time` (optional, ISO8601) : Début time-range
- `end_time` (optional, ISO8601) : Fin time-range
- `limit` (optional, int, default=50, max=200) : Nombre max logs

**Response** :
```json
{
  "ok": true,
  "run_id": "apps_logs_1708617606_ddd444",
  "script_id": "AKfycbx...",
  "logs": [
    {
      "execution_id": "exec123",
      "function_name": "MCP_IMPL_initializeDay",
      "status": "SUCCESS",
      "start_time": "2026-02-20T10:30:00Z",
      "end_time": "2026-02-20T10:30:02Z",
      "duration_ms": 2150,
      "log_entries": [
        {"severity": "INFO", "message": "MEMORY_APPEND_OK"}
      ]
    }
  ],
  "total_logs": 15
}
```

**Redaction** : Messages contenant patterns secrets/tokens

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Apps Script — Read logs`
- Details : `script_id=..., count=..., time_range=...`
- Tags : `MCP;APPS_SCRIPT;READ;LOGS`

---

#### 4. `GET /apps-script/project/{script_id}/version-info` (Option)
**Description** : Info dernière version  
**Gouvernance** : READ_ONLY  
**Params** :
- `script_id` (required, string) : ID projet

**Response** :
```json
{
  "ok": true,
  "run_id": "apps_version_1708617607_eee555",
  "script_id": "AKfycbx...",
  "latest_version": 42,
  "version_description": "Patch BLK-001/002/003",
  "created_time": "2026-02-20T11:00:00Z",
  "head_deployment_id": "AKfycby..."
}
```

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Apps Script — Version info`
- Details : `script_id=..., version=...`
- Tags : `MCP;APPS_SCRIPT;READ;VERSION`

---

## C) Cloud Run + Cloud Logging (Priorité 3)

### Objectif
Diagnostiquer prod/staging **sans console**.

### Endpoints

#### 1. `GET /cloud-run/service/{service_name}/status`
**Description** : Status service (revision, image digest, last deploy)  
**Gouvernance** : READ_ONLY  
**Params** :
- `service_name` (required, string) : Nom du service (ex: `mcp-memory-proxy`)
- `region` (optional, string, default=from_settings) : Région GCP

**Response** :
```json
{
  "ok": true,
  "run_id": "cr_status_1708617608_fff666",
  "service_name": "mcp-memory-proxy",
  "region": "us-central1",
  "status": {
    "ready_condition": "True",
    "latest_created_revision": "mcp-memory-proxy-00025-zmb",
    "latest_ready_revision": "mcp-memory-proxy-00025-zmb",
    "url": "https://mcp-memory-proxy-522732657254.us-central1.run.app",
    "traffic": [
      {"revision": "mcp-memory-proxy-00025-zmb", "percent": 100}
    ],
    "last_modified": "2026-02-20T04:28:00Z",
    "image_digest": "sha256:abc123def456...",
    "environment": "PRODUCTION"
  }
}
```

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Cloud Run — Service status`
- Details : `service=..., revision=..., region=...`
- Tags : `MCP;CLOUD_RUN;READ;STATUS`

---

#### 2. `POST /cloud-logging/query`
**Description** : Query Cloud Logging avec pagination/time-range  
**Gouvernance** : READ_ONLY  
**Params (body JSON)** :
```json
{
  "resource_type": "cloud_run_revision",
  "resource_labels": {
    "service_name": "mcp-memory-proxy",
    "revision_name": "mcp-memory-proxy-00025-zmb"
  },
  "filter": "severity>=INFO",
  "start_time": "2026-02-20T10:00:00Z",
  "end_time": "2026-02-20T11:00:00Z",
  "limit": 100,
  "page_token": null
}
```

**Response** :
```json
{
  "ok": true,
  "run_id": "logs_query_1708617609_ggg777",
  "entries": [
    {
      "timestamp": "2026-02-20T10:30:15.123Z",
      "severity": "INFO",
      "text_payload": "GET /infra/whoami 200 - 15ms",
      "labels": {
        "correlation_id": "req_1708617615_abc"
      }
    }
  ],
  "next_page_token": "token789...",
  "total_entries": 245
}
```

**Redaction** : `text_payload` contenant patterns secrets/API keys

**Limites** :
- Max 1000 entries par requête
- Time-range max 7 jours
- Timeout 30s

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Cloud Logging — Query`
- Details : `resource=..., filter=..., entries=...`
- Tags : `MCP;CLOUD_LOGGING;READ;QUERY`

---

#### 3. `GET /cloud-run/job/{job_name}/status` (Option)
**Description** : Status Cloud Run Job + executions  
**Gouvernance** : READ_ONLY  
**Params** :
- `job_name` (required, string) : Nom du job
- `region` (optional, string) : Région GCP
- `limit` (optional, int, default=10, max=50) : Nombre max executions récentes

**Response** :
```json
{
  "ok": true,
  "run_id": "cr_job_1708617610_hhh888",
  "job_name": "mcp-deploy-iapf",
  "region": "us-central1",
  "latest_execution": {
    "execution_id": "exec_20260220_103000",
    "status": "SUCCEEDED",
    "start_time": "2026-02-20T10:30:00Z",
    "completion_time": "2026-02-20T10:32:15Z",
    "duration_seconds": 135,
    "log_uri": "https://console.cloud.google.com/..."
  },
  "recent_executions": []
}
```

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Cloud Run Job — Status`
- Details : `job=..., status=..., region=...`
- Tags : `MCP;CLOUD_RUN;READ;JOB`

---

## D) Secret Manager (Priorité 4 — Gouverné)

### Objectif
Permettre à Élia de "mettre les clés au bon endroit" **sans exposition**.

### Endpoints

#### 1. `GET /secrets/list`
**Description** : Lister secrets + métadonnées + labels + versions actives  
**Gouvernance** : READ_ONLY  
**Params** :
- `project_id` (optional, string, default=from_settings) : Projet GCP
- `filter` (optional, string) : Filtre labels (ex: `labels.env=production`)
- `limit` (optional, int, default=50, max=200) : Nombre max secrets

**Response** :
```json
{
  "ok": true,
  "run_id": "secrets_list_1708617611_iii999",
  "project_id": "box-magic-ocr-intelligent",
  "secrets": [
    {
      "name": "projects/123/secrets/mcp_api_key",
      "secret_id": "mcp_api_key",
      "labels": {"env": "production", "service": "mcp-proxy"},
      "replication": "AUTOMATIC",
      "created_time": "2026-01-15T10:00:00Z",
      "latest_version": {
        "version_id": "5",
        "state": "ENABLED",
        "created_time": "2026-02-18T14:00:00Z"
      },
      "total_versions": 5
    }
  ],
  "total_secrets": 12
}
```

**Redaction** : **Jamais** retourner la valeur du secret (value)

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Secret Manager — List secrets`
- Details : `project=..., count=..., filter=...`
- Tags : `MCP;SECRETS;READ;LIST`

---

#### 2. `GET /secrets/{secret_id}/reference`
**Description** : Lire référence uniquement (jamais la valeur)  
**Gouvernance** : READ_ONLY  
**Params** :
- `secret_id` (required, string) : ID du secret
- `project_id` (optional, string) : Projet GCP
- `version` (optional, string, default=latest) : Version du secret

**Response** :
```json
{
  "ok": true,
  "run_id": "secrets_ref_1708617612_jjj000",
  "secret_id": "mcp_api_key",
  "secret_name": "projects/123/secrets/mcp_api_key",
  "version": "5",
  "version_state": "ENABLED",
  "reference": "projects/123/secrets/mcp_api_key/versions/5",
  "labels": {"env": "production"},
  "created_time": "2026-02-18T14:00:00Z",
  "value": "[REDACTED]"
}
```

**⚠️ IMPORTANT** : Le champ `value` est **toujours** `[REDACTED]`. Seule la référence est retournée.

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Secret Manager — Get reference`
- Details : `secret_id=..., version=..., reference=...`
- Tags : `MCP;SECRETS;READ;REFERENCE`

---

#### 3. `POST /secrets/create` (Gouverné WRITE)
**Description** : Créer secret (mode DRY_RUN disponible)  
**Gouvernance** : WRITE_DRY_RUN / WRITE_APPLY  
**Params (body JSON)** :
```json
{
  "secret_id": "new_api_key",
  "value": "sk-abc123...",
  "labels": {"env": "staging", "service": "test"},
  "replication": "automatic",
  "project_id": "box-magic-ocr-intelligent",
  "dry_run": true
}
```

**Response (DRY_RUN)** :
```json
{
  "ok": true,
  "run_id": "secrets_create_1708617613_kkk111",
  "dry_run": true,
  "action": "CREATE_SECRET",
  "secret_id": "new_api_key",
  "secret_name": "projects/123/secrets/new_api_key",
  "reference": "projects/123/secrets/new_api_key/versions/1",
  "labels": {"env": "staging"},
  "message": "DRY_RUN: Secret would be created (not applied)",
  "to_apply": {
    "set_dry_run_false": true,
    "confirm_action": "CREATE_SECRET"
  }
}
```

**Response (APPLY)** :
```json
{
  "ok": true,
  "run_id": "secrets_create_1708617614_lll222",
  "dry_run": false,
  "action": "CREATE_SECRET",
  "secret_id": "new_api_key",
  "secret_name": "projects/123/secrets/new_api_key",
  "reference": "projects/123/secrets/new_api_key/versions/1",
  "created_time": "2026-02-20T11:00:00Z",
  "message": "Secret created successfully"
}
```

**Journalisation** :
- Type : `DECISION` (si APPLY), `CONSTAT` (si DRY_RUN)
- Title : `MCP Secret Manager — Create secret [DRY_RUN|APPLIED]`
- Details : `secret_id=..., reference=..., dry_run=...`
- Tags : `MCP;SECRETS;WRITE;CREATE`

**Validation gouvernée** :
- Un seul GO requis (pas de multi-confirm)
- Log MEMORY_LOG obligatoire
- Redaction de la valeur dans tous les logs

---

#### 4. `POST /secrets/{secret_id}/rotate` (Gouverné WRITE)
**Description** : Rotater secret (nouvelle version)  
**Gouvernance** : WRITE_DRY_RUN / WRITE_APPLY  
**Params (body JSON)** :
```json
{
  "secret_id": "mcp_api_key",
  "new_value": "sk-new123...",
  "disable_previous_version": false,
  "dry_run": true
}
```

**Response (similaire à create)** :
```json
{
  "ok": true,
  "run_id": "secrets_rotate_1708617615_mmm333",
  "dry_run": true,
  "action": "ROTATE_SECRET",
  "secret_id": "mcp_api_key",
  "new_version": "6",
  "reference": "projects/123/secrets/mcp_api_key/versions/6",
  "previous_version": "5",
  "message": "DRY_RUN: Secret version 6 would be created, version 5 kept enabled"
}
```

**Journalisation** :
- Type : `DECISION` (si APPLY), `CONSTAT` (si DRY_RUN)
- Title : `MCP Secret Manager — Rotate secret [DRY_RUN|APPLIED]`
- Details : `secret_id=..., new_version=..., dry_run=...`
- Tags : `MCP;SECRETS;WRITE;ROTATE`

---

## E) Web Access (Observabilité)

### Objectif
Quand une doc Google change, Élia sait retrouver l'info au lieu de bloquer.

### Endpoints

#### 1. `POST /web/search`
**Description** : Web search contrôlé (allowlist domaines + quotas + logs)  
**Gouvernance** : READ_ONLY  
**Params (body JSON)** :
```json
{
  "query": "Google Apps Script API documentation",
  "max_results": 10,
  "allowed_domains": [
    "developers.google.com",
    "cloud.google.com",
    "googleapis.dev"
  ]
}
```

**Response** :
```json
{
  "ok": true,
  "run_id": "web_search_1708617616_nnn444",
  "query": "Google Apps Script API documentation",
  "results": [
    {
      "title": "Apps Script API | Google Developers",
      "url": "https://developers.google.com/apps-script/api",
      "snippet": "The Apps Script API lets you programmatically create...",
      "domain": "developers.google.com"
    }
  ],
  "total_results": 5,
  "quota_remaining": 95
}
```

**Limites** :
- Max 10 résultats par requête
- Quota 100 requêtes/jour par défaut
- Timeout 10s
- Allowlist domaines stricte (configurable SETTINGS)

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Web — Search`
- Details : `query=..., results=..., quota_remaining=...`
- Tags : `MCP;WEB;READ;SEARCH`

---

#### 2. `POST /web/fetch`
**Description** : Fetch URL contrôlé (allowlist domaines + logs)  
**Gouvernance** : READ_ONLY  
**Params (body JSON)** :
```json
{
  "url": "https://developers.google.com/apps-script/api",
  "method": "GET",
  "headers": {},
  "max_size": 1048576
}
```

**Response** :
```json
{
  "ok": true,
  "run_id": "web_fetch_1708617617_ooo555",
  "url": "https://developers.google.com/apps-script/api",
  "status_code": 200,
  "content_type": "text/html",
  "content_length": 45678,
  "content": "<!DOCTYPE html>\n<html>...",
  "truncated": false,
  "quota_remaining": 94
}
```

**Limites** :
- Seulement GET/HEAD
- Max 5MB par fetch
- Allowlist domaines stricte
- Timeout 15s
- Quota 100 requêtes/jour

**Journalisation** :
- Type : `CONSTAT`
- Title : `MCP Web — Fetch`
- Details : `url=..., status=..., size=...`
- Tags : `MCP;WEB;READ;FETCH`

---

## F) Terminal / Command Runner (Option)

### Objectif
Exécuter des checks techniques rapides **sans friction**.

### Endpoints

#### 1. `POST /terminal/run` (Très cadré)
**Description** : Command runner avec allowlist commandes stricte  
**Gouvernance** : READ_ONLY (diagnostics) / WRITE_DRY_RUN / WRITE_APPLY  
**Params (body JSON)** :
```json
{
  "command": "gcloud run services describe mcp-memory-proxy --region=us-central1 --format=json",
  "mode": "READ_ONLY",
  "timeout_seconds": 30,
  "dry_run": false
}
```

**Allowlist commandes READ_ONLY** :
- `gcloud run services describe`
- `gcloud run services list`
- `gcloud logging read`
- `gcloud secrets list`
- `gcloud secrets versions list`
- `gsutil ls`
- `gsutil du`

**Allowlist commandes WRITE (après GO)** :
- `gcloud run services update` (DRY_RUN disponible via `--dry-run`)
- `gcloud secrets create`
- `gcloud secrets versions add`

**Response** :
```json
{
  "ok": true,
  "run_id": "terminal_run_1708617618_ppp666",
  "command": "gcloud run services describe...",
  "mode": "READ_ONLY",
  "exit_code": 0,
  "stdout": "{\n  \"apiVersion\": \"serving.knative.dev/v1\",\n  ...\n}",
  "stderr": "",
  "duration_ms": 1250,
  "dry_run": false
}
```

**Limites** :
- Seulement commandes allowlistées
- Timeout max 60s
- Logs stdout/stderr tronqués à 100KB
- Sandbox environnement

**Journalisation** :
- Type : `DECISION` (si WRITE_APPLY), `CONSTAT` (si READ_ONLY ou DRY_RUN)
- Title : `MCP Terminal — Run command [READ_ONLY|DRY_RUN|APPLIED]`
- Details : `command=..., exit_code=..., mode=...`
- Tags : `MCP;TERMINAL;RUN`

---

## Journalisation & Gouvernance

### Format MEMORY_LOG

Toutes les actions MCP Phase 2 loggent dans **MEMORY_LOG** avec :

```javascript
{
  type: "CONSTAT" | "DECISION",  // DECISION si WRITE_APPLY
  title: "MCP {Domain} — {Action} [{Mode}]",
  details: "run_id=..., params=..., result=...",
  source: "MCP_ACTIONS_EXTENDED",
  tags: "MCP;{DOMAIN};{ACTION_TYPE};{MODE}"
}
```

**Exemples** :
- `MCP Drive — Tree listing [READ_ONLY]`
- `MCP Secret Manager — Create secret [DRY_RUN]`
- `MCP Secret Manager — Rotate secret [APPLIED]`

### `run_id` unique

Format : `{domain}_{action}_{timestamp}_{random6}`

Exemples :
- `drive_tree_1708617600_abc123`
- `secrets_create_1708617613_kkk111`

**Utilisation** :
- Corrélation logs backend ↔ MEMORY_LOG
- Recherche rapide dans LOGS
- Traçabilité complète

### Modes gouvernés

| Mode | Description | GO requis | Log type | DRY_RUN |
|------|-------------|-----------|----------|---------|
| `READ_ONLY` | Lecture seule | Non | CONSTAT | N/A |
| `WRITE_DRY_RUN` | Simulation WRITE | Non | CONSTAT | Oui |
| `WRITE_APPLY` | Action réelle | **Oui** | DECISION | Non |

### Validation GO (WRITE_APPLY)

**Un seul GO** via popup Google Sheets :
```
MCP — {Action} (WRITE_APPLY)

Domaine : {Domain}
Action  : {Action}
Params  : {params_summary}

⚠️ Cette action modifiera l'environnement {PROD|STAGING}

Mode DRY_RUN : disponible pour tester avant application

Continuer avec WRITE_APPLY ?
[Oui] [Non]
```

**Pas de multi-confirm** : un seul popup, une seule décision.

---

## Redaction & Sécurité

### Patterns redactés automatiquement

**Backend proxy** : Redaction systématique avant réponse

| Pattern | Remplacement | Domaines concernés |
|---------|--------------|---------------------|
| `sk-[A-Za-z0-9]+` | `[REDACTED_API_KEY]` | Tous |
| Email addresses | `[REDACTED_EMAIL]` | Drive, Apps Script, Logs |
| `AIza[A-Za-z0-9_-]{35}` | `[REDACTED_GCP_KEY]` | Tous |
| `projects/[0-9]+/secrets/*/versions/*/value` | `[REDACTED_SECRET_VALUE]` | Secret Manager |
| Token JWT `eyJ...` | `[REDACTED_JWT]` | Tous |
| `ghp_[A-Za-z0-9]+` | `[REDACTED_GITHUB_TOKEN]` | Web, Terminal |

### Règles de sécurité

1. **Jamais de secret en clair** :
   - Secret Manager : seulement références retournées
   - MEMORY_LOG : valeurs redactées
   - LOGS : redaction automatique

2. **Allowlist stricte** :
   - Web : domaines configurables via SETTINGS
   - Terminal : commandes allowlistées (pas d'exec arbitraire)

3. **Quotas** :
   - Web search/fetch : 100 requêtes/jour par défaut
   - Terminal : 50 runs/jour READ_ONLY, 10 runs/jour WRITE
   - Configurable via SETTINGS

4. **Audit trail complet** :
   - MEMORY_LOG : toutes actions
   - Backend LOGS : toutes requêtes avec `run_id`
   - Corrélation facile run_id ↔ correlation_id

---

## Endpoints récapitulatifs

### Priorité 1 — Google Drive (4 endpoints)
- `GET /drive/tree` — Liste récursive folder
- `GET /drive/file/{file_id}/metadata` — Métadonnées fichier
- `GET /drive/search` — Recherche fichiers
- `GET /drive/file/{file_id}/content` — Lire contenu (opt)

### Priorité 2 — Apps Script (4 endpoints)
- `GET /apps-script/project/{script_id}/deployments` — Liste deployments
- `GET /apps-script/project/{script_id}/structure` — Structure projet
- `GET /apps-script/project/{script_id}/logs` — Logs/executions
- `GET /apps-script/project/{script_id}/version-info` — Info version (opt)

### Priorité 3 — Cloud Run + Logging (3 endpoints)
- `GET /cloud-run/service/{service_name}/status` — Status service
- `POST /cloud-logging/query` — Query logs
- `GET /cloud-run/job/{job_name}/status` — Status job (opt)

### Priorité 4 — Secret Manager (4 endpoints)
- `GET /secrets/list` — Liste secrets
- `GET /secrets/{secret_id}/reference` — Référence secret
- `POST /secrets/create` — Créer secret (gouverné)
- `POST /secrets/{secret_id}/rotate` — Rotater secret (gouverné)

### Observabilité — Web (2 endpoints)
- `POST /web/search` — Web search contrôlé
- `POST /web/fetch` — Fetch URL contrôlé

### Option — Terminal (1 endpoint)
- `POST /terminal/run` — Command runner cadré

**Total** : **18 endpoints** (15 READ_ONLY + 3 WRITE gouvernés)

---

## Configuration SETTINGS

Nouvelles clés à ajouter dans onglet **SETTINGS** :

| Clé | Valeur | Description |
|-----|--------|-------------|
| `mcp_gcp_project_id` | `box-magic-ocr-intelligent` | Projet GCP par défaut |
| `mcp_gcp_region` | `us-central1` | Région GCP par défaut |
| `mcp_cloud_run_service` | `mcp-memory-proxy` | Service Cloud Run principal |
| `mcp_web_allowed_domains` | `developers.google.com,cloud.google.com,googleapis.dev` | Domaines autorisés web search/fetch |
| `mcp_web_quota_daily` | `100` | Quota web search/fetch par jour |
| `mcp_terminal_quota_daily_read` | `50` | Quota terminal READ_ONLY par jour |
| `mcp_terminal_quota_daily_write` | `10` | Quota terminal WRITE par jour |
| `mcp_environment` | `PRODUCTION` | Environnement actuel (PRODUCTION/STAGING) |

---

## Distinction PROD / STAGING

### Variables d'environnement backend

```python
# memory-proxy/app/config.py
MCP_ENVIRONMENT = os.getenv("MCP_ENVIRONMENT", "STAGING")  # STAGING par défaut
MCP_GCP_PROJECT_ID = os.getenv("MCP_GCP_PROJECT_ID", "box-magic-ocr-intelligent")
MCP_GCP_REGION = os.getenv("MCP_GCP_REGION", "us-central1")
```

### Basculer PROD ↔ STAGING

**Backend (Cloud Run env vars)** :
```bash
gcloud run services update mcp-memory-proxy \
  --region=us-central1 \
  --set-env-vars="MCP_ENVIRONMENT=PRODUCTION"
```

**Hub (SETTINGS)** :
```
mcp_environment = PRODUCTION
```

### Règles gouvernance par environnement

| Mode | STAGING | PRODUCTION |
|------|---------|------------|
| READ_ONLY | ✅ Autorisé | ✅ Autorisé |
| WRITE_DRY_RUN | ✅ Autorisé | ✅ Autorisé |
| WRITE_APPLY | ✅ Autorisé (1 GO) | ⚠️ GO + confirmation email |

**PRODUCTION** : Option d'ajouter confirmation email avant WRITE_APPLY (phase future).

---

## Prochaines étapes

1. **Implémenter backend proxy** : 18 endpoints + redaction + journalisation
2. **Créer G16_MCP_ACTIONS_EXTENDED.gs** : Menu unifié "Actions MCP"
3. **Mettre à jour G14_MCP_HTTP_CLIENT.gs** : Ajouter wrappers pour nouveaux endpoints
4. **Tests validation** : 20 appels consécutifs par endpoint (checklist OK/KO)
5. **Documentation** : Guide déploiement + examples d'usage

---

**Date création** : 2026-02-20 19:00 UTC  
**Auteur** : Claude Code (Genspark AI Developer)  
**Version** : Phase 2 — Extension contrôlée des accès MCP  
**Status** : Spécification complète (prêt pour implémentation)
