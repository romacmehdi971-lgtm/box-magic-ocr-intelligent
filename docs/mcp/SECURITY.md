# MCP Cockpit IAPF - Security & IAM

**Version**: 1.0.0  
**Classification**: PROD - Monitoring Read-Only + Write Controlled

---

## 🔐 Principe de Sécurité

Le MCP Cockpit IAPF applique le principe du **moindre privilège** :
- **READ-ONLY** sur tous les systèmes audités (Cloud Run, GitHub, Drive, Sheets BOX2026)
- **WRITE contrôlé** uniquement sur HUB ORION (4 onglets spécifiques)
- **0 accès** au runtime OCR en production (isolation stricte)

---

## 👤 Service Account

### Identité PROD
**Email**: `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`  
**Type**: Service Account GCP  
**Project**: `box-magique-gp-prod`

### Création
```bash
gcloud iam service-accounts create mcp-cockpit \
  --display-name="MCP Cockpit IAPF" \
  --description="Service account for MCP Central Cockpit healthcheck job" \
  --project=box-magique-gp-prod
```

### Authentification
**Mode PROD** : Application Default Credentials (ADC) via metadata  
**Pas de credentials.json** : Le service account est attaché au Cloud Run Job

```python
# Code Python utilise automatiquement l'identité du job
from google.auth import default
credentials, project = default()
```

---

## 🔑 Rôles & Permissions IAM

### 1. Cloud Run (READ-ONLY)

**Objectif** : Lire le status et les logs du service `box-magic-ocr-intelligent`

**Rôles requis** :
```bash
# Lecture des services Cloud Run
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/run.viewer"

# Lecture des logs
gcloud projects add-iam-policy-binding box-magique-gp-prod \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/logging.viewer"
```

**Permissions effectives** :
- `run.services.get`
- `run.services.list`
- `logging.logEntries.list`

**Interdictions** :
- ❌ `run.services.update` - Pas de modification
- ❌ `run.services.delete` - Pas de suppression
- ❌ `run.services.setIamPolicy` - Pas de changement IAM

---

### 2. GitHub (READ-ONLY via API publique)

**Objectif** : Auditer les repos OCR et CRM

