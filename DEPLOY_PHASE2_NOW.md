# 🚨 DÉPLOIEMENT PHASE 2 CLOUD RUN — GUIDE RAPIDE
**Date**: 2026-02-20  
**Commit**: a548b88  
**Blocage résolu**: Endpoints Phase 2 intégrés dans main.py

---

## ✅ CHANGEMENTS APPLIQUÉS

### 1. Backend Proxy (main.py modifié)
```python
# Ligne 55: Import Phase 2
from . import phase2_endpoints

# Lignes 130-132: Include router Phase 2
app.include_router(phase2_endpoints.router, tags=["Phase 2 MCP Extensions"])
```

### 2. Script Déploiement (deploy-phase2.sh créé)
- Build image Docker avec tag `phase2-{commit}`
- Push vers `gcr.io/box-magique-gp-prod/mcp-memory-proxy`
- Deploy Cloud Run avec env vars Phase 2
- Vérification /health + /openapi.json

---

## 🚀 DÉPLOIEMENT IMMÉDIAT

### Option A: Script Automatique (Recommandé)

```bash
cd /home/user/webapp/memory-proxy
./deploy-phase2.sh
```

**Durée**: ~5-8 minutes
- Build image: ~2 min
- Push GCR: ~1 min
- Deploy Cloud Run: ~2 min
- Vérification: ~30 sec

---

### Option B: Commandes Manuelles

```bash
cd /home/user/webapp/memory-proxy

# Variables
PROJECT_ID="box-magique-gp-prod"
REGION="us-central1"
SERVICE_NAME="mcp-memory-proxy"
GIT_COMMIT=$(git rev-parse --short HEAD)
IMAGE_TAG="phase2-${GIT_COMMIT}"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}"

# 1. Build
docker build --platform linux/amd64 -t ${IMAGE_NAME} .

# 2. Push
docker push ${IMAGE_NAME}

# 3. Deploy
gcloud run deploy ${SERVICE_NAME} \
  --image ${IMAGE_NAME} \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --service-account mcp-proxy@${PROJECT_ID}.iam.gserviceaccount.com \
  --set-env-vars "\
MCP_ENVIRONMENT=STAGING,\
MCP_GCP_PROJECT_ID=${PROJECT_ID},\
MCP_GCP_REGION=${REGION},\
MCP_CLOUD_RUN_SERVICE=${SERVICE_NAME},\
MCP_WEB_ALLOWED_DOMAINS=googleapis.com;github.com;genspark.ai,\
MCP_WEB_QUOTA_DAILY=100,\
MCP_TERMINAL_QUOTA_DAILY_READ=50,\
MCP_TERMINAL_QUOTA_DAILY_WRITE=10" \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 300

# 4. Vérifier
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --project ${PROJECT_ID} --format 'value(status.url)')
curl -s "${SERVICE_URL}/health" | jq
curl -s "${SERVICE_URL}/openapi.json" | jq '.paths | keys'
```

---

## ✅ VÉRIFICATION POST-DÉPLOIEMENT

### 1. Health Check
```bash
curl -s https://mcp-memory-proxy-522732657254.us-central1.run.app/health
```

**Attendu**:
```json
{
  "status": "ok",
  "version": "3.0.5",
  "build_date": "2026-02-20T20:30:00Z",
  "git_commit": "a548b88",
  "environment": "STAGING"
}
```

---

### 2. OpenAPI Routes
```bash
curl -s https://mcp-memory-proxy-522732657254.us-central1.run.app/openapi.json | jq '.paths | keys'
```

**Attendu** (18 routes Phase 2):
```json
[
  "/drive/tree",
  "/drive/file/{file_id}/metadata",
  "/drive/search",
  "/apps-script/project/{script_id}/deployments",
  "/apps-script/project/{script_id}/structure",
  "/cloud-run/service/{service_name}/status",
  "/cloud-logging/query",
  "/secrets/list",
  "/secrets/{secret_id}/reference",
  "/secrets/create",
  "/secrets/{secret_id}/rotate",
  "/web/search",
  "/web/fetch",
  "/terminal/run"
]
```

---

### 3. Test Endpoint Drive
```bash
# Test /drive/tree (devrait retourner mock structure pour l'instant)
curl -X GET -H "X-API-Key: YOUR_API_KEY" \
  "https://mcp-memory-proxy-522732657254.us-central1.run.app/drive/tree?folder_id=test&limit=10"
```

**Attendu**:
```json
{
  "ok": true,
  "run_id": "drive_tree_abc123...",
  "folder_id": "test",
  "folder_name": "ARCHIVES",
  "total_items": 0,
  "tree": [],
  "message": "Drive API integration pending - returning mock structure"
}
```

---

## 📊 INFORMATIONS DE DÉPLOIEMENT

### Révision Active
```bash
gcloud run revisions list \
  --service mcp-memory-proxy \
  --region us-central1 \
  --project box-magique-gp-prod \
  --limit 5
```

### Image Déployée
```bash
gcloud run services describe mcp-memory-proxy \
  --region us-central1 \
  --project box-magique-gp-prod \
  --format 'value(spec.template.spec.containers[0].image)'
```

**Attendu**: `gcr.io/box-magique-gp-prod/mcp-memory-proxy:phase2-a548b88`

---

## 🎯 RÉSULTAT FINAL

Après déploiement, fournir à l'utilisateur:

1. **Git Commit Déployé**: `a548b88`
2. **Image Tag**: `phase2-a548b88`
3. **Service URL**: `https://mcp-memory-proxy-522732657254.us-central1.run.app`
4. **Health**: `https://mcp-memory-proxy-522732657254.us-central1.run.app/health`
5. **OpenAPI**: `https://mcp-memory-proxy-522732657254.us-central1.run.app/openapi.json`
6. **Docs**: `https://mcp-memory-proxy-522732657254.us-central1.run.app/docs`

### Routes Phase 2 Disponibles (18 total)
- ✅ `/drive/tree` (GET)
- ✅ `/drive/file/{id}/metadata` (GET)
- ✅ `/drive/search` (GET)
- ✅ `/apps-script/project/{id}/deployments` (GET)
- ✅ `/apps-script/project/{id}/structure` (GET)
- ✅ `/cloud-run/service/{name}/status` (GET)
- ✅ `/cloud-logging/query` (POST)
- ✅ `/secrets/list` (GET)
- ✅ `/secrets/{id}/reference` (GET)
- ✅ `/secrets/create` (POST)
- ✅ `/secrets/{id}/rotate` (POST)
- ✅ `/web/search` (POST)
- ✅ `/web/fetch` (POST)
- ✅ `/terminal/run` (POST)

---

## ⚠️ NOTES IMPORTANTES

1. **Mock Responses**: Les endpoints retournent des structures mock pour l'instant (intégration API Google à venir)
2. **run_id**: Chaque appel génère un `run_id` unique traçable
3. **STAGING**: Environment par défaut = STAGING (passer à PROD après validation)
4. **Auth**: Endpoints Phase 2 utilisent `X-API-Key` header
5. **Logs**: Vérifier logs Cloud Run après déploiement pour toute erreur

---

**Dernière mise à jour**: 2026-02-20 20:30 UTC  
**Commit**: a548b88  
**Status**: ✅ Prêt pour déploiement
