# MCP Central Cockpit IAPF - Guide de Déploiement Production

## 📋 Vue d'ensemble

MCP Central Cockpit IAPF - Production Ready avec commande unique `healthcheck_iapf`.

## ✅ Corrections Appliquées (Review PR#5)

### 1️⃣ Split PR ✅
- PR cockpit-only
- Aucune modification runtime OCR
- Isolation complète du module

### 2️⃣ MEMORY_LOG - Format IAPF Officiel ✅

**Format strict obligatoire** :
```
ts_iso | type | title | details | author | source | tags
```

**Exigences** :
- Séparateur : TAB (`\t`) strict
- 7 colonnes exactes
- `ts_iso` : ISO UTC  
- `tags` : séparés par `;`

**Exemple** :
```
2026-02-12T23:30:00Z	healthcheck	IAPF Full Healthcheck	{"cloudrun_status":"unknown","github_repos":2}	mcp_cockpit	mcp_cockpit	audit;monitoring;production
```

### 3️⃣ .gitignore Correct ✅

Ignorer uniquement :
- `credentials.json`
- `.env`
- `secrets.*`
- Artifacts générés : `mcp_cockpit/reports/healthcheck_*.md`, `snapshot_*.json`, `audit_log_*.json`

PAS d'ignore générique `.json` ou `**/.json`

### 4️⃣ Artifacts Générés ✅

Fichiers ignorés par Git :
- `mcp_cockpit/reports/healthcheck_*.md`
- `mcp_cockpit/reports/snapshot_*.json`
- `mcp_cockpit/reports/audit_log_*.json`

Output : Drive `MCP_COCKPIT/02_REPORTS/`

### 5️⃣ No-Touch OCR Runtime ✅

Aucun changement dans :
- `levels/`
- `connectors/` existants
- `ocr_engine.py`

Module `mcp_cockpit/` totalement isolé.

## 🚀 Usage

```bash
python healthcheck_iapf.py healthcheck
```

## 📦 Structure

```
mcp_cockpit/
├── config/          # Configuration PROD
│   ├── __init__.py
│   └── iapf_config.py  # Format MEMORY_LOG officiel
├── utils/           # SafeLogger
│   ├── __init__.py
│   └── safe_logger.py
├── tools/           # Outils MCP
│   ├── __init__.py
│   ├── cloudrun_tool.py
│   ├── github_tool.py
│   ├── drive_tool.py
│   └── sheets_tool.py  # Format IAPF strict
├── orchestrator.py  # Coordination
├── cli.py           # Interface CLI
├── reports/         # Artifacts (ignorés)
│   └── .gitkeep
├── snapshots/       # Snapshots (ignorés)
│   └── .gitkeep
└── audit_logs/      # Logs (ignorés)
    └── .gitkeep
```

## 🎯 Format MEMORY_LOG

**Code** :
```python
hub_sync = sheets.sync_hub(
    event_type="healthcheck",
    title="IAPF Full Healthcheck",
    details='{"cloudrun_status":"unknown"}',
    author="mcp_cockpit",
    tags="audit;monitoring;production"
)
```

**TSV Généré** :
```
2026-02-12T23:30:00Z	healthcheck	IAPF Full Healthcheck	{"cloudrun_status":"unknown"}	mcp_cockpit	mcp_cockpit	audit;monitoring;production
```

## 📊 HUB ORION Writables

- `MEMORY_LOG` : Append-only (format strict)
- `SNAPSHOT_ACTIVE` : Update
- `RISKS` : Append
- `CONFLITS_DETECTES` : Append

## 🔒 Sécurité

- ✅ READ-ONLY monitoring
- ✅ WRITE contrôlé HUB ORION
- ✅ Aucune action destructive
- ✅ SafeLogger masquant PII
- ✅ Fallbacks safe

## 📈 Évolution

- Phase 2 : APIs réelles (Drive, Sheets, gcloud)
- Phase 3 : Multi-clients
- Phase 4 : Automatisation

---

*MCP Central Cockpit IAPF v1.0.0 - Production Ready*
