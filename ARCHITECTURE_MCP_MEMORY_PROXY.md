# 🎯 ARCHITECTURE MCP MEMORY PROXY — PROPOSITION FINALE

**Date** : 2026-02-15 01:00  
**Projet** : box-magique-gp-prod  
**Région** : us-central1

---

## 📊 AUDIT INFRASTRUCTURE EXISTANTE

### ✅ Confirmé présent
- **Cloud Run Service** : `box-magic-ocr-intelligent` (actif, révision 00091-gw7)
- **Cloud Run Job** : `mcp-cockpit-iapf-healthcheck` (10 exécutions, dernière réussie)
- **Artifact Registry** : 
  - `cloud-run-source-deploy` (DOCKER)
  - `mcp-cockpit` (DOCKER, vide actuellement)
- **Service Account** : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com` (READ ONLY + HUB write)

### ⚠️ Non trouvé
- **Image Docker `mcp-cockpit`** : Le registry existe mais est **vide**
- **Healthcheck en tant que service** : Uniquement en tant que Job

---

## 🎯 ARCHITECTURE PROPOSÉE

### Principe : Extension propre, pas duplication

```
┌─────────────────────────────────────────────────────┐
│  GPT (via MCP Client)                               │
└────────────────┬────────────────────────────────────┘
                 │
                 │ HTTPS (IAM protégé)
                 ▼
┌─────────────────────────────────────────────────────┐
│  Cloud Run Service: mcp-memory-proxy                │
│  Image: us-central1-docker.pkg.dev/.../            │
│         mcp-cockpit/memory-proxy:latest             │
│                                                      │
│  Endpoints:                                         │
│  GET  /memory/full       → Tout le Hub             │
│  GET  /memory/log        → MEMORY_LOG              │
│  GET  /memory/snapshot   → SNAPSHOT_ACTIVE         │
│  GET  /memory/rules      → REGLES_DE_GOUVERNANCE   │
│  GET  /memory/cartography→ CARTOGRAPHIE_APPELS     │
│  GET  /memory/dependencies→DEPENDANCES_SCRIPTS     │
│  GET  /memory/architecture→ARCHITECTURE_GLOBALE    │
│  GET  /memory/triggers   → TRIGGERS_ET_TIMERS      │
│  POST /memory/propose    → Proposition (validation)│
│                                                      │
│  Service Account: mcp-cockpit@...                   │
│  IAM: roles/run.invoker (authentifié uniquement)   │
└────────────────┬────────────────────────────────────┘
                 │
                 │ Google Sheets API
                 ▼
┌─────────────────────────────────────────────────────┐
│  Google Sheets: IAPF Memory Hub V1                  │
│  (Source unique de vérité)                          │
│                                                      │
│  Onglets:                                           │
│  - MEMORY_LOG                                       │
│  - SNAPSHOT_ACTIVE                                  │
│  - REGLES_DE_GOUVERNANCE                            │
│  - ARCHITECTURE_GLOBALE                             │
│  - CARTOGRAPHIE_APPELS                              │
│  - DEPENDANCES_SCRIPTS                              │
│  - TRIGGERS_ET_TIMERS                               │
│  - CONFLITS_DETECTES                                │
│  - RISKS                                            │
└─────────────────────────────────────────────────────┘
```

---

## 📦 COMPOSANTS À CRÉER

### 1️⃣ Image Docker : `memory-proxy`

**Base** : Python 3.11-slim  
**Framework** : FastAPI (léger, rapide)  
**Dépendances** :
- `fastapi`
- `uvicorn[standard]`
- `google-auth`
- `google-auth-oauthlib`
- `google-api-python-client`

**Structure** :
```
memory-proxy/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app
│   ├── sheets_client.py     # Google Sheets API
│   ├── memory_service.py    # Logique métier
│   └── models.py            # Pydantic models
├── Dockerfile
├── requirements.txt
└── .dockerignore
```

**Endpoints** :

```python
@app.get("/memory/full")
async def get_full_memory():
    """Retourne tout le Hub (tous les onglets)"""
    return sheets_client.read_all_sheets()

@app.get("/memory/log")
async def get_memory_log():
    """Retourne MEMORY_LOG uniquement"""
    return sheets_client.read_sheet("MEMORY_LOG")

