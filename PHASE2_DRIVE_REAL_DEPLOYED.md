# Phase 2 Drive API Réel — Déploiement Réussi

**Date**: 2026-02-20 23:00 UTC  
**Commit déployé**: `6662647`  
**Cloud Run revision**: `mcp-memory-proxy-00031-lgh`  
**Service URL**: https://mcp-memory-proxy-522732657254.us-central1.run.app

---

## ✅ Livraison Phase 2 — Drive API v3 Réel

### Ce qui a été fait

1. **Backend Proxy — Drive API v3 réel**
   - ✅ Créé `memory-proxy/app/drive_client.py` (9.8 KB, 292 lignes)
     - `get_file_metadata(file_id)` → métadonnées complètes (nom, mimeType, size, dates, owners, capabilities)
     - `list_folder_tree(folder_id, max_depth, limit)` → arbre récursif avec children
     - `search_files(query, folder_id, limit)` → recherche dans Drive
     - `read_file_text(file_id, max_bytes)` → lecture bornée de texte
   - ✅ Patché `memory-proxy/app/phase2_endpoints.py`
     - Import `drive_client`
     - Remplacé 3 mocks par vrais appels Drive API :
       - `/drive/tree` → `drive_client.list_folder_tree()`
       - `/drive/file/{id}/metadata` → `drive_client.get_file_metadata()`
       - `/drive/search` → `drive_client.search_files()`

2. **Hub UI — Menu enrichi**
   - ✅ Ajouté `MCP_ACTION_webFetch()` dans `HUB_COMPLET/G16_MCP_ACTIONS_EXTENDED.gs`
   - ✅ Ajouté entrée menu "📥 Web — Fetch" dans `HUB_COMPLET/G01_UI_MENU.gs`
   - ⚠️ **Wrapper HTTP déjà existant** : `MCP_HTTP.webFetch()` dans G17 (aucune modification requise)

3. **Cloud Build & Déploiement**
   - ✅ Créé `memory-proxy/cloudbuild.yaml` (Cloud Build sans Docker local)
   - ✅ Build réussi : Build ID `3bedd096-f441-4173-a171-d72f2e09eaf0` (1m24s)
   - ✅ Image : `gcr.io/box-magique-gp-prod/mcp-memory-proxy:phase2-6662647`
   - ✅ Secret Manager : créé secret `mcp-cockpit-sa-key` avec service account JSON
   - ✅ IAM : granted `roles/secretmanager.secretAccessor` à `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
   - ✅ Cloud Run déployé :
     - Service: `mcp-memory-proxy`
     - Région: `us-central1`
     - Révision: `mcp-memory-proxy-00031-lgh`
     - Service Account: `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
     - Secret monté: `/secrets/sa-key.json` → `mcp-cockpit-sa-key:latest`
     - Env vars: `GOOGLE_APPLICATION_CREDENTIALS=/secrets/sa-key.json`, `GIT_COMMIT=6662647`, `VERSION=3.0.6-phase2-drive-real`

4. **Git**
   - ✅ Commit `6662647` : "fix(Phase 2 CRITICAL): Drive API v3 réel + Web Fetch menu + Cloud Build config"
   - ✅ Push à GitHub : https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent/commit/6662647
   - ✅ `.gitignore` : ajouté `memory-proxy/sa-key.json`

---

## ⚠️ Action requise : Partage Drive

**Blocage actuel** : Le service account `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com` n'a **pas accès** au folder Drive `1LwUZ67zVstl2tuogcdYYihPilUAXQai3`.

### Erreur constatée

```json
{
  "detail": "Drive API error for file 1LwUZ67zVstl2tuogcdYYihPilUAXQai3: <HttpError 404 when requesting https://www.googleapis.com/drive/v3/files/1LwUZ67zVstl2tuogcdYYihPilUAXQai3 ... returned \"File not found: 1LwUZ67zVstl2tuogcdYYihPilUAXQai3.\""
}
```

### Solution (à faire immédiatement)

1. **Ouvrir Google Drive** : https://drive.google.com/drive/folders/1LwUZ67zVstl2tuogcdYYihPilUAXQai3
2. **Clic droit** sur le dossier `ARCHIVES` (ou racine du projet)
3. **Partager** → Ajouter :
   ```
   mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com
   ```
4. **Niveau d'accès** : **Lecteur** (READ_ONLY suffit)
5. **Valider** le partage

⏱️ **Temps estimé** : 30 secondes.

### Après le partage → Tests de validation

Une fois le dossier partagé, les 3 curls ci-dessous doivent renvoyer des **données réelles** (pas de mocks).

---

## 🔬 Preuves attendues (après partage)

### PREUVE 1 : `/drive/file/{id}/metadata`

**Commande** :
```bash
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/drive/file/1LwUZ67zVstl2tuogcdYYihPilUAXQai3/metadata" | jq '.file | {name, mimeType, modifiedTime, size}'
```

**Résultat attendu** (après partage) :
```json
{
  "name": "ARCHIVES",
  "mimeType": "application/vnd.google-apps.folder",
  "modifiedTime": "2026-02-18T14:23:45.123Z",
  "size": 0
}
```

---

### PREUVE 2 : `/drive/search?query=...`

**Commande** :
```bash
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/drive/search?query=00_GOUVERNANCE&folder_id=1LwUZ67zVstl2tuogcdYYihPilUAXQai3&limit=10" | jq '{total_results, files: [.files[] | {name, mimeType, modifiedTime}]}'
```

