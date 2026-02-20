# 🚀 PHASE 2 — Résumé Exécutif

**Date** : 2026-02-20 19:05 UTC  
**Status** : ✅ Spécification complète (18 endpoints)  
**Documentation** : PHASE2_SPEC_ENDPOINTS_MCP.md (28 KB)

---

## 🎯 Objectif Phase 2

**Extension contrôlée des accès MCP** pour qu'Élia puisse opérer sur l'environnement Google **sans blocages d'accès** et **sans friction**.

**Résultat attendu** : Un seul menu "Actions MCP" avec 18 endpoints couvrant 6 domaines (Drive, Apps Script, Cloud Run, Secrets, Web, Terminal).

---

## 📊 Architecture globale

```
┌─────────────────────────────────────────────────────────────────┐
│                  GOOGLE SHEETS — HUB IAPF                      │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Menu "Actions MCP" (G16_MCP_ACTIONS_EXTENDED.gs)       │  │
│  │                                                          │  │
│  │  1️⃣ Drive (4 endpoints)     READ_ONLY                   │  │
│  │  2️⃣ Apps Script (4 endpoints) READ_ONLY                 │  │
│  │  3️⃣ Cloud Run (3 endpoints)  READ_ONLY                  │  │
│  │  4️⃣ Secrets (4 endpoints)    READ_ONLY + WRITE gouverné │  │
│  │  5️⃣ Web (2 endpoints)        READ_ONLY                  │  │
│  │  6️⃣ Terminal (1 endpoint)    READ_ONLY + WRITE gouverné │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  G14_MCP_HTTP_CLIENT.gs (wrappers HTTP)                 │  │
│  │  + run_id unique, journalisation MEMORY_LOG             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓ HTTPS + X-API-Key
┌─────────────────────────────────────────────────────────────────┐
│         CLOUD RUN — MCP Memory Proxy (Backend)                 │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Nouveaux endpoints Phase 2:                            │  │
│  │                                                          │  │
│  │  GET  /drive/tree                                       │  │
│  │  GET  /drive/file/{id}/metadata                         │  │
│  │  GET  /drive/search                                     │  │
│  │  GET  /drive/file/{id}/content                          │  │
│  │  GET  /apps-script/project/{id}/deployments            │  │
│  │  GET  /apps-script/project/{id}/structure              │  │
│  │  GET  /apps-script/project/{id}/logs                   │  │
│  │  GET  /cloud-run/service/{name}/status                 │  │
│  │  POST /cloud-logging/query                             │  │
│  │  GET  /secrets/list                                     │  │
│  │  GET  /secrets/{id}/reference                           │  │
│  │  POST /secrets/create        [WRITE gouverné]          │  │
│  │  POST /secrets/{id}/rotate   [WRITE gouverné]          │  │
│  │  POST /web/search                                       │  │
│  │  POST /web/fetch                                        │  │
│  │  POST /terminal/run          [WRITE gouverné]          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                             ↓                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Gouvernance (middleware):                              │  │
│  │  • Redaction systématique (secrets, tokens, emails)    │  │
│  │  • Journalisation avec run_id unique                   │  │
│  │  • Pagination + limites (anti payload géant)           │  │
│  │  • Mode DRY_RUN disponible (WRITE)                     │  │
│  │  • Validation GO (WRITE_APPLY)                         │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              APIs Google Cloud / GCP Services                  │
│                                                                 │
│  Drive API • Apps Script API • Cloud Run API                   │
│  Secret Manager API • Cloud Logging API                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 18 Endpoints (6 domaines)

### 1️⃣ Google Drive (Priorité 1) — 4 endpoints

| Endpoint | Méthode | Gouvernance | Description |
|----------|---------|-------------|-------------|
| `/drive/tree` | GET | READ_ONLY | Liste récursive folder (max depth 5) |
| `/drive/file/{id}/metadata` | GET | READ_ONLY | Métadonnées complètes fichier |
| `/drive/search` | GET | READ_ONLY | Recherche par nom/regex (max 200 résultats) |
| `/drive/file/{id}/content` | GET | READ_ONLY | Lire contenu MD/JSON/TXT (max 5MB) |

**🎯 But** : Vérifier présence + dates des fichiers de gouvernance sans UI Drive.

---

### 2️⃣ Apps Script (Priorité 2) — 4 endpoints

| Endpoint | Méthode | Gouvernance | Description |
|----------|---------|-------------|-------------|
| `/apps-script/project/{id}/deployments` | GET | READ_ONLY | Liste deployments (id, version, url) |
| `/apps-script/project/{id}/structure` | GET | READ_ONLY | Structure projet (fichiers + functions) |
| `/apps-script/project/{id}/logs` | GET | READ_ONLY | Logs/executions Apps Script |
| `/apps-script/project/{id}/version-info` | GET | READ_ONLY | Info dernière version |

**🎯 But** : Éviter "mauvaise version déployée", diagnostiquer sans UI.

---

### 3️⃣ Cloud Run + Logging (Priorité 3) — 3 endpoints

| Endpoint | Méthode | Gouvernance | Description |
|----------|---------|-------------|-------------|
| `/cloud-run/service/{name}/status` | GET | READ_ONLY | Status service (revision, image digest) |
| `/cloud-logging/query` | POST | READ_ONLY | Query logs (pagination + time-range) |
| `/cloud-run/job/{name}/status` | GET | READ_ONLY | Status Cloud Run Job + executions |

**🎯 But** : Diagnostiquer prod/staging sans console.

---

### 4️⃣ Secret Manager (Priorité 4) — 4 endpoints **Gouvernés**

| Endpoint | Méthode | Gouvernance | Description |
|----------|---------|-------------|-------------|
| `/secrets/list` | GET | READ_ONLY | Liste secrets + métadonnées + labels |
| `/secrets/{id}/reference` | GET | READ_ONLY | Référence secret (jamais la valeur) |
| `/secrets/create` | POST | **WRITE** | Créer secret (DRY_RUN + APPLY) |
| `/secrets/{id}/rotate` | POST | **WRITE** | Rotater secret (DRY_RUN + APPLY) |

**🎯 But** : Permettre à Élia de "mettre les clés au bon endroit" sans exposition.

⚠️ **IMPORTANT** : Jamais de valeur secret en clair (seulement références).

---

### 5️⃣ Web Access (Observabilité) — 2 endpoints

| Endpoint | Méthode | Gouvernance | Description |
|----------|---------|-------------|-------------|
| `/web/search` | POST | READ_ONLY | Web search contrôlé (allowlist domaines) |
| `/web/fetch` | POST | READ_ONLY | Fetch URL contrôlé (quota 100/jour) |

**🎯 But** : Quand une doc Google change, Élia sait retrouver l'info.

**Limites** : Allowlist domaines stricte (configurable SETTINGS), quota 100/jour.

---

### 6️⃣ Terminal / Command Runner (Option) — 1 endpoint **Gouverné**

| Endpoint | Méthode | Gouvernance | Description |
|----------|---------|-------------|-------------|
| `/terminal/run` | POST | READ_ONLY + **WRITE** | Command runner cadré (allowlist commandes) |

**🎯 But** : Exécuter checks techniques rapides sans friction.

**Allowlist READ_ONLY** : `gcloud run services describe`, `gcloud logging read`, `gcloud secrets list`, `gsutil ls`  
**Allowlist WRITE** : `gcloud run services update`, `gcloud secrets create` (après GO)

---

## 🔒 Gouvernance & Sécurité

### Modes d'action

| Mode | Description | GO requis | Log type | DRY_RUN |
|------|-------------|-----------|----------|---------|
| `READ_ONLY` | Lecture seule | ❌ Non | CONSTAT | N/A |
| `WRITE_DRY_RUN` | Simulation WRITE | ❌ Non | CONSTAT | ✅ Oui |
| `WRITE_APPLY` | Action réelle | ✅ **Oui** | DECISION | ❌ Non |

### Validation GO (WRITE_APPLY)

**Un seul GO** via popup Google Sheets (pas de multi-confirm) :
```
MCP — {Action} (WRITE_APPLY)

