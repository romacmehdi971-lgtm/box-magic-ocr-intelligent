# MCP Cockpit PROD - Pull Request

## 🎯 Objectif

Déployer le MCP Cockpit IAPF en tant que **Cloud Run Job PROD** avec authentification service account et intégration API réelle (Drive, Sheets, Cloud Run).

---

## ✅ DONE Criteria (tests fournis)

### A) Vérification cockpit-only

```bash
git diff main --name-only | grep -E '^(levels|connectors|ocr_engine\.py|utils/)' || echo "✅ 0 fichier runtime OCR modifié"
```

**Résultat** : ✅ **0 fichier runtime OCR modifié**

**Fichiers modifiés** :
- `mcp_cockpit/**` (ajouts PROD)
- `deploy_mcp_cockpit_job.sh` (script déploiement)
- `docs/mcp/**` (documentation complète)
- Aucun fichier runtime OCR touché

---

### B) Exécution en local (mode PROD simulé)

```bash
cd /home/user/webapp
python3 healthcheck_iapf.py healthcheck
```

**Résultat attendu** :
```
✅ IAPF HEALTHCHECK COMPLETE
Status: success
Timestamp: 2026-02-13T12:34:56Z
Risks: 2
Conflicts: 0
Artifacts: 3
```

**Artifacts générés** :
- `mcp_cockpit/reports/snapshot_YYYYMMDD_HHMMSSZ.json`
- `mcp_cockpit/reports/healthcheck_YYYYMMDD_HHMMSSZ.md`
- `mcp_cockpit/reports/audit_log_YYYYMMDD_HHMMSSZ.json`

---

### C) Exécution via Cloud Run Job (PROD)

**Déploiement** :
```bash
./deploy_mcp_cockpit_job.sh
```

**Exécution** :
```bash
gcloud run jobs execute mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod
```

**Logs attendus** :
- `✅ IAPF HEALTHCHECK COMPLETE`
- `Status: success`
- `Artifacts: 3`
- Écriture HUB ORION tentée/réussie

---

### D) HUB mis à jour

Aller sur https://docs.google.com/spreadsheets/d/1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ/edit

**Vérification onglet MEMORY_LOG** :
- Au minimum 1 ligne ajoutée
- Format TSV 7 colonnes : `ts_iso | type | title | details | author | source | tags`
- Séparateur : TAB
- Timestamp : ISO UTC

**Vérification onglet SNAPSHOT_ACTIVE** :
- Mise à jour avec dernier état système

---

## 📦 Changements Inclus

### 1. Cloud Run Job Configuration

**Nouveau** : `mcp_cockpit/Dockerfile.job`
- Image Python 3.11-slim
- gcloud CLI pour audits Cloud Run
- Authentification via metadata (ADC)
- Variables d'environnement : `ENVIRONMENT=PROD`, `USE_METADATA_AUTH=true`

**Nouveau** : `deploy_mcp_cockpit_job.sh`
- Script one-shot de déploiement
- Active les APIs GCP
- Build + Deploy automatique
- Affiche commandes d'exécution

---

### 2. Configuration PROD

**Modifié** : `mcp_cockpit/config/iapf_config.py`
- Ajout `DRIVE_PATHS.root_id` : `1LwUZ67zVstl2tuogcdYYihPilUAXQai3`
- Ajout `SERVICE_ACCOUNT` config avec scopes OAuth
- `use_metadata = True` pour Cloud Run Job

---

### 3. Sheets Tool PROD (API réelle)

**Remplacé** : `mcp_cockpit/tools/sheets_tool.py`
- Mode PROD : Utilise `google-api-python-client`
- Authentification via ADC (metadata)
- Lecture BOX2026 avec Sheets API
- Écriture HUB ORION (MEMORY_LOG, RISKS, CONFLITS_DETECTES)
- Format MEMORY_LOG strict : 7 colonnes TSV
- Fallback gracieux si permissions manquantes

---

### 4. Documentation Complète "Ultra Pro"

**Nouveau** : `docs/mcp/README.md` (7 KB)
- Overview complet
- Architecture flow
- Configuration PROD
- Exemples d'utilisation

**Nouveau** : `docs/mcp/DEPLOYMENT.md` (8.6 KB)
- Prerequisites (APIs, SA, permissions)
- Procédure one-shot
- Tests de validation
- Planification Cloud Scheduler

**Nouveau** : `docs/mcp/SECURITY.md` (10 KB)
- Service Account setup
- Rôles IAM détaillés
- Scopes OAuth
- Interdictions absolues
- Gestion secrets
- SafeLogger PII masking