@app.get("/memory/snapshot")
async def get_snapshot():
    """Retourne SNAPSHOT_ACTIVE"""
    return sheets_client.read_sheet("SNAPSHOT_ACTIVE")

@app.get("/memory/rules")
async def get_rules():
    """Retourne REGLES_DE_GOUVERNANCE"""
    return sheets_client.read_sheet("REGLES_DE_GOUVERNANCE")

# ... etc pour tous les onglets

@app.post("/memory/propose")
async def propose_memory_entry(entry: MemoryEntry):
    """
    Propose une nouvelle entrée MEMORY_LOG
    
    Workflow:
    1. Valider format (7 colonnes TSV)
    2. Vérifier doublon (titre + date)
    3. Vérifier conflit (règles de gouvernance)
    4. Retourner proposition avec validation_required=True
    5. Humain valide manuellement via HUB
    """
    validation = memory_service.validate_entry(entry)
    
    if validation.has_duplicate:
        return {"status": "duplicate", "details": validation.duplicate_details}
    
    if validation.has_conflict:
        return {"status": "conflict", "details": validation.conflict_details}
    
    return {
        "status": "pending_validation",
        "proposal": entry.dict(),
        "validation_required": True,
        "message": "Proposition enregistrée. Validation humaine requise dans HUB."
    }
```

---

### 2️⃣ Cloud Run Service : `mcp-memory-proxy`

**Configuration** :
```yaml
service: mcp-memory-proxy
region: us-central1
image: us-central1-docker.pkg.dev/box-magique-gp-prod/mcp-cockpit/memory-proxy:latest
service_account: mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com

# Ressources
cpu: 1
memory: 512Mi
max_instances: 10
min_instances: 0 (scale to zero)
timeout: 60s

# IAM
ingress: internal-and-cloud-load-balancing
authentication: required (IAM)

# Variables d'environnement
GOOGLE_SHEET_ID: <ID du Hub IAPF Memory V1>
READ_ONLY_MODE: true (par défaut)
```

---

### 3️⃣ IAM (à configurer manuellement)

**Service Account** : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com` (existant)

**Permissions requises** :
```bash
# Lecture Google Sheets
roles/sheets.viewer (sur le Google Sheet HUB)

# Écriture Google Sheets (pour POST /memory/propose, validation humaine)
roles/sheets.editor (sur le Google Sheet HUB)

# Cloud Run
roles/run.invoker (pour GPT/MCP client)
```

**Commandes IAM (à exécuter manuellement)** :
```bash
# Donner accès lecture/écriture au Sheet HUB
# (à faire via Google Sheets UI : Partager → mcp-cockpit@... → Éditeur)

# Donner accès Cloud Run au client GPT
gcloud run services add-iam-policy-binding mcp-memory-proxy \
  --region=us-central1 \
  --member="serviceAccount:<YOUR_GPT_CLIENT_SA>@box-magique-gp-prod.iam.gserviceaccount.com" \
  --role="roles/run.invoker"
```

---

## 🔐 SÉCURITÉ

### Lecture (GET)
- ✅ Authentification IAM requise
- ✅ Service Account `mcp-cockpit` avec accès READ sur le Hub
- ✅ Pas d'accès public
- ✅ Logs activés

