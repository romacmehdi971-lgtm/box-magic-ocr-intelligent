# PHASE 2 — CHECKLIST DE VALIDATION COMPLÈTE
# Extension Contrôlée des Accès MCP
**Date**: 2026-02-20  
**Version**: 1.0 One-Shot  
**Projet**: IAPF Hub Memory — MCP Proxy Extension

---

## 📋 VALIDATION STRUCTURE

- **Total**: 58 critères OK/KO
- **Format**: ✅ OK | ❌ KO | ⏳ En cours | ⏭️ N/A
- **Exigence**: Minimum 52/58 (≥90%) pour GO PROD
- **Blocage**: Tout KO sur critères CRITICAL bloque PROD

---

## 1️⃣ BACKEND PROXY (20 critères)

### 1.1 Infrastructure & Configuration (5 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 1.1.1 | Cloud Run service `mcp-memory-proxy` déployé et accessible | CRITICAL | ⏳ | URL: https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app |
| 1.1.2 | Toutes les APIs GCP activées (Drive, Apps Script, Cloud Run, Logging, Secret Manager) | CRITICAL | ⏳ | Console GCP > APIs & Services |
| 1.1.3 | Service Account avec permissions correctes (roles: `roles/drive.readonly`, `roles/cloudrun.viewer`, `roles/logging.viewer`, `roles/secretmanager.viewer`, `roles/script.readonly`) | CRITICAL | ⏳ | IAM configuration |
| 1.1.4 | Variables d'environnement configurées (STAGING vs PROD) | HIGH | ⏳ | `MCP_ENVIRONMENT=STAGING` par défaut |
| 1.1.5 | Healthcheck `/health` retourne 200 + version + build info | MEDIUM | ⏳ | Test avec curl |

### 1.2 Endpoints Drive (4 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 1.2.1 | `GET /drive/tree` fonctionne avec pagination (limit ≤ 200) | HIGH | ⏳ | 20 appels consécutifs sans erreur |
| 1.2.2 | `GET /drive/file/{file_id}/metadata` retourne métadonnées complètes + redaction emails | HIGH | ⏳ | Vérifier redaction pattern `[REDACTED_EMAIL]` |
| 1.2.3 | `GET /drive/search` fonctionne avec query ≤ 100 chars + pagination | MEDIUM | ⏳ | Test avec 3 queries différentes |
| 1.2.4 | `GET /drive/file/{file_id}/text` bounded read (max 1MB par défaut) | MEDIUM | ⏳ | Vérifier truncation |

### 1.3 Endpoints Apps Script (3 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 1.3.1 | `GET /apps-script/project/{script_id}/deployments` liste déploiements (limit ≤ 50) | HIGH | ⏳ | 10 appels consécutifs |
| 1.3.2 | `GET /apps-script/project/{script_id}/structure` retourne liste fichiers + fonctions | HIGH | ⏳ | Vérifier extraction noms fichiers/fonctions |
| 1.3.3 | Apps Script API activée + OAuth scopes configurés (`script.projects.readonly`) | CRITICAL | ⏳ | Console GCP + appsscript.json |

### 1.4 Endpoints Cloud Run + Logging (3 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 1.4.1 | `GET /cloud-run/service/{name}/status` retourne état service (revision, image digest, env) | HIGH | ⏳ | 10 appels consécutifs |
| 1.4.2 | `POST /cloud-logging/query` fonctionne avec pagination (limit ≤ 1000) | MEDIUM | ⏳ | Tester avec time-range |
| 1.4.3 | Cloud Run Admin API + Cloud Logging API activées | CRITICAL | ⏳ | Console GCP |

