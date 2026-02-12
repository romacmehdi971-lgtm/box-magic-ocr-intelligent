"""
Configuration centrale IAPF PROD
"""
import os
from datetime import datetime

# Cloud Run Production
CLOUDRUN_CONFIG = {
    "project": "box-magique-gp-prod",
    "region": "us-central1",
    "service": "box-magic-ocr-intelligent",
    "url": "https://box-magic-ocr-intelligent-xxxxxx-uc.a.run.app"  # Fallback
}

# GitHub Repositories
GITHUB_REPOS = {
    "ocr": {
        "owner": "romacmehdi971-lgtm",
        "repo": "box-magic-ocr-intelligent",
        "url": "https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent"
    },
    "crm": {
        "owner": "romacmehdi971-lgtm",
        "repo": "crm-cyril-martins",
        "url": "https://github.com/romacmehdi971-lgtm/crm-cyril-martins"
    }
}

# Google Sheets
SHEETS_CONFIG = {
    "box2026": {
        "id": "1U_tLe3n_1_hL6HcRJ4yrbMDTNMfTKvPsTrbva1Sjc-4",
        "url": "https://docs.google.com/spreadsheets/d/1U_tLe3n_1_hL6HcRJ4yrbMDTNMfTKvPsTrbva1Sjc-4/edit",
        "name": "BOX2026"
    },
    "hub_orion": {
        "id": "1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ",
        "url": "https://docs.google.com/spreadsheets/d/1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ/edit",
        "name": "IAPF_MEMORY_HUB_V1",
        "writable_sheets": ["MEMORY_LOG", "SNAPSHOT_ACTIVE", "RISKS", "CONFLITS_DETECTES"]
    }
}

# Drive Architecture
DRIVE_PATHS = {
    "root": "IA Process Factory",
    "governance": "00_GOUVERNANCE",
    "mcp_cockpit": "MCP_COCKPIT",
    "subdirs": [
        "01_CONFIG",
        "02_REPORTS", 
        "03_SNAPSHOTS",
        "04_AUDIT_LOGS",
        "05_RUNBOOKS",
        "99_ARCHIVES"
    ]
}

# Standard naming factures
INVOICE_NAMING_PATTERN = r"^\d{4}-\d{2}-\d{2}_[A-Z0-9_]+_TTC_[\d.]+EUR_[A-Z_]+_[A-Z0-9_]+\.pdf$"
INVOICE_NAMING_TEMPLATE = "YYYY-MM-DD_FOURNISSEUR_TTC_<montant>EUR_<TYPE>_<NUMERO>.pdf"

# Hub Orion - Structure TSV Memory Log (7 colonnes strict)
HUB_MEMORY_LOG_COLUMNS = [
    "timestamp",
    "event_type", 
    "source",
    "entity_id",
    "action",
    "status",
    "metadata_json"
]

# Interdictions absolues
FORBIDDEN_ACTIONS = [
    "drive_rename",
    "drive_move", 
    "drive_delete",
    "cloudrun_deploy",
    "github_push",
    "secrets_in_code",
    "log_with_pii"
]

# Snapshot structure
SNAPSHOT_SCHEMA = {
    "meta": {
        "timestamp": "ISO8601",
        "version": "string",
        "environment": "PROD"
    },
    "cloudrun": {},
    "github": {},
    "drive": {},
    "sheets": {},
    "hub": {},
    "risks": [],
    "conflicts": [],
    "artifacts": []
}

def get_timestamp():
    """Timestamp ISO8601 strict"""
    return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

def get_filename_timestamp():
    """Timestamp pour noms de fichiers"""
    return datetime.utcnow().strftime("%Y%m%d_%H%M%SZ")

def validate_config():
    """Valide la configuration"""
    errors = []
    
    # Vérifier que toutes les clés essentielles existent
    if not CLOUDRUN_CONFIG.get("project"):
        errors.append("CLOUDRUN_CONFIG.project manquant")
    
    if not GITHUB_REPOS.get("ocr") or not GITHUB_REPOS.get("crm"):
        errors.append("GITHUB_REPOS incomplet")
    
    if not SHEETS_CONFIG.get("box2026") or not SHEETS_CONFIG.get("hub_orion"):
        errors.append("SHEETS_CONFIG incomplet")
    
    return len(errors) == 0, errors

# Export config validation au module load
CONFIG_VALID, CONFIG_ERRORS = validate_config()
