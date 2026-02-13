# MCP Cockpit IAPF - Overview

**Version**: 1.0.0  
**Environment**: PROD  
**Type**: Cloud Run Job (one-shot + schedulable)

---

## 🎯 Qu'est-ce que le MCP Cockpit IAPF ?

Le **MCP Central Cockpit IAPF** est un système de monitoring centralisé pour l'IA Process Factory. Il audite et supervise :

- **Cloud Run** : Status et logs du service OCR intelligent
- **GitHub** : État des repos OCR et CRM
- **Drive** : Architecture des dossiers IAPF
- **Sheets** : Cohérence des données BOX2026 et HUB ORION

### Principes

- **READ-ONLY** : Monitoring sans modification des systèmes audités
- **WRITE contrôlé** : Écriture uniquement dans HUB ORION (logs, snapshots, risks)
- **Cockpit-only** : Isolation totale du runtime OCR (0 impact production)
- **One-shot** : Exécution sur demande ou planifiée

---

## 🏗️ Architecture

```
MCP Cockpit IAPF
│
├── Cloud Run Job
│   ├── Image: gcr.io/box-magique-gp-prod/mcp-cockpit-iapf-healthcheck
│   ├── SA: mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com
│   └── Auth: ADC (Application Default Credentials via metadata)
│
├── Composants
│   ├── config/        Configuration PROD (IDs, URLs, scopes)
│   ├── tools/         Auditeurs (CloudRun, GitHub, Drive, Sheets)
│   ├── orchestrator   Logique de healthcheck
│   ├── utils/         SafeLogger (masquage PII)
│   └── cli            Point d'entrée
│
└── Outputs
    ├── snapshots/     JSON complet de l'état système
    ├── reports/       Markdown human-readable
    └── audit_logs/    Logs structurés JSON
```

### Flow d'exécution

```
1. Trigger (manuel ou scheduler)
   ↓
2. Cloud Run Job démarre (container isolé)
   ↓
3. Authentification via service account metadata
   ↓
4. Audit READ-ONLY (Cloud Run, GitHub, Drive, Sheets)
   ↓
5. Détection de risks & conflicts
   ↓
6. WRITE sur HUB ORION (MEMORY_LOG, SNAPSHOT_ACTIVE)
   ↓
7. Génération artifacts (JSON, MD, logs)
   ↓
8. Job termine (success/failure)
   ↓
9. Artifacts disponibles dans le container
   (optionnel: upload Drive si autorisé)
```

---

## 🔐 Security & IAM

Voir [SECURITY.md](./SECURITY.md) pour les détails complets.

**Service Account** : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`

**Scopes requis** :
- `cloud-platform` : Lecture Cloud Run (status, logs)
- `drive.readonly` : Lecture Drive (architecture folders)
- `spreadsheets` : Lecture BOX2026, Écriture HUB ORION

**Interdictions absolues** :
- ❌ Pas de `drive_rename`, `drive_move`, `drive_delete`
- ❌ Pas de `cloudrun_deploy` ou modification code runtime OCR
- ❌ Pas de `github_push`
- ❌ Pas de secrets en dur dans le code
- ❌ Pas de logs contenant PII/données client

---

## 📦 Configuration PROD

Les ressources PROD ciblées :

### Cloud Run
- Project: `box-magique-gp-prod`
- Region: `us-central1`
- Service: `box-magic-ocr-intelligent`

### GitHub Repos
- OCR: `romacmehdi971-lgtm/box-magic-ocr-intelligent`
- CRM: `romacmehdi971-lgtm/crm-cyril-martins`

### Google Drive
- Root IAPF: `1LwUZ67zVstl2tuogcdYYihPilUAXQai3`
- URL: https://drive.google.com/drive/folders/1LwUZ67zVstl2tuogcdYYihPilUAXQai3

### Google Sheets
- **BOX2026** (READ-ONLY): `1U_tLe3n_1_hL6HcRJ4yrbMDTNMfTKvPsTrbva1Sjc-4`
- **HUB ORION** (WRITE): `1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ`

---

## 🚀 Déploiement

Voir [DEPLOYMENT.md](./DEPLOYMENT.md) pour les instructions complètes.

**Commande one-shot** :
```bash
./deploy_mcp_cockpit_job.sh
```

Cette commande :
1. Active les APIs GCP nécessaires
2. Vérifie le service account
3. Build l'image Docker
4. Déploie le Cloud Run Job
5. Affiche les commandes d'exécution

---

## 🏃 Exécution

Voir [RUNBOOK.md](./RUNBOOK.md) pour les procédures opérationnelles.

### Exécution manuelle (one-shot)
```bash
gcloud run jobs execute mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod
```

### Planification quotidienne (6h UTC)
```bash
gcloud scheduler jobs create http mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1 \
  --schedule='0 6 * * *' \
  --uri='https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/box-magique-gp-prod/jobs/mcp-cockpit-iapf-healthcheck:run' \
  --http-method=POST \
  --oauth-service-account-email=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com
