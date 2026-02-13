# MCP Cockpit IAPF - Troubleshooting

**Version**: 1.0.0  
**Last Updated**: 2026-02-13

---

## 🔍 Diagnostic Rapide

### Le job échoue immédiatement

**Symptôme** : Exécution se termine en quelques secondes avec erreur

**Causes fréquentes** :
1. Service account manquant ou mal configuré
2. Image Docker introuvable
3. Variables d'environnement incorrectes

**Solution** :
```bash
# Vérifier le job
gcloud run jobs describe mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod \
  --format=yaml

# Vérifier le service account
gcloud iam service-accounts describe mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
  --project=box-magique-gp-prod
```

---

## ❌ Erreurs Fréquentes

### 1. Permission Denied (Drive)

**Erreur** :
```
403 Forbidden: The caller does not have permission to access folder 1LwUZ67zVstl2tuogcdYYihPilUAXQai3
```

**Cause** : Le dossier Drive n'est pas partagé avec le service account

**Solution** :
1. Aller sur https://drive.google.com/drive/folders/1LwUZ67zVstl2tuogcdYYihPilUAXQai3
2. Clic droit → Partager
3. Ajouter `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
4. Permission : **Lecteur**
5. Envoyer

**Validation** :
```bash
# Tester avec impersonation
gcloud auth application-default login --impersonate-service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com
```

---

### 2. Permission Denied (Sheets)

**Erreur** :
```
403 Forbidden: The caller does not have permission to access spreadsheet 1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ
```

**Cause** : Le spreadsheet n'est pas partagé avec le service account

**Solution pour BOX2026 (READ)** :
1. Ouvrir https://docs.google.com/spreadsheets/d/1U_tLe3n_1_hL6HcRJ4yrbMDTNMfTKvPsTrbva1Sjc-4/edit
2. Partager avec `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
3. Permission : **Lecteur**

**Solution pour HUB ORION (WRITE)** :
1. Ouvrir https://docs.google.com/spreadsheets/d/1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ/edit
2. Partager avec `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
3. Permission : **Éditeur**

**Validation** :
```bash
# Tester l'accès via gcloud (nécessite gsheets installé)
gcloud auth application-default login --impersonate-service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com
```

---

### 3. Cloud Run Service Not Found

**Erreur** :
```
404 Not Found: Service box-magic-ocr-intelligent not found in region us-central1
```

**Cause** : Le service OCR n'existe pas ou est dans une autre région

**Solution** :
```bash
# Lister tous les services Cloud Run
gcloud run services list \
  --project=box-magique-gp-prod \
  --format="table(name,region,status)"

# Mettre à jour la config si nécessaire
# Éditer mcp_cockpit/config/iapf_config.py
```

---

### 4. GitHub Rate Limit

**Erreur** :
```
403 Forbidden: API rate limit exceeded for <IP>
```

**Cause** : Limite de 60 requêtes/heure dépassée (mode non-authentifié)

**Solution temporaire** :
```python
# Le code gère automatiquement avec fallback
# Log: "risk: github_rate_limit"
```

**Solution permanente** :
```bash
# Créer un GitHub Personal Access Token (PAT) avec scope public_repo
# https://github.com/settings/tokens

# Ajouter comme secret Cloud Run
echo -n "ghp_xxxxxxxxxxxx" | gcloud secrets create github-token \
  --data-file=- \
  --project=box-magique-gp-prod

gcloud secrets add-iam-policy-binding github-token \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=box-magique-gp-prod

# Mettre à jour le job
gcloud run jobs update mcp-cockpit-iapf-healthcheck \
  --update-secrets=GITHUB_TOKEN=github-token:latest \
  --region=us-central1 \
  --project=box-magique-gp-prod
```

---

### 5. Timeout Job

**Erreur** :
```
Job execution exceeded timeout of 10m
```

**Cause** : Audits trop lents (API externe, Drive avec beaucoup de fichiers)

**Solution** :
```bash
# Augmenter le timeout
gcloud run jobs update mcp-cockpit-iapf-healthcheck \
  --task-timeout=20m \
  --region=us-central1 \
  --project=box-magique-gp-prod