Domaine : Secret Manager
Action  : Create secret "new_api_key"
Params  : labels={env:staging}

⚠️ Cette action modifiera l'environnement STAGING

Mode DRY_RUN : disponible pour tester avant application

Continuer avec WRITE_APPLY ?
[Oui] [Non]
```

### Journalisation MEMORY_LOG

**Obligatoire pour TOUTES les actions** (READ comme WRITE) :

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

**Format** : `{domain}_{action}_{timestamp}_{random6}`

**Exemples** :
- `drive_tree_1708617600_abc123`
- `secrets_create_1708617613_kkk111`

**Utilisation** :
- Corrélation logs backend ↔ MEMORY_LOG
- Recherche rapide dans LOGS
- Traçabilité complète

### Redaction systématique

**Patterns redactés automatiquement** (backend proxy) :

| Pattern | Remplacement | Domaines |
|---------|--------------|----------|
| `sk-[A-Za-z0-9]+` | `[REDACTED_API_KEY]` | Tous |
| Email addresses | `[REDACTED_EMAIL]` | Drive, Apps Script, Logs |
| `AIza[A-Za-z0-9_-]{35}` | `[REDACTED_GCP_KEY]` | Tous |
| Secret values | `[REDACTED_SECRET_VALUE]` | Secret Manager |
| Token JWT `eyJ...` | `[REDACTED_JWT]` | Tous |
| `ghp_[A-Za-z0-9]+` | `[REDACTED_GITHUB_TOKEN]` | Web, Terminal |

### Pagination & Limites

**Anti payload géant** :

| Domaine | Limite par page | Limite max | Time-range max |
|---------|-----------------|------------|----------------|
| Drive tree | 100 (max 500) | 500 items/niveau | N/A |
| Drive search | 50 (max 200) | 200 résultats | N/A |
| Apps Script logs | 50 (max 200) | 200 logs | 30 jours |
| Cloud Logging | 100 (max 1000) | 1000 entries | 7 jours |
| Secrets list | 50 (max 200) | 200 secrets | N/A |
| Web search | 10 (max 10) | 10 résultats | N/A |

---

## 🎯 Menu unifié "Actions MCP"

**Nouveau fichier** : `G16_MCP_ACTIONS_EXTENDED.gs`

### Structure menu

```
IAPF Memory (menu principal)
├── ...
└── Actions MCP (sous-menu)
    ├── 📂 Drive
    │   ├── 🔍 List tree folder
    │   ├── 📄 Get file metadata
    │   ├── 🔎 Search files
    │   └── 📖 Read file content
    ├── ⚙️ Apps Script
    │   ├── 📦 List deployments
    │   ├── 🗂️ Project structure
    │   ├── 📝 Read logs
    │   └── ℹ️ Version info
    ├── ☁️ Cloud Run
    │   ├── 🚀 Service status
    │   ├── 📊 Query logs
    │   └── 🔧 Job status
    ├── 🔐 Secret Manager
    │   ├── 📋 List secrets (READ)
    │   ├── 🔗 Get reference (READ)
    │   ├── ➕ Create secret (WRITE)
    │   └── 🔄 Rotate secret (WRITE)
    ├── 🌐 Web
    │   ├── 🔍 Web search
    │   └── 🌍 Fetch URL
    └── 💻 Terminal
        └── ⚡ Run command