### 1.5 Endpoints Secret Manager (4 critères) — CRITICAL

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 1.5.1 | `GET /secrets/list` retourne métadonnées SANS valeurs (toujours `[REDACTED]`) | CRITICAL | ⏳ | Vérifier aucune valeur cleartext dans logs/response |
| 1.5.2 | `GET /secrets/{id}/reference` retourne référence (projects/.../versions/X) SANS valeur | CRITICAL | ⏳ | Pattern: `projects/{pid}/secrets/{sid}/versions/{v}` |
| 1.5.3 | `POST /secrets/create` mode DRY_RUN OK (dry_run=true par défaut) | CRITICAL | ⏳ | Vérifier aucune création réelle |
| 1.5.4 | `POST /secrets/create` mode APPLY OK (dry_run=false) + GO confirmation requise | CRITICAL | ⏳ | Créer secret test, vérifier ID retourné |

### 1.6 Endpoints Web & Terminal (3 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 1.6.1 | `POST /web/search` fonctionne avec allowlist domains + quotas | MEDIUM | ⏳ | Vérifier quota restant dans response |
| 1.6.2 | `POST /web/fetch` allowlist validation + max_size ≤ 5MB | MEDIUM | ⏳ | Tester avec URL bloquée (doit échouer) |
| 1.6.3 | `POST /terminal/run` allowlist strict (READ_ONLY commands only par défaut) | HIGH | ⏳ | Tester `gcloud run services describe` |

### 1.7 Governance & Redaction (3 critères) — CRITICAL

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 1.7.1 | Tous les endpoints retournent `run_id` unique (format: `{domain}_{action}_{uuid}`) | CRITICAL | ⏳ | Vérifier pattern dans 50 responses |
| 1.7.2 | Redaction patterns appliqués (emails, tokens, IDs, secrets) | CRITICAL | ⏳ | Patterns: `[REDACTED_EMAIL]`, `[REDACTED_TOKEN]`, `[REDACTED]` |
| 1.7.3 | WRITE endpoints DRY_RUN par défaut (dry_run=true sauf si explicitement false) | CRITICAL | ⏳ | Vérifier défauts dans code |

---

## 2️⃣ HUB APPS SCRIPT (15 critères)

### 2.1 Menu & UI (3 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 2.1.1 | Menu "Actions MCP" visible dans menu IAPF Memory | HIGH | ⏳ | Vérifier après onOpen() |
| 2.1.2 | 14 entrées menu présentes (Drive 3, Apps Script 2, Cloud Run 1, Secrets 4, Web 1, Terminal 1) | HIGH | ⏳ | Compter entrées |
| 2.1.3 | Popup UX claire : description action + mode (READ_ONLY/DRY_RUN/APPLY) + résultat final | MEDIUM | ⏳ | Tester 5 actions différentes |

### 2.2 HTTP Client Wrappers (6 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 2.2.1 | Fichier `G17_MCP_HTTP_CLIENT_EXTENDED.gs` présent et chargé | CRITICAL | ⏳ | Vérifier import dans projet |
| 2.2.2 | Variable globale `MCP_HTTP` accessible (IIFE pattern) | HIGH | ⏳ | Test: `typeof MCP_HTTP` doit retourner "object" |
| 2.2.3 | API Key récupérée depuis SETTINGS.mcp_api_key automatiquement | CRITICAL | ⏳ | Tester avec clé valide vs invalide |
| 2.2.4 | Retry logic (3 tentatives) + exponential backoff fonctionnel | MEDIUM | ⏳ | Simuler erreur réseau |
| 2.2.5 | Timeout default 30s configuré et respecté | MEDIUM | ⏳ | Tester avec endpoint lent |
| 2.2.6 | Toutes les méthodes MCP_HTTP.* (18 wrappers) accessibles et fonctionnelles | HIGH | ⏳ | Test unitaire chaque wrapper |

### 2.3 Actions Drive (3 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 2.3.1 | `MCP_ACTION_driveListTree()` : prompt folder_id + affiche résultat + run_id | HIGH | ⏳ | Tester avec folder ARCHIVES |
| 2.3.2 | `MCP_ACTION_driveFileMetadata()` : prompt file_id + affiche métadonnées | HIGH | ⏳ | Tester avec fichier existant |
| 2.3.3 | `MCP_ACTION_driveSearch()` : prompt query + affiche résultats | MEDIUM | ⏳ | Tester recherche "IAPF" |

