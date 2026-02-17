# 📋 VALIDATION FINALE ORION - GUIDE ADMIN GCP

**Date:** 2026-02-17 23:35 UTC  
**Status:** ⏳ **En attente actions admin GCP**

---

## 🎯 OBJECTIFS

1. **Récupérer logs production** du job MCP pour validation GO/NO-GO
2. **Migrer MCP_PROXY_API_KEY** vers Secret Manager
3. **Redéployer job** sans env var directe

---

## ⚠️ BLOCAGES ACTUELS

| Action | Status | Raison |
|--------|--------|--------|
| Récupération logs | ❌ | Service account n'a pas `logging.logEntries.list` |
| Création secret | ❌ | Service account n'a pas `secretmanager.secrets.create` |
| IAM binding secret | ❌ | Service account n'a pas `secretmanager.secrets.setIamPolicy` |

**Service Account problématique:**
```
genspark-deploy-temp@box-magique-gp-prod.iam.gserviceaccount.com
```

---

## 📊 PARTIE 1 - RÉCUPÉRATION LOGS PRODUCTION

### Objectif

Prouver que le job MCP v1.1.0 utilise **ProxyTool** pour appeler le REST proxy `/sheets/*`.

### Critères GO/NO-GO

✅ **Logs REQUIS:**
```
[ProxyTool] Initialized with proxy URL https://mcp-memory-proxy-522732657254.us-central1.run.app
[ProxyTool] API Key loaded: YES
[ProxyTool] GET /sheets/SETTINGS?limit=10
[ProxyTool] Response: HTTP 200, body={"http_status":200,"row_count":8,...}
[ProxyTool] GET /sheets/NOPE?limit=1
[ProxyTool] Response: HTTP 404, correlation_id=...
```

### Méthode 1: Console Web GCP (Recommandé)

**Étape 1:** Accéder à Cloud Logging
```
URL: https://console.cloud.google.com/logs/query?project=box-magique-gp-prod
```

**Étape 2:** Configurer le filtre
```
resource.type="cloud_run_job"
resource.labels.job_name="mcp-cockpit-iapf-healthcheck"
resource.labels.location="us-central1"
timestamp>="2026-02-17T22:19:00Z"
timestamp<="2026-02-17T22:22:00Z"
jsonPayload.message=~"ProxyTool"
```

**Étape 3:** Exporter les logs

1. Cliquer sur **Actions** → **Download logs**
2. Format: **JSON**
3. Sauvegarder: `mcp_job_89sx5_logs.json`

**Étape 4:** Filtrer les logs ProxyTool

```bash
cat mcp_job_89sx5_logs.json | \
  jq -r '.[] | select(.jsonPayload.message | contains("ProxyTool")) | 
    {timestamp: .timestamp, severity: .severity, message: .jsonPayload.message}'
```

### Méthode 2: gcloud CLI (Avec compte admin)

```bash
# Authentification admin
gcloud auth login

# Récupération logs complète
gcloud logging read \
  "resource.type=\"cloud_run_job\" AND \
   resource.labels.job_name=\"mcp-cockpit-iapf-healthcheck\" AND \
   resource.labels.location=\"us-central1\" AND \
   timestamp>=\"2026-02-17T22:19:00Z\" AND \
   timestamp<=\"2026-02-17T22:22:00Z\"" \
  --limit=200 \
  --format=json \
  --project=box-magique-gp-prod \
  > mcp_job_89sx5_full_logs.json

# Filtrer ProxyTool
cat mcp_job_89sx5_full_logs.json | \
  jq -r '.[] | select(.jsonPayload.message | contains("ProxyTool")) | 
    {timestamp, severity, message: .jsonPayload.message}'

# Filtrer GET /sheets/SETTINGS
cat mcp_job_89sx5_full_logs.json | \
  jq -r '.[] | select(.jsonPayload.message | contains("/sheets/SETTINGS")) | 
    {timestamp, message: .jsonPayload.message}'

# Filtrer HTTP 200
cat mcp_job_89sx5_full_logs.json | \
  jq -r '.[] | select(.jsonPayload.message | contains("HTTP 200")) | 
    {timestamp, message: .jsonPayload.message}'

# Filtrer HTTP 404
cat mcp_job_89sx5_full_logs.json | \
  jq -r '.[] | select(.jsonPayload.message | contains("HTTP 404")) | 
    {timestamp, message: .jsonPayload.message}'
```

### Informations Contextuelles

```yaml
Job: mcp-cockpit-iapf-healthcheck
Execution: mcp-cockpit-iapf-healthcheck-89sx5
Region: us-central1
Image: gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0
Digest: sha256:3f94debfdc606e6c3f0bceec9078578c4187e8f64ccb5258533a7582583724c8

Timeline:
  Start: 2026-02-17T22:19:03Z
  End: 2026-02-17T22:20:42Z (1m38.7s)
  Status: COMPLETED ✅

Environment:
  MCP_PROXY_API_KEY: kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE (43 chars)
  ENVIRONMENT: PROD
  USE_METADATA_AUTH: true
```