```

**Total** : 18 entrées menu (organisées par domaine).

---

## 📦 Fichiers à créer/modifier

### Backend (Cloud Run — memory-proxy)

**Nouveaux fichiers** :
1. `memory-proxy/app/drive.py` — Endpoints Drive (4)
2. `memory-proxy/app/apps_script.py` — Endpoints Apps Script (4)
3. `memory-proxy/app/cloud_run.py` — Endpoints Cloud Run + Logging (3)
4. `memory-proxy/app/secrets.py` — Endpoints Secret Manager (4)
5. `memory-proxy/app/web.py` — Endpoints Web (2)
6. `memory-proxy/app/terminal.py` — Endpoint Terminal (1)
7. `memory-proxy/app/redaction.py` — Redaction systématique
8. `memory-proxy/app/governance.py` — Modes gouvernés + journalisation

**Fichiers modifiés** :
- `memory-proxy/app/main.py` — Router + nouveaux endpoints
- `memory-proxy/app/config.py` — Config Phase 2 (quotas, allowlists, env)

### Hub (Apps Script)

**Nouveaux fichiers** :
1. `HUB_COMPLET/G16_MCP_ACTIONS_EXTENDED.gs` — Menu Actions MCP + actions UI

**Fichiers modifiés** :
2. `HUB_COMPLET/G14_MCP_HTTP_CLIENT.gs` — Wrappers HTTP Phase 2
3. `HUB_COMPLET/G01_UI_MENU.gs` — Ajout sous-menu "Actions MCP"

---

## ✅ Checklist Validation (20 appels consécutifs)

**Critères binaires OK/KO** par endpoint :

### Phase 2.A — Drive (4 endpoints)

| Endpoint | Test | Critère | OK/KO |
|----------|------|---------|-------|
| `/drive/tree` | 20 appels consécutifs | Aucune erreur réseau/ClientResponseError | ⏳ |
| `/drive/tree` | Pagination | Max 500 items/niveau respecté | ⏳ |
| `/drive/tree` | Profondeur | Max depth 5 respecté | ⏳ |
| `/drive/tree` | Journalisation | MEMORY_LOG écrit 20 fois (CONSTAT) | ⏳ |
| `/drive/file/{id}/metadata` | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/drive/file/{id}/metadata` | Redaction | Emails redactés ([REDACTED_EMAIL]) | ⏳ |
| `/drive/file/{id}/metadata` | Journalisation | MEMORY_LOG écrit 20 fois | ⏳ |
| `/drive/search` | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/drive/search` | Pagination | Max 200 résultats respecté | ⏳ |
| `/drive/search` | Journalisation | MEMORY_LOG écrit 20 fois | ⏳ |
| `/drive/file/{id}/content` | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/drive/file/{id}/content` | Limite taille | Max 5MB respecté (truncated si dépassé) | ⏳ |
| `/drive/file/{id}/content` | Types autorisés | Seulement text/plain, text/markdown, application/json | ⏳ |

