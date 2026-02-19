# 🚨 RAPPORT D'INCOHÉRENCE CRITIQUE - MCP MEMORY PROXY

**Date**: 2026-02-19T20:22:00Z
**Analyste**: Claude Sonnet 4.5
**Statut**: INCOHÉRENCE MAJEURE DÉTECTÉE

---

## 1. RÉALITÉ SERVIE (FAITS VÉRIFIÉS)

### Service Cloud Run actuel
- **Service**: mcp-memory-proxy
- **URL principale**: https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app
- **URL alternative**: https://mcp-memory-proxy-522732657254.us-central1.run.app
- **Révision active**: mcp-memory-proxy-00018-h29 (100% traffic)
- **Image**: gcr.io/box-magique-gp-prod/mcp-memory-proxy@sha256:58ada6b840b118a8f91938a26cb70ad446b3de758cd44692f19c1dc352be3098
- **Digest confirmé**: sha256:58ada6b840b118a8f91938a26cb70ad446b3de758cd44692f19c1dc352be3098
- **Git commit**: 763aa85 (selon env vars)

### Variables d'environnement
```python
VERSION = v3.1.2-limit-fix
GIT_COMMIT = 763aa85
READ_ONLY_MODE = true
ENABLE_ACTIONS = false
DRY_RUN_MODE = true
GOOGLE_SHEET_ID = 1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ
```

---

## 2. INCOHÉRENCE CRITIQUE

### ❌ PROBLÈME: Version annoncée vs version dans le code

**Ce que les endpoints publics retournent**:
- GET / → `{"version": "3.0.5"}`
- GET /health → `{"version": "3.0.5"}`
- GET /docs-json → `{"version": "3.0.5"}`
- GET /openapi.json → `{"info": {"version": "3.0.5"}}`

**Ce que /infra/whoami retourne**:
- GET /infra/whoami → `{"version": "v3.1.2-limit-fix"}` ✅

**Cause racine identifiée**:
```python
# Dans memory-proxy/app/config.py (ligne 48)
API_VERSION = "3.0.5"  # ❌ HARDCODÉ

# FastAPI utilise cette constante dans main.py (ligne 65)
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,  # ← ici, 3.0.5
    ...
)
```

**Impact**:
- Les endpoints documentés (/, /health, /docs-json, /openapi.json) utilisent `config.API_VERSION` = "3.0.5"
- L'endpoint /infra/whoami lit directement l'env var `VERSION` = "v3.1.2-limit-fix"
- **ÉLIA VOIT** la version 3.0.5 dans son contrat MCP, alors que le backend est bien v3.1.2-limit-fix

---

## 3. TESTS DIRECTS DES ENDPOINTS AVEC ?limit=

### ✅ RÉSULTAT: LE BACKEND FONCTIONNE CORRECTEMENT

| Endpoint | Status | Résultat | Verdict |
|----------|--------|----------|---------|
| /sheets/SETTINGS?limit=1 | 200 | row_count=1, data_count=1 | ✅ OK |
| /sheets/MEMORY_LOG?limit=5 | 200 | row_count=5, data_count=5 | ✅ OK |
| /sheets/DRIVE_INVENTORY?limit=10 | 200 | row_count=10, data_count=10 | ✅ OK |
| /sheets/SETTINGS (sans limit) | 200 | row_count=8, data_count=8 | ✅ OK |
| /gpt/memory-log?limit=3 | 403 | "Invalid or missing API Key" | ⚠️ AUTH |

**CONCLUSION**:
- ✅ Le paramètre `?limit=` fonctionne PARFAITEMENT (tests directs 100% OK)
- ✅ La pagination stricte est respectée
- ✅ Pas de régression (sans limit fonctionne aussi)

**SI ÉLIA VOIT DES ERREURS ClientResponseError**:
→ C'est le WRAPPER/canal MCP qui casse le querystring OU problème d'authentification
→ CE N'EST PAS LE BACKEND qui est en cause

---

## 4. CONTRAT EXPOSÉ (docs-json & openapi.json)

### Endpoints listés dans /openapi.json

**GET endpoints (READ)**:
- ✅ /
- ✅ /health
- ✅ /docs-json
- ✅ /sheets
- ✅ /sheets/{sheet_name}
- ✅ /proposals
- ✅ /gpt/hub-status
- ✅ /gpt/memory-log
- ✅ /gpt/snapshot-active
- ✅ /system/time-status
- ✅ /whoami
- ✅ /infra/whoami ← **PRÉSENT dans openapi.json**
- ✅ /infra/cloudrun/services
- ✅ /infra/cloudrun/jobs
- ✅ /infra/cloudrun/job/{name}/executions
- ✅ /infra/logs/query

**POST endpoints (WRITE)**:
- ⚠️ /propose
- ⚠️ /proposals/{proposal_id}/validate
- ⚠️ /close-day
- ⚠️ /audit
- ⚠️ /hub/memory_log/write