### Checklist Validation GO

- [ ] **Log `[ProxyTool] Initialized`** présent
- [ ] **Log `API Key loaded: YES`** présent (clé masquée)
- [ ] **Log `GET /sheets/SETTINGS?limit=10`** présent
- [ ] **Log `Response: HTTP 200`** présent
- [ ] **row_count = 8** dans la réponse
- [ ] **Log `GET /sheets/NOPE?limit=1`** présent
- [ ] **Log `Response: HTTP 404`** présent
- [ ] **correlation_id** présent dans réponse 404
- [ ] **Aucune erreur** `ConnectionError`, `401`, `403`

Si **tous les critères ✅** → **GO pour validation ORION**

---

## 🔐 PARTIE 2 - MIGRATION SECRET MANAGER

### Objectif

Migrer `MCP_PROXY_API_KEY` depuis env var directe vers Secret Manager.

### Étape 1: Créer le Secret

**Console Web:**

1. Accéder à Secret Manager:
   ```
   https://console.cloud.google.com/security/secret-manager?project=box-magique-gp-prod
   ```

2. Cliquer **CREATE SECRET**

3. Configuration:
   ```yaml
   Name: mcp-proxy-api-key
   Secret value: kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE
   Replication: Automatic
   ```

4. Cliquer **CREATE**

**OU via gcloud:**

```bash
# Authentification admin
gcloud auth login

# Créer secret
echo -n "kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE" | \
  gcloud secrets create mcp-proxy-api-key \
    --data-file=- \
    --replication-policy=automatic \
    --project=box-magique-gp-prod

# Vérifier création
gcloud secrets describe mcp-proxy-api-key \
  --project=box-magique-gp-prod
```

### Étape 2: Donner accès au Service Account MCP

```bash
# Service account du job MCP
SA_MCP="mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com"

# Ajouter permission Secret Accessor
gcloud secrets add-iam-policy-binding mcp-proxy-api-key \
  --member="serviceAccount:$SA_MCP" \
  --role="roles/secretmanager.secretAccessor" \
  --project=box-magique-gp-prod

# Vérifier permissions
gcloud secrets get-iam-policy mcp-proxy-api-key \
  --project=box-magique-gp-prod
```

### Étape 3: Redéployer le Job avec Secret

```bash
# Déployer job avec référence au secret
gcloud run jobs deploy mcp-cockpit-iapf-healthcheck \
  --image=gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0 \
  --region=us-central1 \
  --service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
  --update-secrets="MCP_PROXY_API_KEY=mcp-proxy-api-key:latest" \
  --set-env-vars="ENVIRONMENT=PROD,USE_METADATA_AUTH=true" \
  --max-retries=0 \
  --task-timeout=600s \
  --memory=512Mi \
  --cpu=1

# Vérifier configuration
gcloud run jobs describe mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --format=json | \
  jq '.spec.template.spec.template.spec.containers[0].env'
```

**Output attendu:**
```json
[
  {
    "name": "MCP_PROXY_API_KEY",
    "valueFrom": {
      "secretKeyRef": {
        "key": "latest",
        "name": "mcp-proxy-api-key"
      }
    }
  },
  {
    "name": "ENVIRONMENT",
    "value": "PROD"
  },
  {
    "name": "USE_METADATA_AUTH",
    "value": "true"
  }
]
```

### Étape 4: Tester le Job avec Secret

```bash
# Exécuter le job
gcloud run jobs execute mcp-cockpit-iapf-healthcheck \
  --region=us-central1

# Récupérer l'ID d'exécution
EXECUTION=$(gcloud run jobs executions list \
  --job=mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --limit=1 \
  --format='value(metadata.name)')

echo "Execution ID: $EXECUTION"

# Attendre la complétion (max 3 min)
for i in {1..36}; do
  STATUS=$(gcloud run jobs executions describe $EXECUTION \
    --region=us-central1 \
    --format='value(status.conditions[0].type)')
  
  echo "[$(date +%H:%M:%S)] Status: $STATUS"
  
  if [[ "$STATUS" == "Completed" ]]; then
    echo "✅ Job completed successfully"
    break
  fi
  
  sleep 5
done

# Vérifier les logs de cette nouvelle exécution
gcloud logging read \
  "resource.type=\"cloud_run_job\" AND \
   resource.labels.job_name=\"mcp-cockpit-iapf-healthcheck\" AND \
   timestamp>=\"$(date -u -d '5 minutes ago' +%Y-%m-%dT%H:%M:%SZ)\" AND \
   jsonPayload.message=~\"ProxyTool\"" \
  --limit=50 \
  --format=json \
  --project=box-magique-gp-prod | \
  jq -r '.[] | {timestamp, message: .jsonPayload.message}'
```

---

## 📋 CHECKLIST FINALE

### Validation Logs (PARTIE 1)