### 2.4 Actions Apps Script (2 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 2.4.1 | `MCP_ACTION_appsScriptDeployments()` : récupère scriptId automatique + liste déploiements | HIGH | ⏳ | `ScriptApp.getScriptId()` |
| 2.4.2 | `MCP_ACTION_appsScriptStructure()` : affiche nb fichiers + nb fonctions | HIGH | ⏳ | Vérifier extraction correcte |

### 2.5 Actions Secret Manager (4 critères) — CRITICAL

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 2.5.1 | `MCP_ACTION_secretsList()` : affiche liste secrets + warning "valeurs JAMAIS retournées" | CRITICAL | ⏳ | UI doit afficher ⚠️ explicite |
| 2.5.2 | `MCP_ACTION_secretGetReference()` : prompt secret_id + affiche reference + [REDACTED] | CRITICAL | ⏳ | Vérifier UI redaction |
| 2.5.3 | `MCP_ACTION_secretCreateDryRun()` : DRY_RUN avec message clair "not applied" | CRITICAL | ⏳ | Mode = DRY_RUN dans UI |
| 2.5.4 | `MCP_ACTION_secretCreateApply()` : APPLY avec popup GO confirmation obligatoire | CRITICAL | ⏳ | Popup YES/NO avant APPLY |

---

## 3️⃣ LOGGING & JOURNALISATION (8 critères)

### 3.1 MEMORY_LOG Integration (4 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 3.1.1 | Chaque action MCP écrit dans MEMORY_LOG (type=MCP_ACTION, run_id présent) | CRITICAL | ⏳ | Vérifier 20 actions → 20 lignes MEMORY_LOG |
| 3.1.2 | Format MEMORY_LOG : timestamp, type, title, details, author, source, tags, run_id | HIGH | ⏳ | Vérifier colonnes |
| 3.1.3 | Backend proxy écrit dans LOGS_SYSTEM via API (si endpoint `/memory/log` existe) | MEDIUM | ⏳ | Vérifier logs backend |
| 3.1.4 | run_id unique et traçable (pas de collision sur 1000 appels) | HIGH | ⏳ | Test collision UUID |

### 3.2 LOGS Sheet & Errors (2 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 3.2.1 | Onglet LOGS_SYSTEM contient logs proxy + timestamp + level | MEDIUM | ⏳ | Vérifier format |
| 3.2.2 | Erreurs API loggées dans ERRORS sheet (si échec critique) | MEDIUM | ⏳ | Simuler erreur 500 |

### 3.3 Redaction Logs (2 critères) — CRITICAL

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 3.3.1 | Aucun secret cleartext dans MEMORY_LOG, LOGS_SYSTEM, ERRORS | CRITICAL | ⏳ | Audit manuel 100 lignes logs |
| 3.3.2 | Emails, tokens, IDs redacted dans tous les logs Hub + Proxy | CRITICAL | ⏳ | Pattern check |

---

## 4️⃣ CONFIGURATION & ACCÈS (10 critères)

### 4.1 SETTINGS Sheet (4 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 4.1.1 | Clé `mcp_api_key` présente et valide dans SETTINGS | CRITICAL | ⏳ | Tester avec/sans clé |
| 4.1.2 | Clés Phase 2 ajoutées : `mcp_gcp_project_id`, `mcp_gcp_region`, `mcp_environment` | HIGH | ⏳ | Vérifier 8 nouvelles clés |
| 4.1.3 | Valeurs default STAGING configurées (mcp_environment=STAGING) | HIGH | ⏳ | Avant validation PROD |
| 4.1.4 | Clés allowlist/quotas configurées : `mcp_allowed_domains`, `mcp_web_quota`, `mcp_terminal_quota` | MEDIUM | ⏳ | Domaines allowlist |

### 4.2 Drive Access Model (3 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 4.2.1 | Modèle d'accès Drive défini (shared drive / folder share / impersonation) | HIGH | ⏳ | Documenter choix |
| 4.2.2 | Service Account a accès lecture au folder ARCHIVES (archives_folder_id) | HIGH | ⏳ | Test list tree |
| 4.2.3 | Instructions partage prêtes (share folder avec SA email) | MEDIUM | ⏳ | Doc pour Élia |