```

**Optimisation code** :
- Limiter la profondeur de scan Drive
- Paralléliser les audits
- Utiliser des caches pour GitHub

---

### 6. Memory Exceeded

**Erreur** :
```
Memory limit of 1Gi exceeded
```

**Cause** : Trop de données en mémoire (gros snapshots)

**Solution** :
```bash
# Augmenter la mémoire
gcloud run jobs update mcp-cockpit-iapf-healthcheck \
  --memory=2Gi \
  --region=us-central1 \
  --project=box-magique-gp-prod
```

---

### 7. MEMORY_LOG Format Error

**Erreur** :
```
ValueError: MEMORY_LOG requires 7 columns, got 6
```

**Cause** : Ligne TSV mal formatée (TAB manquant ou en trop)

**Solution** :
```python
# Vérifier le format dans sheets_tool.py
row = [
    ts_iso,      # Colonne 1
    type,        # Colonne 2
    title,       # Colonne 3
    details,     # Colonne 4 (JSON échappé)
    author,      # Colonne 5
    source,      # Colonne 6
    tags         # Colonne 7
]
# Séparateur : "\t"
```

**Validation manuelle** :
```bash
# Compter les TABs dans une ligne
echo "2026-02-13T06:00:00Z	healthcheck	Test	{}	mcp	job	tag1;tag2" | awk -F'\t' '{print NF}'
# Output attendu: 7
```

---

### 8. No Logs Visible

**Erreur** : Exécution réussie mais aucun log visible dans Cloud Console

**Cause** : Rôle `logging.viewer` manquant pour le service account

**Solution** :
```bash
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/logging.viewer"
```

---

### 9. Scheduler ne déclenche pas le job

**Erreur** : Planification créée mais le job ne s'exécute jamais

**Vérification** :
```bash
# Statut de la planification
gcloud scheduler jobs describe mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1 \
  --project=box-magique-gp-prod

# Vérifier state: ENABLED
```

**Causes fréquentes** :
1. Planification suspendue (`state: PAUSED`)
2. URI Cloud Run Job incorrecte
3. Service account scheduler n'a pas le droit d'invoquer le job

**Solution** :
```bash
# Donner le droit au SA d'invoquer le job
gcloud run jobs add-iam-policy-binding mcp-cockpit-iapf-healthcheck \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --region=us-central1 \
  --project=box-magique-gp-prod

# Tester manuellement
gcloud scheduler jobs run mcp-cockpit-iapf-healthcheck-daily \
  --location=us-central1 \
  --project=box-magique-gp-prod
```

---

### 10. Image Build Fails

**Erreur** :
```
Error: failed to build: error building image: error building stage...
```

**Cause** : Dockerfile incorrect ou fichiers manquants

**Vérification locale** :
```bash
# Tester le build localement
docker build -f mcp_cockpit/Dockerfile.job -t test-cockpit .

# Lister les fichiers copiés
docker run --rm test-cockpit ls -la /app/mcp_cockpit
```

**Solution** :
```bash
# Vérifier que tous les fichiers existent
ls -la mcp_cockpit/
ls -la healthcheck_iapf.py
ls -la requirements.txt
```

---

## 🧪 Tests de Diagnostic

### Test 1 : Authentification Service Account

```bash
# Tester l'impersonation
gcloud auth application-default login \
  --impersonate-service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com

# Lister les permissions effectives
gcloud projects get-iam-policy box-magique-gp-prod \
  --flatten="bindings[].members" \
  --filter="bindings.members:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com"
```

---

### Test 2 : Accès Drive

```bash
# Lister les fichiers (nécessite gdrive CLI ou script Python)
python3 << 'EOF'
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Note: En PROD, credentials viennent de metadata
# Ici on teste avec impersonation

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
creds, _ = google.auth.default(scopes=SCOPES)

