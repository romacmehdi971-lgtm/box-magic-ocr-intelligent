# MCP Cockpit IAPF - Deployment Guide

**Version**: 1.0.0  
**Target**: Cloud Run Job PROD  
**Mode**: One-shot + Schedulable

---

## 📋 Prerequisites

### 1. GCP Project Setup
- **Project ID**: `box-magique-gp-prod`
- **Region**: `us-central1`
- **Billing**: Activé

### 2. APIs Required
Les APIs suivantes doivent être activées (le script de déploiement les active automatiquement) :
- `cloudbuild.googleapis.com` - Build Docker
- `run.googleapis.com` - Cloud Run Jobs
- `containerregistry.googleapis.com` - Container Registry
- `cloudscheduler.googleapis.com` - Scheduler (optionnel)

### 3. Service Account
**Email**: `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`

**Création (si n'existe pas)** :
```bash
gcloud iam service-accounts create mcp-cockpit \
  --display-name="MCP Cockpit IAPF" \
  --project=box-magique-gp-prod
```

**Rôles requis** :
```bash
# Cloud Run - lecture status/logs
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/run.viewer"

gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/logging.viewer"

# Drive & Sheets - accès via partage explicite (voir section Permissions ci-dessous)
```

### 4. Permissions Drive & Sheets

**Drive IAPF Root** :
- Aller sur https://drive.google.com/drive/folders/1LwUZ67zVstl2tuogcdYYihPilUAXQai3
- Clic droit → Partager
- Ajouter `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
- Permission : **Lecteur** (Viewer)

**Sheets BOX2026** :
- Aller sur https://docs.google.com/spreadsheets/d/1U_tLe3n_1_hL6HcRJ4yrbMDTNMfTKvPsTrbva1Sjc-4/edit
- Partager avec `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
- Permission : **Lecteur** (Viewer)

**Sheets HUB ORION** :
- Aller sur https://docs.google.com/spreadsheets/d/1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ/edit
- Partager avec `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
- Permission : **Éditeur** (Editor) - écriture sur MEMORY_LOG, SNAPSHOT_ACTIVE, RISKS, CONFLITS_DETECTES

---

## 🚀 Déploiement One-Shot

### Méthode 1 : Script automatique (recommandé)

```bash
# Depuis la racine du repo
./deploy_mcp_cockpit_job.sh
```

Ce script :
1. ✅ Configure le projet GCP actif
2. ✅ Active les APIs nécessaires
3. ✅ Vérifie l'existence du service account
4. ✅ Build l'image Docker avec Cloud Build
5. ✅ Déploie le Cloud Run Job
6. ✅ Affiche les commandes d'exécution

**Durée estimée** : 5-10 minutes

---

### Méthode 2 : Commandes manuelles

Si vous préférez exécuter les étapes manuellement :

#### Étape 1 : Activer les APIs
```bash
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  containerregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  --project=box-magique-gp-prod
```

#### Étape 2 : Build de l'image Docker
```bash
gcloud builds submit \
  --tag=gcr.io/box-magique-gp-prod/mcp-cockpit-iapf-healthcheck \
  --dockerfile=mcp_cockpit/Dockerfile.job \
  --project=box-magique-gp-prod \
  --timeout=10m \
  .
```

#### Étape 3 : Déployer le Cloud Run Job
```bash
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
```

---

## 🧪 Vérification du Déploiement

### Test 1 : Exécution manuelle
```bash
gcloud run jobs execute mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod
```

**Résultat attendu** :
```
✓ Creating execution... Done.
  ✓ Provisioning resources...
  ✓ Running...
Done.
Execution [mcp-cockpit-iapf-healthcheck-xxxxx] completed successfully.
```

### Test 2 : Consulter les logs
```bash
# Récupérer le nom de la dernière exécution
EXECUTION=$(gcloud run jobs executions list \
  --job=mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --limit=1 \
  --format='value(name)')

# Voir les logs
gcloud run jobs executions describe $EXECUTION \
  --region=us-central1 \
  --format=yaml
```

**Contenu attendu dans les logs** :
- `✅ IAPF HEALTHCHECK COMPLETE`
- `Status: success`
- `Risks: <nombre>`
- `Conflicts: <nombre>`
- `Artifacts: 3`

### Test 3 : Vérifier HUB ORION
Aller sur https://docs.google.com/spreadsheets/d/1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ/edit

**Vérification onglet MEMORY_LOG** :
- Une nouvelle ligne doit apparaître avec `type=healthcheck`
- Format TSV 7 colonnes respecté
- Timestamp ISO UTC correct

---

## 📅 Planification Automatique (Optionnel)

Pour exécuter le healthcheck quotidiennement à 6h UTC :

```bash
gcloud scheduler jobs create http mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1 \
  --schedule='0 6 * * *' \
  --uri='https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/box-magique-gp-prod/jobs/mcp-cockpit-iapf-healthcheck:run' \
  --http-method=POST \
  --oauth-service-account-email=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
  --description='MCP Cockpit IAPF - Daily Healthcheck'
```

**Autres fréquences** :
- Toutes les heures : `0 * * * *`
- Toutes les 6h : `0 */6 * * *`
- Lundi-Vendredi 9h : `0 9 * * 1-5`

**Tester la planification** :
```bash
gcloud scheduler jobs run mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1
```

---

## 🔄 Mise à Jour du Job

### Rebuild après changements code
```bash
# 1. Rebuild l'image
gcloud builds submit \
  --tag=gcr.io/box-magique-gp-prod/mcp-cockpit-iapf-healthcheck \
  --dockerfile=mcp_cockpit/Dockerfile.job \
  --project=box-magique-gp-prod \
  .

# 2. Mettre à jour le job (même commande que deploy)
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
```

---

## 🗑️ Rollback / Suppression

### Supprimer la planification uniquement
```bash
gcloud scheduler jobs delete mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1 \
  --quiet
```

### Supprimer le job (rollback complet)
```bash
gcloud run jobs delete mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod \
  --quiet
```

**Impact** : ❌ **0 sur le runtime OCR** (isolation stricte cockpit-only)

---

## 📊 Monitoring Production

### Dashboard GCP Console
https://console.cloud.google.com/run/jobs/details/us-central1/mcp-cockpit-iapf-healthcheck?project=box-magique-gp-prod

**Métriques disponibles** :
- Nombre d'exécutions
- Taux de succès/échec
- Durée moyenne d'exécution
- Erreurs récentes

### Alertes recommandées
```bash
# Alerte si le job échoue 3 fois consécutivement
gcloud alpha monitoring policies create \
  --notification-channels=<CHANNEL_ID> \
  --display-name="MCP Cockpit Job Failures" \
  --condition-display-name="Job Failed" \
  --condition-threshold-value=3 \
  --condition-threshold-duration=1800s
```

---

## 🔐 Variables d'Environnement

Le job Cloud Run utilise ces variables :

| Variable | Valeur PROD | Description |
|----------|-------------|-------------|
| `ENVIRONMENT` | `PROD` | Mode d'exécution |
| `USE_METADATA_AUTH` | `true` | Authentification via metadata (ADC) |
| `PROJECT_ID` | `box-magique-gp-prod` | Inféré automatiquement |
| `REGION` | `us-central1` | Inféré automatiquement |

**Pas de secrets en variables d'environnement** : l'authentification se fait via le service account attaché au job.

---

## 📝 Checklist Déploiement

- [ ] Service account `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com` créé
- [ ] Rôles IAM attribués (run.viewer, logging.viewer)
- [ ] Drive IAPF root partagé avec le SA (Viewer)
- [ ] Sheets BOX2026 partagé avec le SA (Viewer)
- [ ] Sheets HUB ORION partagé avec le SA (Editor)
- [ ] Script `deploy_mcp_cockpit_job.sh` exécuté avec succès
- [ ] Test d'exécution manuelle passé
- [ ] Logs confirment `IAPF HEALTHCHECK COMPLETE`
- [ ] HUB ORION MEMORY_LOG mis à jour avec nouvelle ligne
- [ ] Planification créée (si désiré)
- [ ] Dashboard GCP vérifié

---

## 🆘 En cas de problème

Voir [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) pour les erreurs fréquentes.

**Support** : romacmehdi971-lgtm