### 4.3 GCP APIs & Permissions (3 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 4.3.1 | 5 APIs activées : Drive, Apps Script, Cloud Run, Cloud Logging, Secret Manager | CRITICAL | ⏳ | Console GCP |
| 4.3.2 | Service Account roles configurés (6 roles minimum) | CRITICAL | ⏳ | IAM audit |
| 4.3.3 | Apps Script OAuth scopes ajoutés dans appsscript.json | HIGH | ⏳ | `oauthScopes` array |

---

## 5️⃣ PAGINATION & QUOTAS (5 critères)

### 5.1 Pagination (3 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 5.1.1 | Endpoints avec `limit` parameter respectent max (Drive ≤200, Apps Script ≤50, Logging ≤1000) | HIGH | ⏳ | Test avec limit=9999 (doit cap) |
| 5.1.2 | `page_token` fonctionnel pour endpoints paginés (Drive search, Logging query) | MEDIUM | ⏳ | Tester 3 pages |
| 5.1.3 | Response indique `next_page_token` si données tronquées | MEDIUM | ⏳ | Vérifier structure |

### 5.2 Quotas & Limits (2 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 5.2.1 | Web search quota tracking (quota_remaining dans response) | MEDIUM | ⏳ | Décrémenter à chaque appel |
| 5.2.2 | Size limits appliqués (Drive read ≤1MB, Web fetch ≤5MB, Query ≤100 chars) | HIGH | ⏳ | Tester limites |

---

## 6️⃣ DÉPLOIEMENT & DOCS (5 critères)

### 6.1 Déploiement (3 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 6.1.1 | Script déploiement one-shot prêt (deploy.sh) | MEDIUM | ⏳ | Test en STAGING |
| 6.1.2 | Dockerfile mis à jour + requirements.txt inclut nouveaux packages | MEDIUM | ⏳ | build image Docker |
| 6.1.3 | Variables d'environnement Cloud Run configurées (8 vars minimum) | HIGH | ⏳ | Console Cloud Run |

### 6.2 Documentation (2 critères)

| # | Critère | Type | Status | Notes |
|---|---------|------|--------|-------|
| 6.2.1 | Guide déploiement one-shot complet (PHASE2_GUIDE_DEPLOIEMENT_ONESHOT.md) | HIGH | ⏳ | 5-10 min setup |
| 6.2.2 | Instructions finales pour Élia (partage Drive, secrets IDs, validation) | HIGH | ⏳ | PHASE2_INSTRUCTIONS_FINALES.md |

---

## 📊 SCORECARD FINALE

### Résumé par Section

| Section | Total | OK | KO | En cours | Score | Status |
|---------|-------|----|----|----------|-------|--------|
| Backend Proxy | 20 | 0 | 0 | 20 | 0% | ⏳ |
| Hub Apps Script | 15 | 0 | 0 | 15 | 0% | ⏳ |
| Logging & Journalisation | 8 | 0 | 0 | 8 | 0% | ⏳ |
| Configuration & Accès | 10 | 0 | 0 | 10 | 0% | ⏳ |
| Pagination & Quotas | 5 | 0 | 0 | 5 | 0% | ⏳ |
| Déploiement & Docs | 5 | 0 | 0 | 5 | 0% | ⏳ |
| **TOTAL** | **58** | **0** | **0** | **58** | **0%** | ⏳ |

### Critères CRITICAL (15 total)