service = build('drive', 'v3', credentials=creds)
results = service.files().list(
    q="'1LwUZ67zVstl2tuogcdYYihPilUAXQai3' in parents",
    pageSize=10,
    fields="files(id, name)"
).execute()

print(results.get('files', []))
EOF
```

---

### Test 3 : Accès Sheets

```bash
python3 << 'EOF'
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds, _ = google.auth.default(scopes=SCOPES)

service = build('sheets', 'v4', credentials=creds)
sheet = service.spreadsheets()

# Test lecture BOX2026
result = sheet.values().get(
    spreadsheetId='1U_tLe3n_1_hL6HcRJ4yrbMDTNMfTKvPsTrbva1Sjc-4',
    range='CONFIG!A1:B10'
).execute()

print(f"Rows: {len(result.get('values', []))}")
EOF
```

---

## 📊 Monitoring Santé

### Indicateurs clés à surveiller

```bash
# Taux de succès (dernières 24h)
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=mcp-cockpit-iapf-healthcheck AND timestamp>=\"$(date -u -d '24 hours ago' '+%Y-%m-%dT%H:%M:%SZ')\"" \
  --project=box-magique-gp-prod \
  --format="value(jsonPayload.status)" | \
  awk '{success += ($1 == "success"); total++} END {print (success/total*100) "%"}'

# Durée moyenne d'exécution
gcloud logging read \
  "resource.type=cloud_run_job AND resource.labels.job_name=mcp-cockpit-iapf-healthcheck AND textPayload=~\"HEALTHCHECK COMPLETE\"" \
  --project=box-magique-gp-prod \
  --limit=10 \
  --format=json | jq -r '.[].timestamp' | head -2 | xargs -I {} date -d {} +%s | awk '{sum+=$1; n++} END {print (sum/n) "s"}'
```

---

## 🔄 Procédure de Recovery

### Si le job est complètement bloqué

1. **Arrêter les exécutions en cours** :
```bash
# Lister les exécutions actives
gcloud run jobs executions list \
  --job=mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod \
  --filter="status.conditions.status=Unknown"

# Supprimer une exécution bloquée (non supporté, attendre timeout)
# Cloud Run Jobs n'a pas de commande "cancel"
```

2. **Redéployer le job** :
```bash
./deploy_mcp_cockpit_job.sh
```

3. **Tester** :
```bash
gcloud run jobs execute mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --project=box-magique-gp-prod
```

---

## 🆘 Escalade

### Niveau 1 : Auto-diagnostic (0-15 min)
- Consulter ce document
- Vérifier permissions (Drive, Sheets, Cloud Run)
- Relancer le job manuellement

### Niveau 2 : Logs Analysis (15-60 min)
- Extraire les logs détaillés
- Identifier l'erreur précise
- Appliquer la solution correspondante

### Niveau 3 : Code Fix (> 60 min)
- Problème structurel nécessitant un hotfix
- Rollback vers version stable
- Ouvrir un ticket GitHub

**Contact** : romacmehdi971-lgtm

---

## 📝 Checklist Troubleshooting

Avant d'escalader, vérifier :

- [ ] Service account existe et est activé
- [ ] Drive root partagé avec SA (Viewer)
- [ ] Sheets BOX2026 partagé avec SA (Viewer)
- [ ] Sheets HUB ORION partagé avec SA (Editor)
- [ ] Rôles IAM attribués (run.viewer, logging.viewer)
- [ ] APIs activées (run, logging, drive, sheets)
- [ ] Image Docker buildée sans erreur
- [ ] Job déployé correctement
- [ ] Exécution manuelle testée
- [ ] Logs accessibles et consultés
- [ ] Quotas GCP non dépassés

---

## 📚 Ressources

- [README](./README.md) - Vue d'ensemble
- [DEPLOYMENT](./DEPLOYMENT.md) - Guide de déploiement
- [SECURITY](./SECURITY.md) - IAM & Permissions
- [RUNBOOK](./RUNBOOK.md) - Procédures opérationnelles
- [GCP Cloud Run Jobs Docs](https://cloud.google.com/run/docs/create-jobs)