- [ ] Logs récupérés depuis Cloud Logging
- [ ] Log `[ProxyTool] Initialized` confirmé
- [ ] Log `GET /sheets/SETTINGS?limit=10` → `HTTP 200` confirmé
- [ ] Log `GET /sheets/NOPE?limit=1` → `HTTP 404 + correlation_id` confirmé
- [ ] Aucune erreur runtime détectée
- [ ] **DÉCISION:** ✅ GO ou ❌ NO-GO

### Migration Secret Manager (PARTIE 2)

- [ ] Secret `mcp-proxy-api-key` créé dans Secret Manager
- [ ] Service account `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com` a accès au secret
- [ ] Job redéployé avec `--update-secrets="MCP_PROXY_API_KEY=mcp-proxy-api-key:latest"`
- [ ] Env var directe `MCP_PROXY_API_KEY` supprimée (remplacée par secret)
- [ ] Job testé avec nouvelle configuration
- [ ] Logs du nouveau job confirment fonctionnement avec secret
- [ ] **DÉCISION:** ✅ Migration complète

---

## 🚨 ERREURS POSSIBLES & SOLUTIONS

### Erreur 1: "Permission 'secretmanager.secrets.accessSecretVersion' denied"

**Cause:** Service account MCP n'a pas accès au secret.

**Solution:**
```bash
gcloud secrets add-iam-policy-binding mcp-proxy-api-key \
  --member="serviceAccount:mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor" \
  --project=box-magique-gp-prod
```

### Erreur 2: Job fail avec "MCP_PROXY_API_KEY env var required"

**Cause:** Secret non monté correctement.

**Solution:** Vérifier la configuration:
```bash
gcloud run jobs describe mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --format='value(spec.template.spec.template.spec.containers[0].env)'
```

Doit contenir:
```
name: MCP_PROXY_API_KEY
valueFrom:
  secretKeyRef:
    key: latest
    name: mcp-proxy-api-key
```

### Erreur 3: "Secret 'mcp-proxy-api-key' not found"

**Cause:** Secret non créé ou mauvais nom.

**Solution:** Vérifier l'existence:
```bash
gcloud secrets list --project=box-magique-gp-prod | grep mcp-proxy-api-key
```

---

## 📊 INFORMATIONS COMPLÉMENTAIRES

### Service Accounts Impliqués

```yaml
Deploy SA (permissions insuffisantes):
  Email: genspark-deploy-temp@box-magique-gp-prod.iam.gserviceaccount.com
  Rôles manquants:
    - roles/logging.viewer (pour logs)
    - roles/secretmanager.admin (pour secrets)

MCP Job SA (à configurer):
  Email: mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com
  Rôle requis:
    - roles/secretmanager.secretAccessor (sur mcp-proxy-api-key)
```

### Configuration Actuelle du Job

```yaml
Image: gcr.io/box-magique-gp-prod/mcp-cockpit:v1.1.0
Digest: sha256:3f94debfdc606e6c3f0bceec9078578c4187e8f64ccb5258533a7582583724c8

Env Vars (ACTUEL - à remplacer):
  - name: MCP_PROXY_API_KEY
    value: "kTxWKxMrrrEXtM132Vd1Qqc4Zf6QsmQKLOo_W1PuDWE"  # ❌ Hardcodé
  - name: ENVIRONMENT
    value: "PROD"
  - name: USE_METADATA_AUTH
    value: "true"

Secrets (CIBLE):
  - name: MCP_PROXY_API_KEY
    valueFrom:
      secretKeyRef:
        key: latest
        name: mcp-proxy-api-key  # ✅ Depuis Secret Manager
```

### Commandes de Vérification

```bash
# Vérifier secret existe
gcloud secrets describe mcp-proxy-api-key --project=box-magique-gp-prod

# Vérifier permissions
gcloud secrets get-iam-policy mcp-proxy-api-key --project=box-magique-gp-prod

# Vérifier job config
gcloud run jobs describe mcp-cockpit-iapf-healthcheck \
  --region=us-central1 \
  --format=json | jq '.spec.template.spec.template.spec.containers[0].env'

# Test d'accès au secret (avec SA MCP)
gcloud secrets versions access latest \
  --secret=mcp-proxy-api-key \
  --impersonate-service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com
```

---

## 📞 SUPPORT

**Repository:** https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent

**Commits:**
- `9e97b25` - Validation blocked report
- `6b4f7e8` - Deploy v1.1.0 production
- `bf414ac` - ProxyTool integration

**Documentation:**
- [VALIDATION_BLOCKED_REPORT.md](./VALIDATION_BLOCKED_REPORT.md)
- [LOGS_PRODUCTION_MANUAL_STEPS.md](./LOGS_PRODUCTION_MANUAL_STEPS.md)
- [MCP_PROXY_DEPLOYMENT_FINAL.md](./MCP_PROXY_DEPLOYMENT_FINAL.md)

---

**Date:** 2026-02-17 23:35 UTC  
**Status:** ⏳ **En attente actions admin GCP**  
**Actions requises:** Logs production + Migration Secret Manager
