# MCP Cockpit IAPF - Runbook

**Version**: 1.0.0  
**Audience**: Ops, DevOps, SRE  
**Update**: 2026-02-13

---

## 🎯 Vue d'ensemble

Ce runbook décrit les procédures opérationnelles pour exécuter et surveiller le MCP Cockpit IAPF en production.

**Job Cloud Run** : `mcp-cockpit-iapf-healthcheck`  
**Project** : `box-magique-gp-prod`  
**Region** : `us-central1`

---

## 🏃 Exécution One-Shot

### Commande de base

```bash
gcloud run jobs execute mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod
```

**Durée attendue** : 2-5 minutes

**Output attendu** :
```
✓ Creating execution... Done.
  ✓ Provisioning resources...
  ✓ Running...
Done.
Execution [mcp-cockpit-iapf-healthcheck-abc123] completed successfully.
```

---

### Exécution avec suivi en temps réel

```bash
# Lancer le job
EXECUTION=$(gcloud run jobs execute mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod \
  --format='value(metadata.name)')

# Suivre les logs en temps réel
gcloud logging tail "resource.type=cloud_run_job AND resource.labels.job_name=mcp-cockpit-iapf-healthcheck" \
  --project=box-magique-gp-prod
```

---

### Vérifier le résultat

```bash
# Récupérer la dernière exécution
LAST_EXECUTION=$(gcloud run jobs executions list \
  --job=mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod \
  --limit=1 \
  --format='value(name)')

# Voir les détails
gcloud run jobs executions describe $LAST_EXECUTION \
  --region=us-central1 \
  --project=box-magique-gp-prod \
  --format=yaml
```

**Champs clés** :
- `status.conditions[0].status` → `True` si succès
- `status.completionTime` → Date/heure de fin
- `status.logUri` → Lien vers les logs

---

## 📅 Planification Automatique

### Créer une planification Cloud Scheduler

**Quotidien à 6h UTC** :
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

**Autres planifications utiles** :

```bash
# Toutes les heures
--schedule='0 * * * *'

# Toutes les 6h
--schedule='0 */6 * * *'

# Lundi-Vendredi à 9h heure de Paris (8h UTC en hiver, 7h UTC en été)
--schedule='0 8 * * 1-5'
--time-zone='Europe/Paris'
```

---

### Tester la planification

```bash
# Déclencher manuellement
gcloud scheduler jobs run mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1 \
  --project=box-magique-gp-prod

# Vérifier le statut
gcloud scheduler jobs describe mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1 \
  --project=box-magique-gp-prod
```

---

### Lister toutes les planifications

```bash
gcloud scheduler jobs list \
  --location=us-central1 \
  --project=box-magique-gp-prod \
  --filter="name:mcp-cockpit"
```

---

### Suspendre/Reprendre une planification

```bash
# Suspendre
gcloud scheduler jobs pause mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1 \
  --project=box-magique-gp-prod

# Reprendre
gcloud scheduler jobs resume mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1 \
  --project=box-magique-gp-prod
```

---

## 📊 Monitoring & Logs

### Console GCP

**Dashboard job** :
https://console.cloud.google.com/run/jobs/details/us-central1/mcp-cockpit-iapf-healthcheck?project=box-magique-gp-prod

**Métriques disponibles** :
- Nombre d'exécutions (total, réussites, échecs)
- Durée moyenne/min/max d'exécution
- Taux de succès (%)
- Dernière exécution

---

### Logs via gcloud

```bash
# Logs des 24 dernières heures
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=mcp-cockpit-iapf-healthcheck AND timestamp>=\"$(date -u -d '24 hours ago' '+%Y-%m-%dT%H:%M:%SZ')\"" \
  --project=box-magique-gp-prod \
  --limit=100 \
  --format=json

# Logs d'une exécution spécifique
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=mcp-cockpit-iapf-healthcheck AND labels.execution_name=$EXECUTION_NAME" \
  --project=box-magique-gp-prod \
  --format=json
```

---

### Filtrer les logs par niveau

```bash
# Erreurs uniquement
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=mcp-cockpit-iapf-healthcheck AND severity>=ERROR" \
  --project=box-magique-gp-prod \
  --limit=50

# Warnings + Errors
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=mcp-cockpit-iapf-healthcheck AND severity>=WARNING" \
  --project=box-magique-gp-prod \
  --limit=50
```

---

### Logs des planifications Cloud Scheduler

```bash
gcloud logging read \
  "resource.type=cloud_scheduler_job AND resource.labels.job_id=mcp-cockpit-iapf-healthcheck-daily" \
  --project=box-magique-gp-prod \
  --limit=20
```

---

## 📈 Métriques Clés

### Taux de succès attendu
- **> 95%** : Bon
- **80-95%** : Surveiller (possibles problèmes permissions/quotas)
- **< 80%** : Alerte (intervention requise)

### Durée d'exécution
- **Normale** : 2-5 minutes
- **Acceptable** : 5-10 minutes
- **Anormale** : > 10 minutes (possibles timeouts API)

### Risks détectés
- **0-2 risks** : Normal (ex: cloudrun_status unknown en mode simulation)
- **3-5 risks** : Surveiller (possibles drifts de config)
- **> 5 risks** : Alerte (problèmes structurels)

---

## 🔔 Alertes Recommandées

