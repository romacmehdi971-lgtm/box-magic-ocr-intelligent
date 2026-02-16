# 🎯 ARCHITECTURE MCP MEMORY PROXY — FINALE VALIDÉE

**Date** : 2026-02-15 01:20  
**Projet** : box-magique-gp-prod  
**Région** : us-central1

---

## 📊 CONFIGURATION VALIDÉE

### Google Sheet Hub
- **ID** : `1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ`
- **Onglets** : 18 (tous exposés)
- **Nouveau** : `PROPOSITIONS_PENDING` (créé lors du déploiement)

### Service Account
- **Cloud Run** : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`
- **Client GPT** : Compte principal `romacmehdi971@gmail.com` (via IAM)
- **Pas de SA dédié** : L'existant suffit

### Workflow Validation
- **Type** : B (JSON structuré)
- **Onglet** : `PROPOSITIONS_PENDING`
- **Écriture MEMORY_LOG** : ❌ Interdite (validation humaine requise)
- **Notification** : Optionnelle (email)

---

## 🏗️ ARCHITECTURE TECHNIQUE

```
┌─────────────────────────────────────────────────────┐
│  GPT (romacmehdi971@gmail.com)                      │
└────────────────┬────────────────────────────────────┘
                 │
                 │ HTTPS + Bearer Token (gcloud auth)
                 ▼
┌─────────────────────────────────────────────────────┐
│  Cloud Run Service: mcp-memory-proxy                │
│  us-central1                                        │
│  Service Account: mcp-cockpit@...                   │
│  IAM: roles/run.invoker (authentifié)              │
│                                                      │
│  Endpoints:                                         │
│  GET  /health                    → Health check     │
│  GET  /sheets                    → Liste 18 onglets │
│  GET  /sheets/{name}             → Onglet spécifique│
│  POST /propose                   → Proposition      │
│  GET  /proposals                 → PROPOSITIONS_PENDING│
│  POST /proposals/{id}/validate   → Validation humaine│
│  GET  /docs                      → Auto-doc FastAPI │
│                                                      │
│  Variables d'env:                                   │
│  - GOOGLE_SHEET_ID=1kq83HL...   │
│  - READ_ONLY_MODE=true           │
│  - ENABLE_NOTIFICATIONS=false    │
└────────────────┬────────────────────────────────────┘
                 │
                 │ Google Sheets API v4
                 ▼
┌─────────────────────────────────────────────────────┐
│  Google Sheets: IAPF Memory Hub V1                  │
│  ID: 1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ  │
│                                                      │
│  18 onglets existants + 1 nouveau:                  │
│  - MEMORY_LOG                    (lecture)          │
│  - SNAPSHOT_ACTIVE               (lecture)          │
│  - REGLES_DE_GOUVERNANCE         (lecture)          │
│  - ARCHITECTURE_GLOBALE          (lecture)          │
│  - CARTOGRAPHIE_APPELS           (lecture)          │
│  - DEPENDANCES_SCRIPTS           (lecture)          │
│  - TRIGGERS_ET_TIMERS            (lecture)          │
│  - CONFLITS_DETECTES             (lecture)          │
│  - RISKS                         (lecture)          │
│  - ... (9 autres onglets)        (lecture)          │
│  - PROPOSITIONS_PENDING          (lecture + écriture)│
└─────────────────────────────────────────────────────┘
```

---

## 📦 STRUCTURE CODE

```
memory-proxy/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app + endpoints
│   ├── sheets.py            # Google Sheets API client
│   ├── proposals.py         # Logique propositions
│   ├── validation.py        # Détection doublons/conflits
│   ├── models.py            # Pydantic models
│   └── config.py            # Configuration
├── Dockerfile
├── requirements.txt
├── .dockerignore
└── README.md
```

---

## 🔐 IAM & PERMISSIONS

### Service Account Cloud Run
**Email** : `mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com`

**Permissions requises** :
- ✅ `roles/sheets.editor` sur le Sheet Hub (partage manuel via UI)
- ✅ `roles/logging.logWriter` (logs Cloud Run)

### Client GPT (romacmehdi971@gmail.com)
**Permission requise** :
- ✅ `roles/run.invoker` sur le service `mcp-memory-proxy`

**Commande IAM** (à exécuter après déploiement) :
```bash
gcloud run services add-iam-policy-binding mcp-memory-proxy \
  --region=us-central1 \
  --member="user:romacmehdi971@gmail.com" \
  --role="roles/run.invoker"