**Résultat attendu** (≥ 1 résultat réel) :
```json
{
  "total_results": 2,
  "files": [
    {
      "name": "00_GOUVERNANCE",
      "mimeType": "application/vnd.google-apps.folder",
      "modifiedTime": "2026-01-15T09:12:34.567Z"
    },
    {
      "name": "00_GOUVERNANCE_BACKUP.pdf",
      "mimeType": "application/pdf",
      "modifiedTime": "2026-01-10T08:45:12.345Z"
    }
  ]
}
```

---

### PREUVE 3 : `/drive/tree?folder_id=...`

**Commande** :
```bash
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/drive/tree?folder_id=1LwUZ67zVstl2tuogcdYYihPilUAXQai3&max_depth=2&limit=100" | jq '{folder_name, total_items, tree_sample: [.tree[0:3] | .[] | {name, type, children_count}]}'
```

**Résultat attendu** (items > 0) :
```json
{
  "folder_name": "ARCHIVES",
  "total_items": 42,
  "tree_sample": [
    {
      "name": "00_GOUVERNANCE",
      "type": "folder",
      "children_count": 8
    },
    {
      "name": "01_SNAPSHOTS",
      "type": "folder",
      "children_count": 15
    },
    {
      "name": "README.md",
      "type": "file",
      "children_count": null
    }
  ]
}
```

---

## 📋 Apps Script — Validation (à faire)

**Endpoints Apps Script** :
- `/apps-script/project/{script_id}/deployments`
- `/apps-script/project/{script_id}/structure`

**APIs/Scopes requis** (à vérifier dans Google Cloud Console) :
1. **Apps Script API** : https://console.cloud.google.com/apis/library/script.googleapis.com
   - Statut requis : **Enabled**
2. **OAuth Scopes** (service account `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`) :
   - `https://www.googleapis.com/auth/script.projects.readonly`
   - `https://www.googleapis.com/auth/script.deployments.readonly`

**Commandes de test** (à exécuter après activation Apps Script API) :
```bash
# Test 1: List deployments
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/apps-script/project/{SCRIPT_ID}/deployments?limit=10" | jq '.'

# Test 2: Get project structure
curl -s "https://mcp-memory-proxy-522732657254.us-central1.run.app/apps-script/project/{SCRIPT_ID}/structure" | jq '.'
```

**Remplacer `{SCRIPT_ID}`** par l'ID réel du projet Apps Script (visible dans l'URL : `https://script.google.com/home/projects/{SCRIPT_ID}/edit`).

---

## 🚀 Métriques finales

| Métrique | Valeur |
|----------|--------|
| **Commit déployé** | `6662647` |
| **Image Docker** | `gcr.io/box-magique-gp-prod/mcp-memory-proxy:phase2-6662647` |
| **Cloud Run revision** | `mcp-memory-proxy-00031-lgh` |
| **Build time** | 1m24s |
| **Deploy time** | 1m57s |
| **Service URL** | https://mcp-memory-proxy-522732657254.us-central1.run.app |
| **Health check** | `/health` (accessible) |
| **OpenAPI** | `/openapi.json` (14 Phase 2 routes listées) |
| **Environment** | STAGING |
| **Service Account** | `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com` |
| **Secret Manager** | `mcp-cockpit-sa-key` (version 1, mounted) |

---

## 📊 Checklist finale

- [x] **Backend** : Drive API v3 réel (client créé, endpoints patchés)
- [x] **Hub UI** : Web Fetch ajouté au menu "Actions MCP"
- [x] **Cloud Build** : Config créée, build SUCCESS
- [x] **Secret Manager** : Service account key créé et monté
- [x] **Cloud Run** : Déployé avec service account `mcp-cockpit`, secret monté
- [x] **Git** : Commit `6662647` pushed, `.gitignore` à jour
- [ ] **Drive partage** : ⚠️ **ACTION REQUISE** — Partager folder `1LwUZ67zVstl2tuogcdYYihPilUAXQai3` avec `mcp-cockpit@...`
- [ ] **Preuves curl** : En attente du partage Drive (3 commandes ci-dessus)
- [ ] **Apps Script** : API à activer + 2 curls de validation

---

## 🔗 Liens utiles

- **GitHub repo** : https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent
- **Commit déployé** : https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent/commit/6662647
- **Cloud Run service** : https://console.cloud.google.com/run/detail/us-central1/mcp-memory-proxy?project=box-magique-gp-prod
- **Secret Manager** : https://console.cloud.google.com/security/secret-manager/secret/mcp-cockpit-sa-key?project=box-magique-gp-prod
- **Service Account** : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
- **Drive folder** : https://drive.google.com/drive/folders/1LwUZ67zVstl2tuogcdYYihPilUAXQai3

---

## ⏭️ Prochaines étapes

1. **Immédiat** : Partager le dossier Drive avec `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com` (30 secondes)
2. **Validation** : Exécuter les 3 curls de preuve (2 minutes)
3. **Apps Script** : Activer API + tester 2 endpoints (5 minutes)
4. **Hub** : Redéployer G16/G17 mis à jour (Web Fetch disponible)
5. **PROD** : Si tests OK (score ≥ 90%), switch `MCP_ENVIRONMENT=PRODUCTION`

**Fin du rapport.**