| # | Critère | Status | Blocage PROD |
|---|---------|--------|--------------|
| 1.1.1 | Cloud Run déployé | ⏳ | OUI |
| 1.1.2 | APIs GCP activées | ⏳ | OUI |
| 1.1.3 | Service Account permissions | ⏳ | OUI |
| 1.3.3 | Apps Script API + OAuth | ⏳ | OUI |
| 1.4.3 | Cloud Run + Logging API | ⏳ | OUI |
| 1.5.1 | Secrets list sans valeurs | ⏳ | OUI |
| 1.5.2 | Secret reference sans valeur | ⏳ | OUI |
| 1.5.3 | Secret create DRY_RUN | ⏳ | OUI |
| 1.5.4 | Secret create APPLY + GO | ⏳ | OUI |
| 1.7.1 | run_id unique | ⏳ | OUI |
| 1.7.2 | Redaction patterns | ⏳ | OUI |
| 1.7.3 | WRITE DRY_RUN default | ⏳ | OUI |
| 2.2.1 | G17 présent | ⏳ | OUI |
| 2.2.3 | API Key SETTINGS | ⏳ | OUI |
| 2.5.1-4 | Actions Secrets UI | ⏳ | OUI |
| 3.1.1 | MEMORY_LOG write | ⏳ | OUI |
| 3.3.1-2 | Redaction logs | ⏳ | OUI |
| 4.1.1 | mcp_api_key valide | ⏳ | OUI |
| 4.3.1-2 | GCP APIs + SA roles | ⏳ | OUI |

---

## ⚠️ DÉCISION GO / NO-GO PROD

### Seuils de Validation

- **GO PROD** : Score global ≥ 90% (52/58) ET tous critères CRITICAL = ✅
- **GO STAGING ONLY** : Score 70-89% (41-51/58) OU 1-2 critères CRITICAL = ❌
- **NO-GO** : Score < 70% (< 41/58) OU ≥ 3 critères CRITICAL = ❌

### Process de Validation

1. **Phase 2.1** : Backend + Hub déployés en STAGING
2. **Phase 2.2** : Exécuter 20 appels par endpoint (READ_ONLY)
3. **Phase 2.3** : Tester 5 actions WRITE (DRY_RUN puis APPLY avec GO)
4. **Phase 2.4** : Audit logs (MEMORY_LOG + redaction)
5. **Phase 2.5** : Remplir checklist (OK/KO pour chaque critère)
6. **Phase 2.6** : Calculer score + décision GO/NO-GO

### Notes de Validation

- Documenter chaque KO avec raison + fix proposé
- Capturer run_id de chaque test pour traçabilité
- Screenshots des popups UI pour validation UX
- Export MEMORY_LOG + LOGS_SYSTEM après tests

---

## 📝 ANNEXES

### A1. Commandes Test Validation

```bash
# Backend Health
curl https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app/health

# Drive List Tree (20 appels)
for i in {1..20}; do
  curl -H "X-API-Key: $API_KEY" \
    "https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app/drive/tree?folder_id=1ABC...&limit=50"
done

# Secret List (redaction check)
curl -H "X-API-Key: $API_KEY" \
  "https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app/secrets/list?limit=10" \
  | grep -E '\[REDACTED\]'

# Terminal Run READ_ONLY
curl -X POST -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"command":"gcloud run services describe mcp-memory-proxy --region=us-central1","mode":"READ_ONLY"}' \
  "https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app/terminal/run"
```

### A2. Hub Tests Apps Script

```javascript
// G16 UI Test
function TEST_driveListTree() {
  MCP_ACTION_driveListTree(); // Prompt folder_id
}

// G17 HTTP Test
function TEST_httpClientDirect() {
  var resp = MCP_HTTP.driveSearch("IAPF", {limit: 5});
  Logger.log("Response: " + JSON.stringify(resp));
  return resp.ok && resp.run_id;
}

// MEMORY_LOG Validation
function TEST_memoryLogWritten() {
  var before = SpreadsheetApp.getActiveSpreadsheet()
    .getSheetByName("MEMORY_LOG").getLastRow();
  
  MCP_ACTION_driveSearch(); // Execute action
  
  var after = SpreadsheetApp.getActiveSpreadsheet()
    .getSheetByName("MEMORY_LOG").getLastRow();
  
  return after > before; // Should have +1 row
}
```

---

**Dernière mise à jour** : 2026-02-20 18:30 UTC  
**Responsable validation** : Élia (MCP Coordinator)  
**Contact support** : GitHub Issues — box-magic-ocr-intelligent