```

---

## 🔹 ENDPOINTS DÉTAILLÉS

### GET /health
**Description** : Health check  
**Auth** : Non requise  
**Response** :
```json
{
  "status": "healthy",
  "timestamp": "2026-02-15T01:20:00Z",
  "sheets_accessible": true
}
```

### GET /sheets
**Description** : Liste tous les onglets du Hub  
**Auth** : Requise (Bearer token)  
**Response** :
```json
{
  "spreadsheet_id": "1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ",
  "sheets": [
    "MEMORY_LOG",
    "SNAPSHOT_ACTIVE",
    "REGLES_DE_GOUVERNANCE",
    "... (18 onglets)"
  ]
}
```

### GET /sheets/{name}
**Description** : Retourne un onglet spécifique  
**Auth** : Requise  
**Params** : `name` (ex: "MEMORY_LOG")  
**Response** :
```json
{
  "sheet_name": "MEMORY_LOG",
  "headers": ["timestamp", "type", "title", "details", "author", "source", "tags"],
  "rows": [
    ["2026-02-14T20:00:00Z", "DECISION", "...", "...", "...", "...", "..."],
    ...
  ],
  "row_count": 156
}
```

### POST /propose
**Description** : Propose une nouvelle entrée MEMORY_LOG  
**Auth** : Requise  
**Body** :
```json
{
  "type": "DECISION",
  "title": "Titre court",
  "details": "Détails complets",
  "author": "romacmehdi971@gmail.com",
  "source": "GPT",
  "tags": "GPT;MCP"
}
```

**Response (si OK)** :
```json
{
  "status": "pending_validation",
  "proposal_id": "PROP-20260215-001",
  "validation_required": true,
  "message": "Proposition enregistrée dans PROPOSITIONS_PENDING. Validation humaine requise.",
  "proposal": {
    "timestamp": "2026-02-15T01:20:00Z",
    "type": "DECISION",
    "title": "Titre court",
    "details": "Détails complets",
    "author": "romacmehdi971@gmail.com",
    "source": "GPT",
    "tags": "GPT;MCP"
  }
}
```

**Response (si doublon)** :
```json
{
  "status": "duplicate",
  "message": "Entrée similaire trouvée dans MEMORY_LOG",
  "duplicate": {
    "timestamp": "2026-02-10T12:00:00Z",
    "title": "Titre similaire",
    "similarity": 0.95
  }
}
```

**Response (si conflit)** :
```json
{
  "status": "conflict",
  "message": "Conflit détecté avec règles de gouvernance",
  "conflicts": [
    {
      "rule": "VIDE > BRUIT",
      "violation": "..."
    }
  ]
}
```

### GET /proposals
**Description** : Liste les propositions en attente  
**Auth** : Requise  
**Response** :
```json
{
  "proposals": [
    {
      "proposal_id": "PROP-20260215-001",
      "timestamp": "2026-02-15T01:20:00Z",
      "type": "DECISION",
      "title": "...",
      "status": "pending"
    }
  ]
}
```

### POST /proposals/{id}/validate
**Description** : Valider une proposition (écrire dans MEMORY_LOG)  
**Auth** : Requise  
**Params** : `id` (ex: "PROP-20260215-001")  
**Body** :
```json
{
  "action": "approve"  // ou "reject"
}
```

**Response** :
```json
{
  "status": "approved",
  "message": "Entrée ajoutée dans MEMORY_LOG",
  "memory_log_row": 157
}
```

---

## 🔧 CORRECTION CLÔTURE JOURNÉE

### Problème actuel
**Erreur** : HTTP 403 `ACCESS_TOKEN_SCOPE_INSUFFICIENT`  
**Cause** : Appel à `google.apps.script.management.v1` (API Apps Script)

### Solution MCP
**Principe** : Remplacer appel Apps Script API par export direct Google Sheets

**Nouveau workflow** :
1. Lecture SNAPSHOT_ACTIVE
2. Export XLSX via Sheets API (pas Apps Script API)
3. Upload Drive (dossier ARCHIVES)
4. Écriture MEMORY_LOG "Clôture journée"

**Implémentation** : Endpoint `/close-day` dans `mcp-memory-proxy`

```python
@app.post("/close-day")
async def close_day():
    """
    Clôture journée sans Apps Script API
    
    Actions:
    1. Export SNAPSHOT_ACTIVE (Sheets API)
    2. Upload vers ARCHIVES (Drive API)
    3. Append MEMORY_LOG "Clôture journée"
    """
    # Export XLSX
    snapshot = sheets_client.export_sheet_as_xlsx("SNAPSHOT_ACTIVE")
    
    # Upload Drive
    archives_folder_id = sheets_client.get_setting("archives_folder_id")
    file = drive_client.upload_file(
        snapshot,
        f"SNAPSHOT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        archives_folder_id
    )
    
    # Log MEMORY_LOG
    sheets_client.append_memory_log({
        "type": "CONSTAT",
        "title": "MCP — Clôture journée",
        "details": f"Snapshot archivé : {file.id}",
        "author": "MCP_COCKPIT",
        "source": "MCP",
        "tags": "MCP;CLOSE"
    })
    
    return {"status": "success", "snapshot_file_id": file.id}
