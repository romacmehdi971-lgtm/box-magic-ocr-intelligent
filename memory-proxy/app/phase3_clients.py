"""
MCP Memory Proxy - Phase 3 Clients
Date: 2026-02-21

Purpose: Real API clients for:
- Apps Script API (deployments, structure, logs)
- Cloud Logging API (query with pagination)
- Secret Manager API (list, reference, create DRY_RUN, rotate DRY_RUN)

Service Account: mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import logging_v2
from google.cloud import secretmanager_v1
from typing import Dict, List, Optional, Any
import os
from datetime import datetime, timedelta
import json

# Service account configuration
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/secrets/sa-key.json")
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "box-magique-gp-prod")

# Scopes
APPS_SCRIPT_SCOPES = [
    'https://www.googleapis.com/auth/script.projects.readonly',
    'https://www.googleapis.com/auth/script.deployments.readonly'
]

LOGGING_SCOPES = ['https://www.googleapis.com/auth/logging.read']
SECRETS_SCOPES = ['https://www.googleapis.com/auth/cloud-platform']


# ============================================================================
# APPS SCRIPT CLIENT
# ============================================================================

def get_apps_script_service():
    """Create authenticated Apps Script API v1 service"""
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=APPS_SCRIPT_SCOPES
    )
    service = build('script', 'v1', credentials=credentials)
    return service


def get_apps_script_deployments(script_id: str) -> Dict[str, Any]:
    """
    Get all deployments for an Apps Script project
    
    Args:
        script_id: Apps Script project ID
        
    Returns:
        Dict with deployments list and metadata
    """
    try:
        service = get_apps_script_service()
        
        response = service.projects().deployments().list(
            scriptId=script_id
        ).execute()
        
        deployments = response.get('deployments', [])
        
        formatted_deployments = [
            {
                "deploymentId": d.get("deploymentId"),
                "deploymentConfig": {
                    "scriptId": d.get("deploymentConfig", {}).get("scriptId"),
                    "versionNumber": d.get("deploymentConfig", {}).get("versionNumber"),
                    "manifestFileName": d.get("deploymentConfig", {}).get("manifestFileName"),
                    "description": d.get("deploymentConfig", {}).get("description")
                },
                "updateTime": d.get("updateTime"),
                "entryPoints": d.get("entryPoints", [])
            }
            for d in deployments
        ]
        
        return {
            "script_id": script_id,
            "deployments": formatted_deployments,
            "total_deployments": len(formatted_deployments),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        return {
            "script_id": script_id,
            "error": f"Apps Script API error: {str(e)}",
            "deployments": [],
            "total_deployments": 0
        }


def get_apps_script_structure(script_id: str) -> Dict[str, Any]:
    """
    Get project structure (metadata + files list)
    
    Args:
        script_id: Apps Script project ID
        
    Returns:
        Dict with project metadata and file list
    """
    try:
        service = get_apps_script_service()
        
        # Get project content
        response = service.projects().getContent(
            scriptId=script_id
        ).execute()
        
        files = response.get('files', [])
        
        formatted_files = [
            {
                "name": f.get("name"),
                "type": f.get("type"),
                "functionSet": f.get("functionSet", {}).get("values", []) if f.get("functionSet") else [],
                "size": len(f.get("source", "")) if f.get("source") else 0
            }
            for f in files
        ]
        
        return {
            "script_id": script_id,
            "script_id_visible": response.get("scriptId"),
            "files": formatted_files,
            "total_files": len(formatted_files),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        return {
            "script_id": script_id,
            "error": f"Apps Script API error: {str(e)}",
            "files": [],
            "total_files": 0
        }


# ============================================================================
# CLOUD LOGGING CLIENT
# ============================================================================

def query_cloud_logging(
    filter_str: str,
    resource_names: Optional[List[str]] = None,
    time_range_hours: int = 24,
    limit: int = 100,
    order_by: str = "timestamp desc"
) -> Dict[str, Any]:
    """
    Query Cloud Logging with filters and pagination
    
    Args:
        filter_str: Cloud Logging filter (e.g., 'resource.type="cloud_run_revision"')
        resource_names: List of resource names to query (e.g., ["projects/PROJECT_ID"])
        time_range_hours: Hours to look back (default 24)
        limit: Max results (default 100)
        order_by: Sort order (default "timestamp desc")
        
    Returns:
        Dict with log entries
    """
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=LOGGING_SCOPES
        )
        
        client = logging_v2.Client(project=GCP_PROJECT_ID, credentials=credentials)
        
        # Build time filter
        time_ago = datetime.utcnow() - timedelta(hours=time_range_hours)
        time_filter = f'timestamp>="{time_ago.isoformat()}Z"'
        
        # Combine filters
        full_filter = f"{filter_str} AND {time_filter}"
        
        # Default resource names
        if not resource_names:
            resource_names = [f"projects/{GCP_PROJECT_ID}"]
        
        # Query logs
        entries = list(client.list_entries(
            resource_names=resource_names,
            filter_=full_filter,
            order_by=order_by,
            max_results=limit
        ))
        
        formatted_entries = [
            {
                "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                "severity": entry.severity,
                "log_name": entry.log_name,
                "resource": {
                    "type": entry.resource.type if entry.resource else None,
                    "labels": dict(entry.resource.labels) if entry.resource and entry.resource.labels else {}
                },
                "text_payload": entry.payload if isinstance(entry.payload, str) else None,
                "json_payload": entry.payload if isinstance(entry.payload, dict) else None,
                "labels": dict(entry.labels) if entry.labels else {}
            }
            for entry in entries
        ]
        
        return {
            "filter": full_filter,
            "resource_names": resource_names,
            "time_range_hours": time_range_hours,
            "total_entries": len(formatted_entries),
            "entries": formatted_entries,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        return {
            "filter": filter_str,
            "error": f"Cloud Logging API error: {str(e)}",
            "entries": [],
            "total_entries": 0
        }


# ============================================================================
# SECRET MANAGER CLIENT
# ============================================================================

def list_secrets(limit: int = 50) -> Dict[str, Any]:
    """
    List all secrets (metadata only, no values)
    
    Args:
        limit: Max secrets to return
        
    Returns:
        Dict with secrets list (no values)
    """
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SECRETS_SCOPES
        )
        
        client = secretmanager_v1.SecretManagerServiceClient(credentials=credentials)
        parent = f"projects/{GCP_PROJECT_ID}"
        
        secrets = []
        for secret in client.list_secrets(request={"parent": parent}):
            secrets.append({
                "name": secret.name.split('/')[-1],
                "full_name": secret.name,
                "create_time": secret.create_time.isoformat() if secret.create_time else None,
                "replication": str(secret.replication.automatic) if secret.replication else None,
                "labels": dict(secret.labels) if secret.labels else {}
            })
            if len(secrets) >= limit:
                break
        
        return {
            "project_id": GCP_PROJECT_ID,
            "total_secrets": len(secrets),
            "secrets": secrets,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        return {
            "project_id": GCP_PROJECT_ID,
            "error": f"Secret Manager API error: {str(e)}",
            "secrets": [],
            "total_secrets": 0
        }


def get_secret_reference(secret_id: str, version: str = "latest") -> Dict[str, Any]:
    """
    Get secret reference (metadata only, NO VALUE)
    
    Args:
        secret_id: Secret name
        version: Version (default "latest")
        
    Returns:
        Dict with secret reference (no value)
    """
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SECRETS_SCOPES
        )
        
        client = secretmanager_v1.SecretManagerServiceClient(credentials=credentials)
        secret_name = f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}/versions/{version}"
        
        version_obj = client.access_secret_version(request={"name": secret_name})
        
        return {
            "secret_id": secret_id,
            "version": version,
            "full_name": secret_name,
            "state": str(version_obj.state),
            "create_time": version_obj.create_time.isoformat() if version_obj.create_time else None,
            "value_provided": False,  # NEVER return the actual value
            "value": "[REDACTED]",    # Always redacted
            "mount_path_suggestion": f"/secrets/{secret_id}.json",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        return {
            "secret_id": secret_id,
            "version": version,
            "error": f"Secret Manager API error: {str(e)}",
            "value_provided": False,
            "value": "[ERROR]"
        }


def create_secret_dryrun(secret_id: str, value: str, labels: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    """
    DRY_RUN: Simulate secret creation (does NOT create)
    
    Args:
        secret_id: Secret name
        value: Secret value (will NOT be stored)
        labels: Optional labels
        
    Returns:
        Dict with DRY_RUN simulation result
    """
    return {
        "mode": "DRY_RUN",
        "action": "CREATE_SECRET",
        "secret_id": secret_id,
        "project_id": GCP_PROJECT_ID,
        "full_name": f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}",
        "value_length": len(value) if value else 0,
        "labels": labels or {},
        "would_create": True,
        "actual_created": False,
        "governance_note": "Use mode=APPLY after GO confirmation to create",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def rotate_secret_dryrun(secret_id: str, new_value: str) -> Dict[str, Any]:
    """
    DRY_RUN: Simulate secret rotation (does NOT rotate)
    
    Args:
        secret_id: Secret name
        new_value: New secret value (will NOT be stored)
        
    Returns:
        Dict with DRY_RUN simulation result
    """
    return {
        "mode": "DRY_RUN",
        "action": "ROTATE_SECRET",
        "secret_id": secret_id,
        "project_id": GCP_PROJECT_ID,
        "full_name": f"projects/{GCP_PROJECT_ID}/secrets/{secret_id}",
        "new_value_length": len(new_value) if new_value else 0,
        "would_rotate": True,
        "actual_rotated": False,
        "governance_note": "Use mode=APPLY after GO confirmation to rotate",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