### 1. Alerte Échec Job

```bash
# Créer une alerte si le job échoue 2 fois consécutivement
gcloud alpha monitoring policies create \
  --notification-channels=<CHANNEL_ID> \
  --display-name="MCP Cockpit Job Failures" \
  --condition-display-name="Job Failed 2x" \
  --condition-threshold-value=2 \
  --condition-threshold-duration=3600s \
  --condition-filter='resource.type="cloud_run_job" AND resource.labels.job_name="mcp-cockpit-iapf-healthcheck" AND metric.type="run.googleapis.com/job/completed_execution_count" AND metric.labels.result="failed"' \
  --project=box-magique-gp-prod
```

### 2. Alerte Durée Excessive

```bash
# Alerte si l'exécution dépasse 10 minutes
gcloud alpha monitoring policies create \
  --notification-channels=<CHANNEL_ID> \
  --display-name="MCP Cockpit Slow Execution" \
  --condition-display-name="Execution > 10min" \
  --condition-threshold-value=600 \
  --condition-threshold-duration=60s \
  --condition-filter='resource.type="cloud_run_job" AND resource.labels.job_name="mcp-cockpit-iapf-healthcheck" AND metric.type="run.googleapis.com/job/execution_duration"' \
  --project=box-magique-gp-prod
```

---

## 🔄 Mise à Jour du Job

### Après modification du code

```bash
# 1. Rebuild l'image
gcloud builds submit \
  --tag=gcr.io/box-magique-gp-prod/mcp-cockpit-iapf-healthcheck \
  --dockerfile=mcp_cockpit/Dockerfile.job \
  --project=box-magique-gp-prod \
  .

# 2. Redéployer le job (même commande)
gcloud run jobs deploy mcp-cockpit-iapf-healthcheck \
  --image=gcr.io/box-magique-gp-prod/mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod \
  --service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
  --max-retries=1 \
  --task-timeout=10m \
  --memory=1Gi \
  --cpu=1 \
  --set-env-vars="ENVIRONMENT=PROD,USE_METADATA_AUTH=true"

# 3. Tester
gcloud run jobs execute mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod
```

---

## 🗑️ Rollback

### Revenir à une version précédente de l'image

```bash
# Lister les versions d'images
gcloud container images list-tags gcr.io/box-magique-gp-prod/mcp-cockpit-iapf-healthcheck \
  --project=box-magique-gp-prod

# Redéployer avec un digest spécifique
gcloud run jobs deploy mcp-cockpit-iapf-healthcheck \
  --image=gcr.io/box-magique-gp-prod/mcp-cockpit-iapf-healthcheck@sha256:<DIGEST> \
  --region=us-central1 \
  --project=box-magique-gp-prod \
  --service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com
```

---

### Désactiver complètement le cockpit

```bash
# 1. Suspendre la planification
gcloud scheduler jobs pause mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1 \
  --project=box-magique-gp-prod

# 2. (Optionnel) Supprimer le job
gcloud run jobs delete mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod \
  --quiet
```

**Impact** : ❌ **0 sur le runtime OCR** (isolation stricte)

---

## 🧪 Tests de Validation

### Test 1 : Exécution réussie

```bash
# Lancer le job
gcloud run jobs execute mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod

# Vérifier status=success dans les logs
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=mcp-cockpit-iapf-healthcheck AND textPayload=~\"IAPF HEALTHCHECK COMPLETE\"" \
  --project=box-magique-gp-prod \
  --limit=1
```

**Résultat attendu** : Log contient `Status: success`

---

### Test 2 : HUB ORION mis à jour

1. Exécuter le job
2. Aller sur https://docs.google.com/spreadsheets/d/1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ/edit
3. Vérifier l'onglet `MEMORY_LOG`

**Résultat attendu** : Nouvelle ligne avec `type=healthcheck` et timestamp récent

---

### Test 3 : Artifacts générés

```bash
# Logs doivent mentionner les 3 artifacts
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=mcp-cockpit-iapf-healthcheck AND textPayload=~\"Artifacts: 3\"" \
  --project=box-magique-gp-prod \
  --limit=1
```

**Résultat attendu** : `snapshot_*.json`, `healthcheck_*.md`, `audit_log_*.json` mentionnés

---

## 📝 Procédure d'Escalade

### Niveau 1 : Auto-résolution (5-15 min)
- Consulter [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- Vérifier permissions Drive/Sheets
- Relancer le job manuellement

### Niveau 2 : DevOps (15-60 min)
- Analyser les logs détaillés
- Vérifier quotas GCP
- Tester en local (Cloud Shell)

### Niveau 3 : Dev Lead (> 60 min)
- Problème structurel code ou config
- Rollback si nécessaire
- Hotfix + redéploiement

**Contact** : romacmehdi971-lgtm

---

## 📚 Ressources

- [README](./README.md) - Vue d'ensemble
- [DEPLOYMENT](./DEPLOYMENT.md) - Guide de déploiement
- [SECURITY](./SECURITY.md) - IAM & Permissions
- [TROUBLESHOOTING](./TROUBLESHOOTING.md) - Résolution d'erreurs

---

## 🔄 Changelog Procédures

### 2026-02-13 - v1.0.0
- Création runbook initial
- Procédures one-shot et scheduler
- Monitoring et alertes
- Tests de validation