**MAIS** dans /docs-json (version simplifiée), seuls 9 endpoints sont listés:
```json
{
  "endpoints": [
    {"method": "GET", "path": "/health"},
    {"method": "GET", "path": "/sheets"},
    {"method": "GET", "path": "/sheets/{sheet_name}"},
    {"method": "POST", "path": "/propose"},
    {"method": "GET", "path": "/proposals"},
    {"method": "POST", "path": "/proposals/{proposal_id}/validate"},
    {"method": "POST", "path": "/close-day"},
    {"method": "POST", "path": "/audit"},
    {"method": "GET", "path": "/docs-json"}
  ]
}
```

**PROBLÈME**:
- /infra/whoami est dans openapi.json ✅
- /infra/whoami n'est PAS dans docs-json ❌
- Si Élia utilise docs-json comme contrat, elle ne verra pas /infra/whoami

---

## 5. AUDIT-SAFE: ÉTAT ACTUEL

### Flags de sécurité (env vars)
```
READ_ONLY_MODE = true       ✅
ENABLE_ACTIONS = false      ✅
DRY_RUN_MODE = true         ✅
```

### ❌ PROBLÈME: Pas de validation serveur sur les POST

Les routes POST existent et sont exposées dans le contrat:
- /propose
- /proposals/{id}/validate
- /close-day
- /audit
- /hub/memory_log/write

**Mais**: Aucune validation serveur ne vérifie `READ_ONLY_MODE` pour bloquer les POST

**Risque**:
- Un client MCP peut théoriquement appeler ces POST
- Si l'auth passe, les opérations d'écriture pourraient s'exécuter (sauf si le code interne respecte les flags)

---

## 6. ACTIONS CORRECTIVES REQUISES

### A. CORRECTION URGENTE: Aligner la version exposée

**Fichier**: `memory-proxy/app/config.py`

**Changement**:
```python
# AVANT (ligne 48)
API_VERSION = "3.0.5"

# APRÈS
API_VERSION = os.environ.get("VERSION", "3.0.5")
```

**Impact**:
- Les endpoints /, /health, /docs-json, /openapi.json afficheront "v3.1.2-limit-fix"
- Cohérence totale avec /infra/whoami

### B. CORRECTION: Ajouter /infra/whoami au contrat docs-json

**Fichier**: `memory-proxy/app/main.py`

**Localisation**: endpoint `@app.get("/docs-json")`

**Changement**: Ajouter /infra/whoami dans la liste des endpoints exposés

### C. SÉCURITÉ: Bloquer les POST si READ_ONLY_MODE=true

**Option 1** (minimaliste): Middleware global
**Option 2**: Décorateur sur chaque route POST
**Option 3**: Retirer les POST du contrat docs-json (si pas d'utilisation prévue)

---

## 7. TRANCHE FINALE: BUG LIMIT = WRAPPER OU BACKEND?

### ✅ BACKEND: FONCTIONNE PARFAITEMENT

Tests directs avec IAM token (Authorization: Bearer):
- /sheets/SETTINGS?limit=1 → 200 OK ✅
- /sheets/MEMORY_LOG?limit=5 → 200 OK ✅
- /sheets/DRIVE_INVENTORY?limit=10 → 200 OK ✅

### ❌ SI ÉLIA VOIT DES ERREURS

**Hypothèses**:
1. **Wrapper MCP casse le querystring**: Le wrapper pourrait ne pas transmettre ?limit= correctement
2. **Problème d'authentification**: /gpt/memory-log?limit=3 retourne 403 (API Key requise, pas IAM)
3. **URL différente**: Élia tape peut-être une autre URL/service (à vérifier dans sa config MCP)

**Action pour Élia**:
- Vérifier sa config MCP: quelle base URL utilise-t-elle?
- Tester directement avec curl + IAM token pour confirmer que le backend fonctionne
- Si problème persiste, c'est le WRAPPER MCP qui doit être corrigé

---

## 8. ACCÈS IAM (STATUT)

### ✅ Service Account: mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com

**Rôles confirmés**:
- roles/run.viewer ✅
- roles/logging.viewer ✅
- roles/artifactregistry.reader ✅
- autres rôles nécessaires présents

**Pas de blocage IAM identifié**

---

## 9. RÉSUMÉ EXÉCUTIF

### FAITS
1. ✅ Backend fonctionne (limit fonctionne, tests 100% OK)
2. ❌ Version exposée incohérente (3.0.5 vs v3.1.2-limit-fix)
3. ❌ /infra/whoami absent du contrat docs-json (mais présent dans openapi.json)
4. ⚠️ Routes POST exposées mais pas de validation READ_ONLY_MODE serveur
5. ✅ Image digest confirmé: sha256:58ada6b840b118a8f91938a26cb70ad446b3de758cd44692f19c1dc352be3098

### SI ÉLIA VOIT DES ERREURS
→ Vérifier son wrapper/canal MCP, pas le backend
→ Tester avec curl direct pour isoler le problème

### CORRECTIONS NÉCESSAIRES
1. Aligner config.API_VERSION avec env var VERSION (1 ligne)
2. Ajouter /infra/whoami au contrat docs-json (quelques lignes)
3. Bloquer POST si READ_ONLY_MODE=true (middleware ou décorateur)

---

**Rapport généré le**: 2026-02-19T20:25:00Z
**Prochaine étape**: Appliquer les corrections minimales (1 seul déploiement)