```

---

## 📊 Artifacts Générés

Chaque exécution génère :

1. **Snapshot JSON** (`snapshot_YYYYMMDD_HHMMSSZ.json`)
   - État complet du système
   - Métadata, audits, risks, conflicts
   - ~8-10 KB

2. **Report Markdown** (`healthcheck_YYYYMMDD_HHMMSSZ.md`)
   - Rapport human-readable
   - Sections par système audité
   - ~2-3 KB

3. **Audit Log JSON** (`audit_log_YYYYMMDD_HHMMSSZ.json`)
   - Log structuré de l'exécution
   - Timestamp, actions, résultats
   - ~200-500 bytes

---

## 🔧 Gouvernance IAPF

### HUB ORION - Format MEMORY_LOG

**7 colonnes TSV strictes** :
```
ts_iso	type	title	details	author	source	tags
```

**Exemple** :
```tsv
2026-02-13T06:00:15Z	healthcheck	IAPF Full Healthcheck	{"cloudrun_status":"healthy","github_repos":2,"risks_count":0}	mcp_cockpit	cloud_run_job	audit;monitoring;production
```

**Règles** :
- Séparateur : TAB (`\t`)
- Timestamp : ISO8601 UTC
- Tags : séparés par `;`
- Pas de TAB ou newline dans les valeurs

### Onglets écriture HUB ORION
- `MEMORY_LOG` : Log des événements cockpit
- `SNAPSHOT_ACTIVE` : État actuel du système
- `RISKS` : Risks détectés
- `CONFLITS_DETECTES` : Conflicts inter-systèmes

---

## 🛑 Rollback

Pour désactiver le cockpit sans impacter l'OCR :

```bash
# Supprimer la planification Cloud Scheduler
gcloud scheduler jobs delete mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1 \
  --quiet

# Supprimer le job Cloud Run
gcloud run jobs delete mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod \
  --quiet
```

**Impact** : 0 sur le runtime OCR (isolation stricte)

---

## 🐛 Troubleshooting

Voir [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) pour les erreurs courantes.

### Problèmes fréquents

1. **Permission denied Drive/Sheets**
   - Vérifier que les ressources sont partagées avec `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
   - Scope minimal : Viewer pour Drive, Editor pour HUB ORION

2. **Cloud Run logs empty**
   - Service account a besoin de `roles/logging.viewer` sur le projet

3. **GitHub rate limit**
   - API publique limitée à 60 req/h
   - Recommandation : ajouter `GITHUB_TOKEN` en secret (optionnel)

---

## 📝 Changelog

### v1.0.0 (2026-02-13)
- 🚀 Déploiement PROD initial
- ✅ Cloud Run Job avec service account
- ✅ Format MEMORY_LOG TSV 7 colonnes
- ✅ Documentation complète (5 fichiers MD)
- ✅ Script deploy one-shot
- ✅ Isolation cockpit-only stricte

---

## 📞 Support

**Maintainer** : Mehdi Romac  
**GitHub** : romacmehdi971-lgtm  
**Service Account** : mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com  
**Project** : box-magique-gp-prod

---

**Ressources** :
- [Deployment Guide](./DEPLOYMENT.md)
- [Security & IAM](./SECURITY.md)
- [Runbook](./RUNBOOK.md)
- [Troubleshooting](./TROUBLESHOOTING.md)