### Écriture (POST)
- ✅ Validation format (7 colonnes TSV)
- ✅ Détection doublons (titre + date)
- ✅ Détection conflits (règles de gouvernance)
- ✅ **Validation humaine obligatoire** (pas d'écriture automatique)
- ✅ Proposition stockée temporairement (ou envoyée via notification)

---

## 🚀 PLAN DE DÉPLOIEMENT

### Phase 1 : Création image Docker (15 min)
```bash
cd /home/user/webapp
mkdir -p memory-proxy/app
# Créer les fichiers Python (main.py, sheets_client.py, etc.)
# Créer Dockerfile + requirements.txt
```

### Phase 2 : Build & Push (5 min)
```bash
cd memory-proxy
docker build -t us-central1-docker.pkg.dev/box-magique-gp-prod/mcp-cockpit/memory-proxy:latest .
docker push us-central1-docker.pkg.dev/box-magique-gp-prod/mcp-cockpit/memory-proxy:latest
```

### Phase 3 : Déploiement Cloud Run (5 min)
```bash
gcloud run deploy mcp-memory-proxy \
  --region=us-central1 \
  --image=us-central1-docker.pkg.dev/box-magique-gp-prod/mcp-cockpit/memory-proxy:latest \
  --service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
  --cpu=1 \
  --memory=512Mi \
  --max-instances=10 \
  --min-instances=0 \
  --timeout=60 \
  --ingress=internal-and-cloud-load-balancing \
  --no-allow-unauthenticated \
  --set-env-vars=GOOGLE_SHEET_ID=<ID_HUB>,READ_ONLY_MODE=true
```

### Phase 4 : Configuration IAM (manuelle)
```bash
# Partager le Google Sheet HUB avec mcp-cockpit@... (Éditeur)
# Donner accès Cloud Run au client GPT (roles/run.invoker)
```

### Phase 5 : Tests (10 min)
```bash
# Test lecture
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://mcp-memory-proxy-<hash>-uc.a.run.app/memory/log

# Test proposition
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"type":"CONSTAT","title":"Test GPT","details":"Test proposition"}' \
  https://mcp-memory-proxy-<hash>-uc.a.run.app/memory/propose
```

---

## ✅ GARANTIES

### Zéro duplication
- ✅ Réutilise `mcp-cockpit` registry existant
- ✅ Réutilise service account `mcp-cockpit` existant
- ✅ Pas de nouveau projet GCP
- ✅ Pas de nouveau OCR
- ✅ Pas de nouveau healthcheck

### Extension propre
- ✅ Nouveau service dédié : `mcp-memory-proxy`
- ✅ Nouvelle image : `memory-proxy:latest`
- ✅ Pas de modification de l'existant

### Sécurité
- ✅ Authentification IAM requise
- ✅ Pas d'écriture automatique (validation humaine)
- ✅ Logs activés
- ✅ Scale to zero (coût optimisé)

---

## 📊 COÛT ESTIMÉ

**Cloud Run Service** : `mcp-memory-proxy`
- Requêtes : ~1000/mois (GPT queries)
- CPU : 1 vCPU × ~10 min/mois = négligeable
- Mémoire : 512 Mi × ~10 min/mois = négligeable
- **Coût total** : **< 1 USD/mois** (scale to zero)

**Artifact Registry** : Stockage image (~200 MB)
- **Coût** : **< 0.10 USD/mois**

**Total estimé** : **< 2 USD/mois**

---

## 🎯 VALIDATION AVANT DÉPLOIEMENT

### Questions à confirmer

1. **ID du Google Sheet HUB** : Quel est l'ID exact du Sheet "IAPF Memory Hub V1" ?

2. **Client GPT** : Quel service account utilisera GPT pour appeler le proxy ?
   - Si pas encore créé, faut-il créer `gpt-client@box-magique-gp-prod.iam.gserviceaccount.com` ?

3. **Validation humaine** : Pour POST /memory/propose, préférez-vous :
   - **Option A** : Retourner la proposition à GPT (GPT affiche "validation requise")
   - **Option B** : Envoyer notification (email/Slack) à l'humain
   - **Option C** : Écrire dans un onglet "PROPOSITIONS_PENDING" du Hub

4. **Onglets à exposer** : Confirmez-vous cette liste ?
   - MEMORY_LOG
   - SNAPSHOT_ACTIVE
   - REGLES_DE_GOUVERNANCE
   - ARCHITECTURE_GLOBALE
   - CARTOGRAPHIE_APPELS
   - DEPENDANCES_SCRIPTS
   - TRIGGERS_ET_TIMERS
   - CONFLITS_DETECTES
   - RISKS

---

## 🚦 FEUX VERTS REQUIS

Avant de déployer, merci de confirmer :

- [ ] Architecture validée (schéma ci-dessus)
- [ ] ID du Google Sheet HUB fourni
- [ ] Service account client GPT créé/identifié
- [ ] Choix workflow validation (A/B/C)
- [ ] Liste onglets confirmée
- [ ] Prêt à exécuter les commandes IAM manuelles

**Une fois validé, je génère le code complet et lance le déploiement.**

---

*2026-02-15 01:00 — Architecture MCP Memory Proxy — Validation requise*