### Phase 2.B — Apps Script (4 endpoints)

| Endpoint | Test | Critère | OK/KO |
|----------|------|---------|-------|
| `/apps-script/project/{id}/deployments` | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/apps-script/project/{id}/deployments` | Journalisation | MEMORY_LOG écrit 20 fois | ⏳ |
| `/apps-script/project/{id}/structure` | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/apps-script/project/{id}/structure` | Journalisation | MEMORY_LOG écrit 20 fois | ⏳ |
| `/apps-script/project/{id}/logs` | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/apps-script/project/{id}/logs` | Redaction | Messages secrets redactés | ⏳ |
| `/apps-script/project/{id}/logs` | Time-range | Max 30 jours respecté | ⏳ |

### Phase 2.C — Cloud Run + Logging (3 endpoints)

| Endpoint | Test | Critère | OK/KO |
|----------|------|---------|-------|
| `/cloud-run/service/{name}/status` | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/cloud-run/service/{name}/status` | Journalisation | MEMORY_LOG écrit 20 fois | ⏳ |
| `/cloud-logging/query` | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/cloud-logging/query` | Pagination | Max 1000 entries respecté | ⏳ |
| `/cloud-logging/query` | Time-range | Max 7 jours respecté | ⏳ |
| `/cloud-logging/query` | Redaction | Secrets dans logs redactés | ⏳ |

### Phase 2.D — Secret Manager (4 endpoints) **CRITIQUE**

| Endpoint | Test | Critère | OK/KO |
|----------|------|---------|-------|
| `/secrets/list` | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/secrets/list` | Redaction | **JAMAIS** de valeur secret en clair | ⏳ |
| `/secrets/list` | Journalisation | MEMORY_LOG écrit 20 fois | ⏳ |
| `/secrets/{id}/reference` | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/secrets/{id}/reference` | Redaction | Champ `value` = `[REDACTED]` | ⏳ |
| `/secrets/create` (DRY_RUN) | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/secrets/create` (DRY_RUN) | Pas d'application | Aucun secret créé réellement | ⏳ |
| `/secrets/create` (DRY_RUN) | Journalisation | MEMORY_LOG type CONSTAT | ⏳ |
| `/secrets/create` (APPLY) | 5 appels consécutifs | Secrets créés réellement | ⏳ |
| `/secrets/create` (APPLY) | Journalisation | MEMORY_LOG type DECISION | ⏳ |
| `/secrets/create` (APPLY) | Redaction | Valeur secret JAMAIS dans logs | ⏳ |
| `/secrets/{id}/rotate` (DRY_RUN) | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/secrets/{id}/rotate` (APPLY) | 5 appels consécutifs | Rotation réelle OK | ⏳ |

### Phase 2.E — Web (2 endpoints)

| Endpoint | Test | Critère | OK/KO |
|----------|------|---------|-------|
| `/web/search` | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/web/search` | Allowlist domaines | Seulement domaines configurés | ⏳ |
| `/web/search` | Quota | Max 100/jour respecté | ⏳ |
| `/web/fetch` | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/web/fetch` | Allowlist domaines | Seulement domaines configurés | ⏳ |
| `/web/fetch` | Limite taille | Max 5MB respecté | ⏳ |

### Phase 2.F — Terminal (1 endpoint) **CRITIQUE**

| Endpoint | Test | Critère | OK/KO |
|----------|------|---------|-------|
| `/terminal/run` (READ_ONLY) | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/terminal/run` (READ_ONLY) | Allowlist commandes | Seulement commandes READ autorisées | ⏳ |
| `/terminal/run` (READ_ONLY) | Journalisation | MEMORY_LOG type CONSTAT | ⏳ |
| `/terminal/run` (WRITE DRY_RUN) | 20 appels consécutifs | Aucune erreur | ⏳ |
| `/terminal/run` (WRITE DRY_RUN) | Pas d'application | Aucune action réelle | ⏳ |
| `/terminal/run` (WRITE APPLY) | 5 appels consécutifs | Actions réelles OK | ⏳ |
| `/terminal/run` (WRITE APPLY) | Journalisation | MEMORY_LOG type DECISION | ⏳ |

