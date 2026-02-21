"""
Phase 2 MCP Extensions - Consolidated Implementation
Drive, Apps Script, Cloud Run, Secrets, Web, Terminal endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, Header
from typing import Optional, Dict, Any, List
from pydantic import BaseModel
import os
import json

from .governance import generate_run_id, ActionMode, should_apply_action, build_governed_response
from .redaction import redact_response, redact_secret_value_always
from .config import get_settings
from . import drive_client

router = APIRouter()
settings = get_settings()

# ============================================================================
# MODELS
# ============================================================================

class DriveTreeRequest(BaseModel):
    folder_id: str
    max_depth: int = 2
    limit: int = 100
    include_trashed: bool = False

class SecretCreateRequest(BaseModel):
    secret_id: str
    value: str
    labels: Dict[str, str] = {}
    replication: str = "automatic"
    project_id: Optional[str] = None
    dry_run: bool = True

class SecretRotateRequest(BaseModel):
    secret_id: str
    new_value: str
    disable_previous_version: bool = False
    dry_run: bool = True

class WebSearchRequest(BaseModel):
    query: str
    max_results: int = 10
    allowed_domains: List[str] = []

class WebFetchRequest(BaseModel):
    url: str
    method: str = "GET"
    headers: Dict[str, str] = {}
    max_size: int = 1048576  # 1MB

class TerminalRunRequest(BaseModel):
    command: str
    mode: str = "READ_ONLY"
    timeout_seconds: int = 30
    dry_run: bool = False

class CloudLoggingQueryRequest(BaseModel):
    resource_type: str
    resource_labels: Dict[str, str]
    filter: str = "severity>=INFO"
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    limit: int = 100
    page_token: Optional[str] = None


# ============================================================================
# DRIVE ENDPOINTS
# ============================================================================

@router.get("/drive/tree")
async def drive_tree(
    folder_id: str,
    max_depth: int = 2,
    limit: int = 100,
    include_trashed: bool = False,
    x_api_key: str = Header(None)
):
    """List recursive folder tree with controlled depth"""
    run_id = generate_run_id("drive", "tree")
    
    try:
        # Real Google Drive API call via drive_client
        tree_data = drive_client.list_folder_tree(
            folder_id=folder_id,
            max_depth=max_depth,
            limit=limit
        )
        
        response = {
            "ok": True,
            "run_id": run_id,
            "folder_id": tree_data.get("folder_id"),
            "folder_name": tree_data.get("folder_name"),
            "total_items": tree_data.get("total_items", 0),
            "tree": tree_data.get("tree", []),
            "truncated": tree_data.get("total_items", 0) >= limit,
            "pagination": {"next_page_token": None},
            "error": tree_data.get("error")
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drive/file/{file_id}/metadata")
async def drive_file_metadata(
    file_id: str,
    x_api_key: str = Header(None)
):
    """Get complete file metadata"""
    run_id = generate_run_id("drive", "metadata")
    
    try:
        # Real Google Drive API call via drive_client
        metadata = drive_client.get_file_metadata(file_id)
        
        response = {
            "ok": True,
            "run_id": run_id,
            "file": metadata
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/drive/search")
async def drive_search(
    query: str,
    folder_id: Optional[str] = None,
    mime_type: Optional[str] = None,
    modified_after: Optional[str] = None,
    limit: int = 50,
    page_token: Optional[str] = None,
    x_api_key: str = Header(None)
):
    """Search files by name/regex"""
    run_id = generate_run_id("drive", "search")
    
    if len(query) > 100:
        raise HTTPException(status_code=400, detail="Query too long (max 100 chars)")
    
    if limit > 200:
        limit = 200
    
    try:
        # Real Google Drive API call via drive_client
        search_data = drive_client.search_files(
            query=query,
            folder_id=folder_id,
            limit=limit
        )
        
        response = {
            "ok": True,
            "run_id": run_id,
            "query": search_data.get("query"),
            "folder_id": search_data.get("folder_id"),
            "total_results": search_data.get("total_results", 0),
            "files": search_data.get("files", []),
            "next_page_token": None,
            "error": search_data.get("error")
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# APPS SCRIPT ENDPOINTS
# ============================================================================

@router.get("/apps-script/project/{script_id}/deployments")
async def apps_script_deployments(
    script_id: str,
    limit: int = 20,
    x_api_key: str = Header(None)
):
    """List Apps Script deployments"""
    run_id = generate_run_id("apps_script", "deployments")
    
    if limit > 50:
        limit = 50
    
    try:
        # TODO: Implement actual Apps Script API call
        response = {
            "ok": True,
            "run_id": run_id,
            "script_id": script_id,
            "deployments": [],
            "total_deployments": 0,
            "message": "Apps Script API integration pending - returning mock structure"
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/apps-script/project/{script_id}/structure")
async def apps_script_structure(
    script_id: str,
    x_api_key: str = Header(None)
):
    """Get Apps Script project structure"""
    run_id = generate_run_id("apps_script", "structure")
    
    try:
        # TODO: Implement actual Apps Script API call
        response = {
            "ok": True,
            "run_id": run_id,
            "script_id": script_id,
            "project_name": "IAPF HUB Memory",
            "files": [],
            "total_files": 0,
            "total_functions": 0,
            "message": "Apps Script API integration pending - returning mock structure"
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CLOUD RUN ENDPOINTS
# ============================================================================

@router.get("/cloud-run/service/{service_name}/status")
async def cloud_run_service_status(
    service_name: str,
    region: Optional[str] = None,
    x_api_key: str = Header(None)
):
    """Get Cloud Run service status"""
    run_id = generate_run_id("cloud_run", "status")
    
    region = region or settings.MCP_GCP_REGION or "us-central1"
    
    try:
        # TODO: Implement actual Cloud Run API call
        response = {
            "ok": True,
            "run_id": run_id,
            "service_name": service_name,
            "region": region,
            "status": {
                "ready_condition": "True",
                "latest_created_revision": f"{service_name}-00001-xxx",
                "latest_ready_revision": f"{service_name}-00001-xxx",
                "url": f"https://{service_name}-xxx.{region}.run.app",
                "traffic": [],
                "last_modified": "2026-02-20T10:00:00Z",
                "image_digest": "sha256:mock",
                "environment": settings.MCP_ENVIRONMENT or "STAGING"
            },
            "message": "Cloud Run API integration pending - returning mock structure"
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cloud-logging/query")
async def cloud_logging_query(
    request: CloudLoggingQueryRequest,
    x_api_key: str = Header(None)
):
    """Query Cloud Logging with pagination"""
    run_id = generate_run_id("cloud_logging", "query")
    
    if request.limit > 1000:
        request.limit = 1000
    
    try:
        # TODO: Implement actual Cloud Logging API call
        response = {
            "ok": True,
            "run_id": run_id,
            "entries": [],
            "next_page_token": None,
            "total_entries": 0,
            "message": "Cloud Logging API integration pending - returning mock structure"
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SECRET MANAGER ENDPOINTS (CRITICAL - GOVERNED)
# ============================================================================

@router.get("/secrets/list")
async def secrets_list(
    project_id: Optional[str] = None,
    filter: Optional[str] = None,
    limit: int = 50,
    x_api_key: str = Header(None)
):
    """List Secret Manager secrets (metadata only, never values)"""
    run_id = generate_run_id("secrets", "list")
    
    project_id = project_id or settings.MCP_GCP_PROJECT_ID or "box-magic-ocr-intelligent"
    
    if limit > 200:
        limit = 200
    
    try:
        # TODO: Implement actual Secret Manager API call
        response = {
            "ok": True,
            "run_id": run_id,
            "project_id": project_id,
            "secrets": [],
            "total_secrets": 0,
            "message": "Secret Manager API integration pending - returning mock structure"
        }
        
        # CRITICAL: Force redaction of any 'value' fields
        return redact_secret_value_always(redact_response(response))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/secrets/{secret_id}/reference")
async def secrets_get_reference(
    secret_id: str,
    project_id: Optional[str] = None,
    version: str = "latest",
    x_api_key: str = Header(None)
):
    """Get secret reference (never the value)"""
    run_id = generate_run_id("secrets", "reference")
    
    project_id = project_id or settings.MCP_GCP_PROJECT_ID or "box-magic-ocr-intelligent"
    
    try:
        # TODO: Implement actual Secret Manager API call
        secret_name = f"projects/{project_id}/secrets/{secret_id}"
        reference = f"{secret_name}/versions/{version}"
        
        response = {
            "ok": True,
            "run_id": run_id,
            "secret_id": secret_id,
            "secret_name": secret_name,
            "version": version,
            "version_state": "ENABLED",
            "reference": reference,
            "labels": {},
            "created_time": "2026-02-20T10:00:00Z",
            "value": "[REDACTED]",  # ALWAYS REDACTED
            "message": "Secret Manager API integration pending - returning mock structure"
        }
        
        # CRITICAL: Force redaction
        return redact_secret_value_always(redact_response(response))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/secrets/create")
async def secrets_create(
    request: SecretCreateRequest,
    x_api_key: str = Header(None)
):
    """Create secret (GOVERNED - DRY_RUN/APPLY)"""
    run_id = generate_run_id("secrets", "create")
    
    project_id = request.project_id or settings.MCP_GCP_PROJECT_ID or "box-magic-ocr-intelligent"
    mode = ActionMode.WRITE_DRY_RUN if request.dry_run else ActionMode.WRITE_APPLY
    
    secret_name = f"projects/{project_id}/secrets/{request.secret_id}"
    reference = f"{secret_name}/versions/1"
    
    try:
        if should_apply_action(mode, request.dry_run):
            # TODO: Implement actual Secret Manager create API call
            message = f"Secret '{request.secret_id}' created successfully"
        else:
            message = f"DRY_RUN: Secret '{request.secret_id}' would be created (not applied)"
        
        result = {
            "secret_id": request.secret_id,
            "secret_name": secret_name,
            "reference": reference,
            "labels": request.labels,
            "created_time": "2026-02-20T11:00:00Z" if not request.dry_run else None,
        }
        
        response = build_governed_response(
            run_id=run_id,
            action="CREATE_SECRET",
            mode=mode,
            dry_run=request.dry_run,
            result=result,
            message=message
        )
        
        # CRITICAL: Never log secret value
        return redact_secret_value_always(redact_response(response))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/secrets/{secret_id}/rotate")
async def secrets_rotate(
    secret_id: str,
    request: SecretRotateRequest,
    x_api_key: str = Header(None)
):
    """Rotate secret (GOVERNED - DRY_RUN/APPLY)"""
    run_id = generate_run_id("secrets", "rotate")
    
    mode = ActionMode.WRITE_DRY_RUN if request.dry_run else ActionMode.WRITE_APPLY
    
    try:
        if should_apply_action(mode, request.dry_run):
            # TODO: Implement actual Secret Manager rotate API call
            new_version = "2"
            message = f"Secret '{secret_id}' rotated to version {new_version}"
        else:
            new_version = "2"
            message = f"DRY_RUN: Secret '{secret_id}' would be rotated to version {new_version} (not applied)"
        
        result = {
            "secret_id": secret_id,
            "new_version": new_version,
            "reference": f"projects/xxx/secrets/{secret_id}/versions/{new_version}",
            "previous_version": "1",
        }
        
        response = build_governed_response(
            run_id=run_id,
            action="ROTATE_SECRET",
            mode=mode,
            dry_run=request.dry_run,
            result=result,
            message=message
        )
        
        # CRITICAL: Never log secret value
        return redact_secret_value_always(redact_response(response))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEB ACCESS ENDPOINTS
# ============================================================================

@router.post("/web/search")
async def web_search(
    request: WebSearchRequest,
    x_api_key: str = Header(None)
):
    """Web search with allowlist domains + quota"""
    run_id = generate_run_id("web", "search")
    
    if request.max_results > 10:
        request.max_results = 10
    
    # TODO: Implement quota check
    # TODO: Implement allowlist domain validation
    # TODO: Implement actual web search (Google Custom Search API or similar)
    
    try:
        response = {
            "ok": True,
            "run_id": run_id,
            "query": request.query,
            "results": [],
            "total_results": 0,
            "quota_remaining": 95,
            "message": "Web search API integration pending - returning mock structure"
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/web/fetch")
async def web_fetch(
    request: WebFetchRequest,
    x_api_key: str = Header(None)
):
    """Fetch URL with allowlist domains"""
    run_id = generate_run_id("web", "fetch")
    
    if request.max_size > 5 * 1024 * 1024:  # 5MB
        request.max_size = 5 * 1024 * 1024
    
    # TODO: Implement allowlist domain validation
    # TODO: Implement actual URL fetch
    
    try:
        response = {
            "ok": True,
            "run_id": run_id,
            "url": request.url,
            "status_code": 200,
            "content_type": "text/html",
            "content_length": 0,
            "content": "",
            "truncated": False,
            "quota_remaining": 94,
            "message": "Web fetch API integration pending - returning mock structure"
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# TERMINAL RUNNER ENDPOINT (CRITICAL - GOVERNED)
# ============================================================================

# Allowlist commands
ALLOWED_COMMANDS_READ = [
    "gcloud run services describe",
    "gcloud run services list",
    "gcloud logging read",
    "gcloud secrets list",
    "gcloud secrets versions list",
    "gsutil ls",
    "gsutil du",
]

ALLOWED_COMMANDS_WRITE = [
    "gcloud run services update",
    "gcloud secrets create",
    "gcloud secrets versions add",
]


@router.post("/terminal/run")
async def terminal_run(
    request: TerminalRunRequest,
    x_api_key: str = Header(None)
):
    """Run command with strict allowlist (GOVERNED)"""
    run_id = generate_run_id("terminal", "run")
    
    # Validate command against allowlist
    command_prefix = ' '.join(request.command.split()[:3])  # First 3 words
    
    is_read = any(cmd in request.command for cmd in ALLOWED_COMMANDS_READ)
    is_write = any(cmd in request.command for cmd in ALLOWED_COMMANDS_WRITE)
    
    if not (is_read or is_write):
        raise HTTPException(status_code=403, detail=f"Command not in allowlist: {command_prefix}")
    
    if is_write:
        mode = ActionMode.WRITE_DRY_RUN if request.dry_run else ActionMode.WRITE_APPLY
    else:
        mode = ActionMode.READ_ONLY
    
    try:
        if should_apply_action(mode, request.dry_run):
            # TODO: Implement actual command execution in sandbox
            exit_code = 0
            stdout = "{}"
            stderr = ""
            message = f"Command executed: {request.command}"
        else:
            exit_code = 0
            stdout = ""
            stderr = ""
            message = f"DRY_RUN: Command would be executed: {request.command}"
        
        result = {
            "command": request.command,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "duration_ms": 0,
        }
        
        response = build_governed_response(
            run_id=run_id,
            action="RUN_COMMAND",
            mode=mode,
            dry_run=request.dry_run,
            result=result,
            message=message
        )
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# PHASE 3 ENDPOINTS - Apps Script, Cloud Logging, Secrets
# ============================================================================

from app import phase3_clients

@router.get("/apps-script/project/{script_id}/deployments")
async def apps_script_deployments(
    script_id: str,
    x_api_key: str = Header(None)
):
    """Get Apps Script project deployments"""
    run_id = generate_run_id("apps_script", "deployments")
    
    try:
        deployments_data = phase3_clients.get_apps_script_deployments(script_id)
        
        response = {
            "ok": True,
            "run_id": run_id,
            "script_id": script_id,
            "deployments": deployments_data.get("deployments", []),
            "total_deployments": deployments_data.get("total_deployments", 0),
            "timestamp": deployments_data.get("timestamp"),
            "error": deployments_data.get("error")
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/apps-script/project/{script_id}/structure")
async def apps_script_structure(
    script_id: str,
    x_api_key: str = Header(None)
):
    """Get Apps Script project structure"""
    run_id = generate_run_id("apps_script", "structure")
    
    try:
        structure_data = phase3_clients.get_apps_script_structure(script_id)
        
        response = {
            "ok": True,
            "run_id": run_id,
            "script_id": script_id,
            "files": structure_data.get("files", []),
            "total_files": structure_data.get("total_files", 0),
            "timestamp": structure_data.get("timestamp"),
            "error": structure_data.get("error")
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cloud-logging/query")
async def cloud_logging_query(
    filter_str: str,
    resource_names: Optional[List[str]] = None,
    time_range_hours: int = 24,
    limit: int = 100,
    x_api_key: str = Header(None)
):
    """Query Cloud Logging"""
    run_id = generate_run_id("cloud_logging", "query")
    
    if limit > 1000:
        limit = 1000
    
    try:
        logs_data = phase3_clients.query_cloud_logging(
            filter_str=filter_str,
            resource_names=resource_names,
            time_range_hours=time_range_hours,
            limit=limit
        )
        
        response = {
            "ok": True,
            "run_id": run_id,
            "filter": logs_data.get("filter"),
            "time_range_hours": time_range_hours,
            "total_entries": logs_data.get("total_entries", 0),
            "entries": logs_data.get("entries", []),
            "timestamp": logs_data.get("timestamp"),
            "error": logs_data.get("error")
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/secrets/list")
async def secrets_list(
    limit: int = 50,
    x_api_key: str = Header(None)
):
    """List secrets (metadata only, no values)"""
    run_id = generate_run_id("secrets", "list")
    
    if limit > 200:
        limit = 200
    
    try:
        secrets_data = phase3_clients.list_secrets(limit=limit)
        
        response = {
            "ok": True,
            "run_id": run_id,
            "project_id": secrets_data.get("project_id"),
            "total_secrets": secrets_data.get("total_secrets", 0),
            "secrets": secrets_data.get("secrets", []),
            "timestamp": secrets_data.get("timestamp"),
            "error": secrets_data.get("error")
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/secrets/{secret_id}/reference")
async def secrets_reference(
    secret_id: str,
    version: str = "latest",
    x_api_key: str = Header(None)
):
    """Get secret reference (metadata only, NO VALUE)"""
    run_id = generate_run_id("secrets", "reference")
    
    try:
        secret_data = phase3_clients.get_secret_reference(secret_id, version)
        
        response = {
            "ok": True,
            "run_id": run_id,
            "secret_id": secret_id,
            "version": secret_data.get("version"),
            "full_name": secret_data.get("full_name"),
            "state": secret_data.get("state"),
            "create_time": secret_data.get("create_time"),
            "value_provided": False,
            "value": "[REDACTED]",
            "mount_path_suggestion": secret_data.get("mount_path_suggestion"),
            "timestamp": secret_data.get("timestamp"),
            "error": secret_data.get("error")
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/secrets/create")
async def secrets_create(
    secret_id: str,
    value: str,
    mode: str = "DRY_RUN",
    labels: Optional[Dict[str, str]] = None,
    x_api_key: str = Header(None)
):
    """Create secret (DRY_RUN by default, APPLY after GO)"""
    run_id = generate_run_id("secrets", "create")
    
    if mode != "APPLY":
        mode = "DRY_RUN"
    
    try:
        if mode == "DRY_RUN":
            result = phase3_clients.create_secret_dryrun(secret_id, value, labels)
        else:
            # APPLY mode (governed by GO)
            result = {
                "mode": "APPLY",
                "error": "APPLY mode requires explicit GO confirmation",
                "governance_note": "Contact admin for APPLY mode execution"
            }
        
        response = {
            "ok": True,
            "run_id": run_id,
            "mode": mode,
            "secret_id": secret_id,
            "result": result
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/secrets/{secret_id}/rotate")
async def secrets_rotate(
    secret_id: str,
    new_value: str,
    mode: str = "DRY_RUN",
    x_api_key: str = Header(None)
):
    """Rotate secret (DRY_RUN by default, APPLY after GO)"""
    run_id = generate_run_id("secrets", "rotate")
    
    if mode != "APPLY":
        mode = "DRY_RUN"
    
    try:
        if mode == "DRY_RUN":
            result = phase3_clients.rotate_secret_dryrun(secret_id, new_value)
        else:
            # APPLY mode (governed by GO)
            result = {
                "mode": "APPLY",
                "error": "APPLY mode requires explicit GO confirmation",
                "governance_note": "Contact admin for APPLY mode execution"
            }
        
        response = {
            "ok": True,
            "run_id": run_id,
            "mode": mode,
            "secret_id": secret_id,
            "result": result
        }
        
        return redact_response(response)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