**Nouveau** : `docs/mcp/RUNBOOK.md` (10.6 KB)
- Exécution one-shot
- Planification automatique
- Monitoring & logs
- Métriques clés
- Alertes recommandées
- Mise à jour & rollback

**Nouveau** : `docs/mcp/TROUBLESHOOTING.md` (11.5 KB)
- 10 erreurs fréquentes + solutions
- Tests de diagnostic
- Procédure de recovery
- Checklist troubleshooting

---

## 🔐 Security & IAM

### Service Account
**Email** : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`

### Permissions requises

**GCP IAM** :
```bash
# Cloud Run
roles/run.viewer
roles/logging.viewer

# (Drive & Sheets via partage explicite)
```

**Drive** :
- Root IAPF (`1LwUZ67zVstl2tuogcdYYihPilUAXQai3`) → Partagé avec SA (Viewer)

**Sheets** :
- BOX2026 (`1U_tLe3n_1_hL6HcRJ4yrbMDTNMfTKvPsTrbva1Sjc-4`) → Partagé avec SA (Viewer)
- HUB ORION (`1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ`) → Partagé avec SA (Editor)

### Pas de secrets en dur
- ✅ Authentification via metadata (ADC)
- ✅ Pas de `credentials.json` en PROD
- ✅ Variables d'environnement non-sensibles uniquement

---

## 📝 Commandes Exactes

### 1. Déployer le job

```bash
cd /home/user/webapp
./deploy_mcp_cockpit_job.sh
```

**Durée** : 5-10 minutes  
**Output** : Image Docker + Job déployé

---

### 2. Exécuter le job (one-shot)

```bash
gcloud run jobs execute mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod
```

**Durée** : 2-5 minutes  
**Output** : Healthcheck complet + artifacts

---

### 3. Créer une planification Cloud Scheduler (quotidien 6h UTC)

```bash
gcloud scheduler jobs create http mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1 \
  --schedule='0 6 * * *' \
  --time-zone='UTC' \
  --uri='https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/box-magique-gp-prod/jobs/mcp-cockpit-iapf-healthcheck:run' \
  --http-method=POST \
  --oauth-service-account-email=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
  --description='MCP Cockpit IAPF - Daily Healthcheck' \
  --project=box-magique-gp-prod
```

---

## 🧪 Tests de Validation

### Test 1 : Build local Docker
```bash
docker build -f mcp_cockpit/Dockerfile.job -t test-cockpit .
docker run --rm test-cockpit --help
```

### Test 2 : Exécution locale (avant déploiement)
```bash
python3 healthcheck_iapf.py healthcheck
# Vérifie : status=success, artifacts=3
```

### Test 3 : Logs Cloud Run Job
```bash
EXECUTION=$(gcloud run jobs executions list \
  --job=mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --limit=1 \
  --format='value(name)')

gcloud run jobs executions describe $EXECUTION \
  --region=us-central1 \
  --format=yaml
```

### Test 4 : HUB ORION updated
Ouvrir https://docs.google.com/spreadsheets/d/1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ/edit  
Vérifier nouvelle ligne dans `MEMORY_LOG`

---

## 🔄 Périmètre IAM

### Service Account créé (si pas existant)
```bash
gcloud iam service-accounts create mcp-cockpit \
  --display-name="MCP Cockpit IAPF" \
  --project=box-magique-gp-prod
```

### Rôles attribués
```bash
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/run.viewer"

gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/logging.viewer"
```

### Partages Drive/Sheets
Voir [DEPLOYMENT.md](./docs/mcp/DEPLOYMENT.md) section "Permissions Drive & Sheets"

---

## 📊 Variables d'Environnement

Le job Cloud Run utilise :

| Variable | Valeur | Description |
|----------|--------|-------------|
| `ENVIRONMENT` | `PROD` | Mode d'exécution |
| `USE_METADATA_AUTH` | `true` | Authentification via metadata (ADC) |

Pas de secrets/credentials en variables d'environnement.

---

## 🎯 Résumé

- ✅ **Cockpit-only strict** : 0 fichier runtime OCR modifié
- ✅ **Cloud Run Job PROD** : Dockerfile + deploy script
- ✅ **Authentification metadata** : Pas de credentials.json
- ✅ **Sheets API réelle** : Lecture BOX2026, Écriture HUB ORION
- ✅ **Format MEMORY_LOG** : TSV 7 colonnes strict
- ✅ **Documentation complète** : 5 fichiers MD (48 KB total)
- ✅ **Tests fournis** : Local, Cloud Run Job, HUB update
- ✅ **Rollback safe** : 0 impact sur OCR runtime

---

## 🔗 Lien PR

https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent/pull/X

---

**Version** : 1.0.0  
**Date** : 2026-02-13  
**Auteur** : romacmehdi971-lgtm