**Total** : **50+ critères binaires** (OK/KO)

---

## 🚀 Prochaines étapes

### Étape 1 : Backend (priorité)
1. Implémenter les 18 endpoints (6 fichiers nouveaux)
2. Ajouter middleware gouvernance (redaction + journalisation)
3. Configurer allowlists + quotas (config.py)
4. Tests unitaires (20 appels consécutifs par endpoint)

### Étape 2 : Hub (Apps Script)
1. Créer G16_MCP_ACTIONS_EXTENDED.gs (menu + actions)
2. Mettre à jour G14_MCP_HTTP_CLIENT.gs (wrappers HTTP)
3. Mettre à jour G01_UI_MENU.gs (ajout sous-menu)
4. Tests UI (clic menu → appel backend → log MEMORY_LOG)

### Étape 3 : Configuration
1. Ajouter clés SETTINGS (mcp_gcp_project_id, mcp_web_allowed_domains, etc.)
2. Configurer env vars Cloud Run (MCP_ENVIRONMENT=STAGING)
3. Activer APIs GCP (Drive, Apps Script, Secret Manager, etc.)

### Étape 4 : Validation
1. Exécuter checklist 50+ critères (OK/KO)
2. Vérifier redaction systématique (aucun secret en clair)
3. Vérifier journalisation (MEMORY_LOG complet)
4. Tests PROD vs STAGING (basculer env)

### Étape 5 : Documentation
1. Guide déploiement Phase 2
2. Examples d'usage par domaine
3. Troubleshooting (errors courants)

---

## 📊 Métriques Phase 2

- **Endpoints** : 18 (15 READ_ONLY + 3 WRITE gouvernés)
- **Fichiers backend** : 8 nouveaux (drive.py, apps_script.py, cloud_run.py, secrets.py, web.py, terminal.py, redaction.py, governance.py)
- **Fichiers Hub** : 1 nouveau (G16), 2 modifiés (G14, G01)
- **Configuration** : 8 nouvelles clés SETTINGS
- **Tests** : 50+ critères binaires OK/KO
- **Documentation** : Spécification 28 KB (PHASE2_SPEC_ENDPOINTS_MCP.md)

---

## ✅ Status actuel

- [x] ✅ Spécification complète (18 endpoints, 6 domaines)
- [ ] ⏳ Implémentation backend (8 fichiers)
- [ ] ⏳ Implémentation Hub (G16 + G14 + G01)
- [ ] ⏳ Configuration (SETTINGS + env vars)
- [ ] ⏳ Tests validation (checklist 50+ critères)
- [ ] ⏳ Documentation (guide déploiement + examples)

---

**Date** : 2026-02-20 19:05 UTC  
**Auteur** : Claude Code (Genspark AI Developer)  
**Version** : Phase 2 — Extension contrôlée des accès MCP  
**Prochaine étape** : Implémenter backend proxy (18 endpoints)
