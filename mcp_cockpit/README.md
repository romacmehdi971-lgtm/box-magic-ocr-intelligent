# MCP Central Cockpit - IA Process Factory

## 🎯 Objectif

MCP Central Cockpit IAPF en PRODUCTION avec monitoring READ-ONLY et écriture contrôlée sur HUB ORION.

## 🏗️ Architecture

```
mcp_cockpit/
├── __init__.py
├── README.md
├── config/
│   ├── __init__.py
│   └── iapf_config.py         # Configuration centrale PROD
├── utils/
│   ├── __init__.py
│   └── safe_logger.py         # Logger sans PII
├── tools/
│   ├── __init__.py
│   ├── cloudrun_tool.py       # READ-ONLY Cloud Run
│   ├── github_tool.py         # READ-ONLY GitHub
│   ├── drive_tool.py          # READ-ONLY Drive + création structure
│   └── sheets_tool.py         # READ BOX2026 + WRITE HUB ORION
├── orchestrator.py            # Orchestrateur principal
├── cli.py                     # Interface CLI
├── reports/                   # Rapports générés
├── snapshots/                 # Snapshots JSON
└── audit_logs/                # Logs d'audit
```

## 🛠️ Outils Disponibles

### Cloud Run
- `iAPF.cloudrun.status` - Statut du service
- `iAPF.cloudrun.logs.export` - Export logs (sanitized)

### GitHub
- `iAPF.github.audit` - Audit d'un repo (OCR ou CRM)
- `iAPF.github.snapshot` - Snapshot de tous les repos

### Drive
- `iAPF.drive.map_architecture` - Cartographie Drive
- `iAPF.drive.audit_naming` - Audit nommage factures
- Standard: `YYYY-MM-DD_FOURNISSEUR_TTC_<montant>EUR_<TYPE>_<NUMERO>.pdf`

### Sheets
- `iAPF.sheets.box2026.audit` - Audit BOX2026 (READ-ONLY)
  - Vérification CONFIG
  - Vérification onglets CRM_*
  - Détection incohérences
- `iAPF.sheets.hub.sync` - Sync HUB ORION (WRITE contrôlé)
  - MEMORY_LOG (append TSV 7 colonnes)
  - SNAPSHOT_ACTIVE (update)
  - RISKS (append)
  - CONFLITS_DETECTES (append)

### Orchestrateur
- `iAPF.healthcheck.iapf` - **Commande principale**
  - Exécute tous les audits
  - Génère rapport Markdown
  - Génère snapshot JSON
  - Génère audit log
  - Sync HUB ORION

## 🚀 Usage

### Commande Unique

```bash
# Depuis la racine du projet
python healthcheck_iapf.py healthcheck

# Ou avec Python module
python -m mcp_cockpit.cli healthcheck

# Avec répertoire de sortie personnalisé
python healthcheck_iapf.py healthcheck -o ./custom_output
```

### Intégration Python

```python
from mcp_cockpit.orchestrator import get_orchestrator

# Exécuter healthcheck
orchestrator = get_orchestrator()
results = orchestrator.healthcheck_iapf()

# Accéder aux résultats
print(results['status'])
print(results['report'])
print(results['snapshot'])
```

## 📦 Artifacts Générés

Chaque exécution génère 3 fichiers :

1. **Snapshot JSON** : `snapshot_YYYYMMDD_HHMMSSZ.json`
   - État complet du système
   - Tous les audits
   - Risks & Conflicts

2. **Report Markdown** : `healthcheck_YYYYMMDD_HHMMSSZ.md`
   - Rapport lisible
   - Sections structurées
   - Résumé des risques

3. **Audit Log** : `audit_log_YYYYMMDD_HHMMSSZ.json`
   - Log d'audit append-only
   - Traçabilité complète

## 📊 Contexte Production

### Cloud Run
- **Project**: box-magique-gp-prod
- **Region**: us-central1
- **Service**: box-magic-ocr-intelligent

### GitHub
- **OCR**: https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent
- **CRM**: https://github.com/romacmehdi971-lgtm/crm-cyril-martins

### Google Sheets
- **BOX2026**: 1U_tLe3n_1_hL6HcRJ4yrbMDTNMfTKvPsTrbva1Sjc-4
- **HUB ORION**: 1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ

### Drive Structure (à créer)
```
IA Process Factory/
└── 00_GOUVERNANCE/
    └── MCP_COCKPIT/
        ├── 01_CONFIG/
        ├── 02_REPORTS/
        ├── 03_SNAPSHOTS/
        ├── 04_AUDIT_LOGS/
        ├── 05_RUNBOOKS/
        └── 99_ARCHIVES/
```

## 🔒 Sécurité

### Interdictions Absolues
- ❌ Aucun rename/move/delete Drive
- ❌ Aucun deploy Cloud Run
- ❌ Aucun push GitHub
- ❌ Aucun secret dans le code
- ❌ Aucun log avec données PII/facture/client

### Logger Sécurisé
- Masquage automatique des patterns sensibles
- Aucune donnée personnelle dans les logs
- Sanitization des montants TTC

## 🎯 HUB ORION - Format MEMORY_LOG

Structure TSV 7 colonnes strict :

```
timestamp | event_type | source | entity_id | action | status | metadata_json
```

Exemple :
```
2026-02-12T23:30:00Z | healthcheck | mcp_cockpit | iapf_healthcheck | full_audit | completed | {"cloudrun_status": "unknown", "github_repos": 2}
```

## 🔄 Workflow

1. **Exécution**: `python healthcheck_iapf.py healthcheck`
2. **Audits**: Tous les composants sont audités
3. **Analyse**: Détection des risques et conflits
4. **Rapports**: Génération des artifacts
5. **Sync**: Synchronisation HUB ORION
6. **Output**: Fichiers sauvegardés dans `mcp_cockpit/reports/`

## 📈 Evolution Multi-Clients

L'architecture est conçue pour évoluer :

- Configuration par client dans `config/clients/`
- Snapshots séparés par client
- HUB ORION peut gérer plusieurs clients
- Architecture extensible

## 🆘 Support

Pour toute question ou problème :
1. Vérifier la configuration dans `config/iapf_config.py`
2. Consulter les logs générés
3. Examiner le dernier snapshot JSON

## 📝 Versions

- **v1.0.0** - Version initiale PROD
  - Commande `healthcheck_iapf` fonctionnelle
  - READ-ONLY monitoring
  - WRITE contrôlé HUB ORION
  - Artifacts générés
  - Architecture extensible

---

*MCP Central Cockpit IAPF - Production Ready*