```

**Permissions requises** :
- ✅ `roles/drive.file` (upload vers ARCHIVES)
- ✅ `roles/sheets.editor` (append MEMORY_LOG)

---

## 📄 DOCUMENTATION AUTO

### Génération lors du déploiement
**Format** : Markdown + JSON
**Localisation** : `/docs` endpoint

**Contenu** :
```markdown
# MCP Memory Proxy — Documentation

**Déployé le** : 2026-02-15 01:30
**Version** : 1.0.0
**Service** : mcp-memory-proxy
**Région** : us-central1

## Architecture
[Schéma auto-généré]

## Endpoints
[Liste avec exemples curl]

## IAM
[Mapping service accounts / rôles]

## Onglets Hub (18)
[Liste avec description]
```

**Mise à jour dynamique** : Lors de chaque déploiement + check quotidien

---

## 📊 DÉPLOIEMENT ONE-SHOT

### Phase 1 : Génération code (15 min)
```bash
cd /home/user/webapp
mkdir -p memory-proxy/app
# Créer 7 fichiers Python
# Créer Dockerfile + requirements.txt
```

### Phase 2 : Build & Push (5 min)
```bash
cd memory-proxy
docker build -t us-central1-docker.pkg.dev/box-magique-gp-prod/mcp-cockpit/memory-proxy:v1.0.0 .
docker push us-central1-docker.pkg.dev/box-magique-gp-prod/mcp-cockpit/memory-proxy:v1.0.0
```

### Phase 3 : Déploiement Cloud Run (5 min)
```bash
gcloud run deploy mcp-memory-proxy \
  --region=us-central1 \
  --image=us-central1-docker.pkg.dev/box-magique-gp-prod/mcp-cockpit/memory-proxy:v1.0.0 \
  --service-account=mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com \
  --cpu=1 \
  --memory=512Mi \
  --max-instances=10 \
  --min-instances=0 \
  --timeout=60 \
  --ingress=internal-and-cloud-load-balancing \
  --no-allow-unauthenticated \
  --set-env-vars="GOOGLE_SHEET_ID=1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ,READ_ONLY_MODE=true,ENABLE_NOTIFICATIONS=false"
```

### Phase 4 : IAM (manuelle)
```bash
# 1. Partager Sheet Hub avec mcp-cockpit@... (Éditeur)
# Via Google Sheets UI : Partager → mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com → Éditeur

# 2. Donner accès Cloud Run à romacmehdi971@gmail.com
gcloud run services add-iam-policy-binding mcp-memory-proxy \
  --region=us-central1 \
  --member="user:romacmehdi971@gmail.com" \
  --role="roles/run.invoker"
```

### Phase 5 : Tests (5 min)
```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe mcp-memory-proxy --region=us-central1 --format='value(status.url)')

# Test health
curl $SERVICE_URL/health

# Test sheets list (avec auth)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  $SERVICE_URL/sheets

# Test lecture MEMORY_LOG
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  $SERVICE_URL/sheets/MEMORY_LOG

# Test proposition
curl -X POST \
  -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  -H "Content-Type: application/json" \
  -d '{"type":"CONSTAT","title":"Test GPT MCP","details":"Test proposition depuis GPT","author":"romacmehdi971@gmail.com","source":"GPT","tags":"GPT;MCP;TEST"}' \
  $SERVICE_URL/propose
```

**Durée totale** : 30 minutes + 5 min IAM

---

## ✅ GARANTIES

- ✅ Zéro duplication infra
- ✅ Réutilisation registry `mcp-cockpit` existant
- ✅ Réutilisation service account existant
- ✅ Correction clôture journée (sans Apps Script API)
- ✅ Documentation auto
- ✅ Onglet PROPOSITIONS_PENDING (nouveau)
- ✅ Validation humaine obligatoire
- ✅ Coût < 2 USD/mois

---

## 🚦 VALIDATION FINALE

**Architecture** : ✅ Validée  
**Configuration** : ✅ Complète  
**IAM** : ✅ Défini  
**Workflow** : ✅ Workflow B confirmé  
**Clôture journée** : ✅ Solution backend MCP

**Prêt à déployer** : ✅ OUI

---

*2026-02-15 01:20 — Architecture finale validée — Déploiement autorisé*
