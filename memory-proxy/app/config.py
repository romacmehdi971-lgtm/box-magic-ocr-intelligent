"""
MCP Memory Proxy - Configuration
Date: 2026-02-15
Purpose: Centralized configuration for MCP Memory Proxy service
"""
import os
from typing import List

# Google Sheet Configuration
GOOGLE_SHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "1kq83HL78CeJsG6s2TGkqr6Sre7BAK7mhhZYwrPIUjQQ")

# Service Account Configuration
# The service account JSON key should be mounted or provided via environment
SERVICE_ACCOUNT_KEY_PATH = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/app/sa-key.json")

# Operational Configuration
READ_ONLY_MODE = os.environ.get("READ_ONLY_MODE", "false").lower() == "true"
ENABLE_NOTIFICATIONS = os.environ.get("ENABLE_NOTIFICATIONS", "false").lower() == "true"
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")

# Drive Configuration
ARCHIVES_FOLDER_ID = os.environ.get("ARCHIVES_FOLDER_ID", "")  # Will be read from SETTINGS sheet

# Expected Sheet Tabs (18 tabs)
EXPECTED_TABS = [
    "MEMORY_LOG",
    "SNAPSHOT_ACTIVE",
    "REGLES_DE_GOUVERNANCE",
    "ARCHITECTURE_GLOBALE",
    "CARTOGRAPHIE_APPELS",
    "DEPENDANCES_SCRIPTS",
    "TRIGGERS_ET_TIMERS",
    "CONFLITS_DETECTES",
    "RISKS",
    "SETTINGS",
    "LOGS_SYSTEM",
    "INDEX_FACTURES",
    "PROPOSITIONS_PENDING",
    "BOX_CONFIG",
    "SUPPLIERS_MEMORY",
    "VALIDATION_RULES",
    "AUDIT_TRAIL",
    "PERFORMANCE_METRICS"
]

# API Configuration
API_VERSION = "1.0.0"
API_TITLE = "MCP Memory Proxy"
API_DESCRIPTION = "REST API for GPT access to IAPF Memory Hub"

# Security
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

# Proposal Configuration
PROPOSAL_ID_PREFIX = "PROP"
PROPOSAL_STATUS_PENDING = "PENDING"
PROPOSAL_STATUS_APPROVED = "APPROVED"
PROPOSAL_STATUS_REJECTED = "REJECTED"

# Memory Log Configuration
MEMORY_LOG_SHEET = "MEMORY_LOG"
PROPOSITIONS_PENDING_SHEET = "PROPOSITIONS_PENDING"
SNAPSHOT_SHEET = "SNAPSHOT_ACTIVE"
SETTINGS_SHEET = "SETTINGS"
CARTOGRAPHIE_SHEET = "CARTOGRAPHIE_APPELS"
DEPENDANCES_SHEET = "DEPENDANCES_SCRIPTS"
ARCHITECTURE_SHEET = "ARCHITECTURE_GLOBALE"

# Logging
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