**Méthode** : API publique GitHub (pas d'auth GCP)
- Endpoint : `https://api.github.com/repos/{owner}/{repo}`
- Rate limit : 60 requêtes/heure (mode non-authentifié)

**Sécurité** :
- Pas de token GitHub stocké en dur
- Optionnel : Variable d'environnement `GITHUB_TOKEN` (secret Cloud Run) pour augmenter rate limit à 5000/h

**Interdictions** :
- ❌ Pas de `git push`
- ❌ Pas de création de PR/issues
- ❌ Pas de modification de code

---

### 3. Google Drive (READ-ONLY)

**Objectif** : Auditer l'architecture des dossiers IAPF

**Ressource ciblée** :
- Root ID : `1LwUZ67zVstl2tuogcdYYihPilUAXQai3`
- URL : https://drive.google.com/drive/folders/1LwUZ67zVstl2tuogcdYYihPilUAXQai3

**Configuration** :
1. Aller sur le dossier Drive
2. Clic droit → Partager
3. Ajouter : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
4. Permission : **Lecteur** (Viewer)

**Scope OAuth** : `https://www.googleapis.com/auth/drive.readonly`

**Permissions effectives** :
- Lister les fichiers et dossiers
- Lire les métadonnées (nom, date, taille)
- Lire le contenu (si nécessaire)

**Interdictions** :
- ❌ `drive.files.update` - Pas de modification
- ❌ `drive.files.delete` - Pas de suppression
- ❌ `drive.files.create` - Pas de création
- ❌ Pas de renommage (cf. `FORBIDDEN_ACTIONS`)

---

### 4. Google Sheets

#### BOX2026 (READ-ONLY)

**Objectif** : Auditer la cohérence des données CRM

**Ressource** :
- Spreadsheet ID : `1U_tLe3n_1_hL6HcRJ4yrbMDTNMfTKvPsTrbva1Sjc-4`
- URL : https://docs.google.com/spreadsheets/d/1U_tLe3n_1_hL6HcRJ4yrbMDTNMfTKvPsTrbva1Sjc-4/edit

**Configuration** :
1. Ouvrir le spreadsheet
2. Partager avec : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
3. Permission : **Lecteur** (Viewer)

**Permissions effectives** :
- `spreadsheets.get` - Lire métadonnées
- `spreadsheets.values.get` - Lire valeurs cellules

**Interdictions** :
- ❌ Pas de `spreadsheets.values.update`
- ❌ Pas de `spreadsheets.values.append`

---

#### HUB ORION (WRITE contrôlé)

**Objectif** : Écrire les logs, snapshots, risks, conflicts

**Ressource** :
- Spreadsheet ID : `1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ`
- URL : https://docs.google.com/spreadsheets/d/1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ/edit

**Configuration** :
1. Ouvrir le spreadsheet
2. Partager avec : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
3. Permission : **Éditeur** (Editor)

**Onglets écriture autorisée** :
- `MEMORY_LOG` - Logs d'événements (format TSV 7 colonnes)
- `SNAPSHOT_ACTIVE` - État système actuel
- `RISKS` - Risks détectés
- `CONFLITS_DETECTES` - Conflicts inter-systèmes

**Scope OAuth** : `https://www.googleapis.com/auth/spreadsheets`

**Permissions effectives** :
- `spreadsheets.values.get` - Lecture
- `spreadsheets.values.append` - Ajout de lignes (append-only)
- `spreadsheets.values.update` - Mise à jour cellules (pour SNAPSHOT_ACTIVE)

**Règles de sécurité code** :
```python
# Dans sheets_tool.py
WRITABLE_SHEETS = ["MEMORY_LOG", "SNAPSHOT_ACTIVE", "RISKS", "CONFLITS_DETECTES"]

def append_memory_log(row):
    # Vérifier format TSV 7 colonnes
    if len(row) != 7:
        raise ValueError("MEMORY_LOG requires 7 columns")
    # Append uniquement (pas de update/delete sur logs existants)
    service.spreadsheets().values().append(...).execute()
```

---

## 🚫 Interdictions Absolues

Définies dans `mcp_cockpit/config/iapf_config.py` :

```python
FORBIDDEN_ACTIONS = [
    "drive_rename",      # Pas de renommage Drive
    "drive_move",        # Pas de déplacement Drive
    "drive_delete",      # Pas de suppression Drive
    "cloudrun_deploy",   # Pas de déploiement Cloud Run
    "github_push",       # Pas de push GitHub
    "secrets_in_code",   # Pas de secrets en dur
    "log_with_pii"       # Pas de PII dans les logs
]
```

**Enforcement** :
- Pas de code implémentant ces actions dans `mcp_cockpit/`
- SafeLogger masque automatiquement les patterns PII
- Review code stricte avant merge

---

## 🔒 Protection des Secrets

### Pas de credentials.json en PROD

**Principe** : Le Cloud Run Job utilise l'identité du service account attaché

**Dockerfile** :
```dockerfile
# Pas de COPY credentials.json
ENV USE_METADATA_AUTH=true
```

**Code Python** :
```python
import os
from google.auth import default

if os.getenv("USE_METADATA_AUTH") == "true":
    credentials, project = default()  # ADC via metadata
else:
    # Mode local dev uniquement
    from google.oauth2 import service_account
    credentials = service_account.Credentials.from_service_account_file(...)
```

### Secrets optionnels (Cloud Run secrets)

Si besoin de `GITHUB_TOKEN` pour rate limit :

```bash
# Créer le secret
echo -n "ghp_xxxxxxxxxxxx" | gcloud secrets create github-token \
  --data-file=- \
  --project=box-magique-gp-prod

# Donner accès au SA
gcloud secrets add-iam-policy-binding github-token \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=box-magique-gp-prod

# Référencer dans le job
gcloud run jobs update mcp-cockpit-iapf-healthcheck \
  --update-secrets=GITHUB_TOKEN=github-token:latest \
  --region=us-central1 \
  --project=box-magique-gp-prod
```

---

## 🛡️ SafeLogger - Masquage PII

Le cockpit utilise `mcp_cockpit/utils/safe_logger.py` pour masquer automatiquement :

**Patterns masqués** :
- Emails : `***@***.***`
- Tokens : `ghp_***`, `Bearer ***`
- URLs avec query params : `?***`
- UUIDs : `****-****-****`
- Montants : `***EUR`, `***€`

**Exemple** :
```python
from mcp_cockpit.utils.safe_logger import SafeLogger

logger = SafeLogger(__name__)
logger.info("Processing john.doe@example.com")  
# Log: "Processing ***@***.***"
```

---

## 📊 Audit IAM

Pour vérifier les permissions effectives :

```bash
# Lister les rôles du SA
gcloud projects get-iam-policy box-magique-gp-prod \
  --flatten="bindings[].members" \
  --filter="bindings.members:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com"

# Tester l'accès à une ressource
gcloud run services describe box-magic-ocr-intelligent \
  --region=us-central1 \
  --project=box-magique-gp-prod \
  --impersonate-service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com
```

---

## 🔄 Rotation des Secrets (Best Practice)

Même si le cockpit n'utilise pas de credentials.json en PROD, si vous ajoutez des secrets :

```bash
# Créer une nouvelle version du secret
echo -n "new_value" | gcloud secrets versions add github-token \
  --data-file=- \
  --project=box-magique-gp-prod

# Le job utilisera automatiquement :latest
```

---

## 🚨 Réponse aux Incidents

### Scénario : Service Account compromis

1. **Désactiver le SA** :
```bash
gcloud iam service-accounts disable mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
  --project=box-magique-gp-prod
```

2. **Supprimer les clés** (si existantes) :
```bash
gcloud iam service-accounts keys list \
  --iam-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
  --project=box-magique-gp-prod

gcloud iam service-accounts keys delete <KEY_ID> \
  --iam-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
  --project=box-magique-gp-prod
```

3. **Auditer les logs d'accès** :
```bash
gcloud logging read \
  "protoPayload.authenticationInfo.principalEmail=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --limit=100 \
  --project=box-magique-gp-prod
```

4. **Créer un nouveau SA** et redéployer

---

## 📝 Checklist Sécurité

- [ ] Service Account créé avec nom descriptif
- [ ] Rôles minimum requis attribués (run.viewer, logging.viewer)
- [ ] Partages Drive/Sheets configurés (Viewer pour read, Editor pour HUB uniquement)
- [ ] Pas de credentials.json dans le repo (gitignore)
- [ ] `USE_METADATA_AUTH=true` dans le job
- [ ] SafeLogger activé pour masquer PII
- [ ] `FORBIDDEN_ACTIONS` respectées dans le code
- [ ] Secrets optionnels stockés dans Secret Manager (pas en env vars)
- [ ] Audit IAM validé
- [ ] Procédure de rotation des secrets documentée

---

## 🆘 Support

**Questions sécurité** : romacmehdi971-lgtm  
**GCP Security** : https://cloud.google.com/security/best-practices
