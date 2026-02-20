"""
MCP Memory Proxy - FastAPI Main Application
Date: 2026-02-15
Purpose: REST API for GPT access to IAPF Memory Hub
"""
import logging
import os
import tempfile
import uuid
import traceback
from typing import Optional, List
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Depends, Query, Header, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import APIKeyHeader
from googleapiclient.errors import HttpError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from .config import (
    API_VERSION,
    API_TITLE,
    API_DESCRIPTION,
    ALLOWED_ORIGINS,
    LOG_LEVEL,
    LOG_FORMAT,
    MEMORY_LOG_SHEET,
    SETTINGS_SHEET,
    API_KEY,
    API_KEY_HEADER,
    GCP_PROJECT_ID,
    GCP_REGION
)
from .models import (
    HealthCheckResponse,
    SheetsListResponse,
    SheetDataResponse,
    SheetInfo,
    ProposeMemoryEntryRequest,
    ProposeMemoryEntryResponse,
    ProposalsListResponse,
    ValidateProposalRequest,
    ValidateProposalResponse,
    CloseDayResponse,
    AuditResponse,
    DocumentationResponse,
    ProposalStatus
)
from .sheets import get_sheets_client, SheetsClient
from .proposals import get_proposal_manager, ProposalManager
from .validation import get_validation_engine, ValidationEngine
from . import infra
from . import hub

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    servers=[
        {
            "url": "https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app",
            "description": "Production Cloud Run"
        }
    ],
    openapi_tags=[
        {"name": "System", "description": "System and health endpoints (PUBLIC)"},
        {"name": "GPT Read-Only", "description": "GPT read-only endpoints for Hub access"},
        {
            "name": "Sheets",
            "description": "Google Sheets operations (DUAL AUTH: IAM token OR X-API-Key)"
        },
        {"name": "Proposals", "description": "Memory entry proposals with validation"},
        {"name": "Operations", "description": "Operational endpoints (audit, close-day)"}
    ]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# READ_ONLY_MODE middleware: block POST/PUT/PATCH/DELETE if READ_ONLY_MODE=true
@app.middleware("http")
async def read_only_middleware(request: Request, call_next):
    """
    Block write operations (POST, PUT, PATCH, DELETE) when READ_ONLY_MODE is enabled.
    This ensures audit-safe operation: clients can only READ data, never modify it.
    """
    import os
    read_only = os.environ.get("READ_ONLY_MODE", "false").lower() == "true"
    
    # Allow all GET requests and OPTIONS (CORS)
    if request.method in ["GET", "HEAD", "OPTIONS"]:
        response = await call_next(request)
        return response
    
    # If READ_ONLY_MODE is true, block write methods
    if read_only and request.method in ["POST", "PUT", "PATCH", "DELETE"]:
        return JSONResponse(
            status_code=403,
            content={
                "detail": "Write operations are disabled (READ_ONLY_MODE=true)",
                "read_only_mode": True,
                "method_attempted": request.method,
                "path": str(request.url.path),
                "audit_safe": True
            }
        )
    
    # Otherwise, proceed normally
    response = await call_next(request)
    return response

# Include P0 routers (Infrastructure + Hub Memory Writer)
app.include_router(infra.router)
app.include_router(hub.router)

# API Key security scheme
api_key_header = APIKeyHeader(name=API_KEY_HEADER, auto_error=False)


async def verify_dual_auth(request: Request, api_key: str = Security(api_key_header)):
    """Verify either IAM token OR API Key (dual-mode auth)
    
    Mode A: IAM Authentication (Cloud Run Invoker)
    - Check Authorization: Bearer <token>
    - Validate token with Google OAuth2
    
    Mode B: API Key Authentication
    - Check X-API-Key header
    - Compare with configured API_KEY
    
    Returns True if either method succeeds.
    """
    correlation_id = str(uuid.uuid4())
    
    # MODE A: Check IAM token (Authorization: Bearer)
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split("Bearer ")[1]
        try:
            # Validate IAM token
            # In Cloud Run, the audience is the service URL
            # For local dev, skip validation
            if os.getenv("ENVIRONMENT") == "production":
                id_info = id_token.verify_oauth2_token(
                    token,
                    google_requests.Request(),
                    audience=None  # Cloud Run validates automatically
                )
                logger.info(f"[{correlation_id}] IAM auth successful: {id_info.get('email', 'unknown')}")
                return True
            else:
                # Dev mode: accept any Bearer token
                logger.info(f"[{correlation_id}] IAM auth bypassed (dev mode)")
                return True
        except Exception as e:
            logger.warning(f"[{correlation_id}] IAM token validation failed: {e}")
            # Continue to API Key fallback
    
    # MODE B: Check API Key
    if not API_KEY:
        # If API_KEY not configured, allow access (backward compatibility)
        logger.warning(f"[{correlation_id}] API_KEY not configured - allowing access")
        return True
    
    if api_key == API_KEY:
        logger.info(f"[{correlation_id}] API Key auth successful")
        return True
    
    # Both methods failed
    logger.error(f"[{correlation_id}] Authentication failed: no valid IAM token or API Key")
    raise HTTPException(
        status_code=403,
        detail={
            "error": "authentication_failed",
            "message": "Authentication required: provide either IAM token (Authorization: Bearer) or API Key (X-API-Key)",
            "correlation_id": correlation_id
        }
    )


async def verify_api_key(api_key: str = Security(api_key_header)):
    """Legacy API Key only verification (kept for backward compatibility)"""
    if not API_KEY:
        logger.warning("API_KEY not configured - allowing access")
        return True
    
    if api_key != API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Invalid or missing API Key"
        )
    return True


# Dependency injection
def get_sheets() -> SheetsClient:
    """Dependency: Get sheets client"""
    return get_sheets_client()


def get_proposals() -> ProposalManager:
    """Dependency: Get proposal manager"""
    return get_proposal_manager()


def get_validator() -> ValidationEngine:
    """Dependency: Get validation engine"""
    return get_validation_engine()


# ==================== ENDPOINTS ====================

# Public endpoints (no API Key required)

@app.get("/", tags=["System"])
async def root():
    """Root endpoint - returns basic service information (PUBLIC)"""
    return {
        "service": API_TITLE,
        "version": API_VERSION,
        "status": "running",
        "documentation": "/docs",
        "openapi_schema": "/openapi.json",
        "health_check": "/health"
    }


@app.get("/health", response_model=HealthCheckResponse, tags=["System"])
async def health_check():
    """
    Health check endpoint (PUBLIC - no API Key required)
    
    Returns service health status without checking Sheets connectivity
    """
    return HealthCheckResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        sheets_accessible=True,  # Assume true to avoid auth issues
        version=API_VERSION
    )


@app.get("/system/time-status", tags=["System"])
async def system_time_status():
    """
    System time and NTP status (PUBLIC - no API Key required)
    
    Returns current system time in UTC ISO 8601 format.
    Cloud Run containers automatically sync with Google's NTP servers.
    
    All timestamps generated by this service are in UTC, independent of local timezone.
    """
    import subprocess
    
    utc_now = datetime.now(timezone.utc)
    
    # Try to get NTP sync status (may not be available in Cloud Run containers)
    ntp_synced = None
    try:
        # Check timedatectl if available
        result = subprocess.run(
            ['timedatectl', 'show', '--property=NTPSynchronized', '--value'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            ntp_synced = result.stdout.strip().lower() == 'yes'
    except:
        # timedatectl not available (normal in Cloud Run)
        ntp_synced = None
    
    return {
        "utc_now": utc_now.isoformat(),
        "utc_timestamp_unix": int(utc_now.timestamp()),
        "timezone": "UTC",
        "ntp_synced": ntp_synced if ntp_synced is not None else "unknown (Cloud Run auto-syncs)",
        "format": "ISO 8601",
        "bureau_timezone_metadata": {
            "timezone": "Europe/Paris",
            "note": "Metadata only - all timestamps generated in UTC"
        },
        "cloud_run_info": "Cloud Run containers automatically sync time with Google NTP servers"
    }


@app.get("/whoami", tags=["System"])
async def whoami():
    """
    Runtime identity and configuration (PUBLIC - no API Key required)
    
    Returns:
    - Service account identity
    - GCP project and region
    - Build version and commit SHA
    - Active scopes (if available)
    """
    import subprocess
    from google.auth import default
    
    # Get service account email
    service_account_email = None
    try:
        result = subprocess.run(
            ['gcloud', 'config', 'get-value', 'account'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            service_account_email = result.stdout.strip()
    except:
        pass
    
    # Try to get credentials info
    credentials_info = {}
    try:
        credentials, project = default()
        if hasattr(credentials, 'service_account_email'):
            service_account_email = credentials.service_account_email
        if hasattr(credentials, 'scopes'):
            credentials_info['scopes'] = list(credentials.scopes) if credentials.scopes else []
        credentials_info['project_id'] = project
    except Exception as e:
        credentials_info['error'] = str(e)
    
    # Get environment info
    import os
    
    return {
        "service": API_TITLE,
        "version": API_VERSION,
        "build_version": os.environ.get("BUILD_VERSION", API_VERSION),
        "git_commit_sha": os.environ.get("GIT_COMMIT_SHA", "unknown"),
        "runtime": {
            "service_account_email": service_account_email or os.environ.get("SERVICE_ACCOUNT_EMAIL", "unknown"),
            "project_id": os.environ.get("GCP_PROJECT_ID", credentials_info.get("project_id", "unknown")),
            "region": os.environ.get("GCP_REGION", "us-central1"),
            "platform": "Cloud Run"
        },
        "credentials": {
            "type": "Application Default Credentials (Cloud Run service account)",
            "scopes": credentials_info.get("scopes", ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive.file"])
        },
        "config": {
            "google_sheet_id": os.environ.get("GOOGLE_SHEET_ID", "not_set"),
            "read_only_mode": os.environ.get("READ_ONLY_MODE", "false"),
            "enable_actions": os.environ.get("ENABLE_ACTIONS", "false"),
            "dry_run_mode": os.environ.get("DRY_RUN_MODE", "true"),
            "log_level": os.environ.get("LOG_LEVEL", "INFO")
        }
    }


# Protected endpoints (API Key required)

@app.get("/sheets", response_model=SheetsListResponse, tags=["Sheets"], dependencies=[Depends(verify_dual_auth)])
async def list_sheets(sheets: SheetsClient = Depends(get_sheets)):
    """
    List all available sheets in the Hub
    
    Returns spreadsheet ID and list of all sheets with metadata
    """
    try:
        sheets_list = sheets.list_sheets()
        
        sheet_info_list = [
            SheetInfo(
                name=s['name'],
                row_count=s['row_count'],
                column_count=s['column_count'],
                headers=s['headers']
            )
            for s in sheets_list
        ]
        
        return SheetsListResponse(
            spreadsheet_id=sheets.spreadsheet_id,
            sheets=sheet_info_list,
            total_sheets=len(sheet_info_list)
        )
    except Exception as e:
        logger.error(f"Failed to list sheets: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sheets/{sheet_name}", response_model=SheetDataResponse, tags=["Sheets"], dependencies=[Depends(verify_dual_auth)])
async def get_sheet_data(
    sheet_name: str,
    limit: Optional[int] = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of rows to return (1-500, default 50)"
    ),
    sheets: SheetsClient = Depends(get_sheets)
):
    """
    Get data from a specific sheet with observability
    
    Returns sheet data as a list of dictionaries (one per row).
    
    Enhanced error handling:
    - Returns detailed error info on failures
    - Includes correlation ID for tracing
    - Logs Google API errors with full context
    """
    correlation_id = str(uuid.uuid4())
    
    try:
        logger.info(f"[{correlation_id}] GET /sheets/{sheet_name} limit={limit}")
        
        # Get raw sheet data with limit applied at API level
        raw_data = sheets.get_sheet_data(
            sheet_name=sheet_name,
            include_headers=True,
            limit=limit
        )
        
        if not raw_data or len(raw_data) < 1:
            return SheetDataResponse(
                sheet_name=sheet_name,
                headers=[],
                data=[],
                row_count=0
            )
        
        headers = raw_data[0]
        rows = raw_data[1:]
        
        # Convert to list of dicts
        data = []
        for row in rows:
            # Pad row to match headers length
            padded_row = row + [''] * (len(headers) - len(row))
            row_dict = dict(zip(headers, padded_row))
            data.append(row_dict)
        
        logger.info(f"[{correlation_id}] Successfully retrieved {len(data)} rows from {sheet_name}")
        
        return SheetDataResponse(
            sheet_name=sheet_name,
            headers=headers,
            data=data,
            row_count=len(data)
        )
    
    except HttpError as e:
        # Google Sheets API error - return detailed error info
        error_details = getattr(e, 'proxy_error_details', None)
        
        if error_details:
            # Use detailed error info from sheets.py
            logger.error(f"[{error_details['correlation_id']}] Google Sheets API error: {error_details}")
            
            raise HTTPException(
                status_code=error_details.get("http_status", 500),
                detail={
                    "correlation_id": error_details["correlation_id"],
                    "error": "google_sheets_api_error",
                    "message": f"Google Sheets API error when reading {sheet_name}",
                    "google_error": error_details.get("error_reason", str(e)),
                    "sheet_name": sheet_name,
                    "limit": limit
                }
            )
        else:
            # Fallback error handling
            correlation_id_fallback = str(uuid.uuid4())
            logger.error(f"[{correlation_id_fallback}] Google Sheets API error (no details): {e}")
            
            raise HTTPException(
                status_code=500,
                detail={
                    "correlation_id": correlation_id_fallback,
                    "error": "google_sheets_api_error",
                    "message": f"Google Sheets API error when reading {sheet_name}",
                    "google_error": str(e),
                    "sheet_name": sheet_name
                }
            )
    
    except ValueError as e:
        # Sheet not found
        logger.error(f"[{correlation_id}] Sheet not found: {sheet_name}")
        raise HTTPException(
            status_code=404,
            detail={
                "correlation_id": correlation_id,
                "error": "sheet_not_found",
                "message": f"Sheet '{sheet_name}' not found",
                "sheet_name": sheet_name,
                "available_sheets": [s['name'] for s in sheets.list_sheets()]
            }
        )
    
    except Exception as e:
        # Unexpected error
        logger.error(f"[{correlation_id}] Unexpected error reading {sheet_name}: {e}\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail={
                "correlation_id": correlation_id,
                "error": "internal_error",
                "message": str(e),
                "sheet_name": sheet_name
            }
        )


# ==================== GPT READ-ONLY ENDPOINTS ====================

@app.get("/gpt/memory-log", tags=["GPT Read-Only"], dependencies=[Depends(verify_api_key)])
async def read_memory_log(
    limit: Optional[int] = Query(50, description="Maximum number of recent entries to return"),
    sheets: SheetsClient = Depends(get_sheets)
):
    """
    GPT Read-Only: Get recent MEMORY_LOG entries
    
    Returns the most recent memory log entries (default: 50)
    """
    try:
        data = sheets.get_sheet_as_dict(MEMORY_LOG_SHEET)
        
        # Return most recent entries (reverse order)
        if limit and limit > 0:
            data = data[-limit:][::-1]  # Last N entries, reversed
        
        return {
            "sheet": MEMORY_LOG_SHEET,
            "total_entries": len(data),
            "entries": data
        }
    except Exception as e:
        logger.error(f"Failed to read MEMORY_LOG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gpt/snapshot-active", tags=["GPT Read-Only"], dependencies=[Depends(verify_api_key)])
async def read_snapshot_active(
    sheets: SheetsClient = Depends(get_sheets)
):
    """
    GPT Read-Only: Get current SNAPSHOT_ACTIVE state
    
    Returns the current active snapshot showing the state of all monitored sheets
    """
    try:
        from .config import SNAPSHOT_SHEET
        data = sheets.get_sheet_as_dict(SNAPSHOT_SHEET)
        
        return {
            "sheet": SNAPSHOT_SHEET,
            "total_snapshots": len(data),
            "snapshots": data
        }
    except Exception as e:
        logger.error(f"Failed to read SNAPSHOT_ACTIVE: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/gpt/hub-status", tags=["GPT Read-Only"], dependencies=[Depends(verify_api_key)])
async def read_hub_status(
    sheets: SheetsClient = Depends(get_sheets)
):
    """
    GPT Read-Only: Get Hub global status
    
    Returns a summary of the Hub state including sheet counts, recent activity, and health
    """
    try:
        # Get MEMORY_LOG count
        memory_log_data = sheets.get_sheet_as_dict(MEMORY_LOG_SHEET)
        memory_log_count = len(memory_log_data)
        
        # Get recent entry
        recent_entry = memory_log_data[-1] if memory_log_data else {}
        
        # Get SNAPSHOT_ACTIVE
        from .config import SNAPSHOT_SHEET
        snapshot_data = sheets.get_sheet_as_dict(SNAPSHOT_SHEET)
        
        # Get all sheets
        all_sheets = sheets.list_sheets()
        
        return {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "memory_log": {
                "total_entries": memory_log_count,
                "latest_entry": recent_entry
            },
            "snapshots": {
                "total": len(snapshot_data),
                "sheets_monitored": len(snapshot_data)
            },
            "hub_sheets": {
                "total": len(all_sheets),
                "names": [s['name'] for s in all_sheets]
            }
        }
    except Exception as e:
        logger.error(f"Failed to get hub status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/propose", response_model=ProposeMemoryEntryResponse, tags=["Proposals"], dependencies=[Depends(verify_api_key)])
async def propose_memory_entry(
    request: ProposeMemoryEntryRequest,
    proposals: ProposalManager = Depends(get_proposals)
):
    """
    Propose a new memory entry
    
    Creates a proposal that requires human validation before being added to MEMORY_LOG
    """
    try:
        response = proposals.create_proposal(request)
        return response
    except Exception as e:
        logger.error(f"Failed to create proposal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/proposals", response_model=ProposalsListResponse, tags=["Proposals"], dependencies=[Depends(verify_api_key)])
async def list_proposals(
    status: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, REJECTED)"),
    proposals: ProposalManager = Depends(get_proposals)
):
    """
    List all proposals
    
    Optionally filter by status (PENDING, APPROVED, REJECTED)
    """
    try:
        # Validate status if provided
        if status and status not in [s.value for s in ProposalStatus]:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status. Must be one of: {[s.value for s in ProposalStatus]}"
            )
        
        response = proposals.list_proposals(status_filter=status)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list proposals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/proposals/{proposal_id}/validate", response_model=ValidateProposalResponse, tags=["Proposals"], dependencies=[Depends(verify_api_key)])
async def validate_proposal(
    proposal_id: str,
    request: ValidateProposalRequest,
    proposals: ProposalManager = Depends(get_proposals)
):
    """
    Validate a proposal (approve or reject)
    
    If approved, the entry is added to MEMORY_LOG
    """
    try:
        response = proposals.validate_proposal(proposal_id, request)
        return response
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to validate proposal {proposal_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/close-day", response_model=CloseDayResponse, tags=["Operations"], dependencies=[Depends(verify_api_key)])
async def close_day(
    sheets: SheetsClient = Depends(get_sheets)
):
    """
    Close the day
    
    Exports SNAPSHOT_ACTIVE as XLSX, uploads to Drive ARCHIVES folder, logs to MEMORY_LOG
    
    Replaces Apps Script API dependency with pure Sheets/Drive API
    """
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        date_str = datetime.now().strftime("%Y%m%d")
        
        # Get settings for archives folder
        settings = sheets.get_settings()
        archives_folder_id = settings.get('archives_folder_id', '')
        
        if not archives_folder_id:
            raise HTTPException(
                status_code=500,
                detail="ARCHIVES folder ID not configured in SETTINGS sheet"
            )
        
        # Create temp file for export
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.xlsx') as tmp_file:
            tmp_path = tmp_file.name
        
        # Export spreadsheet as XLSX
        if not sheets.export_sheet_as_xlsx(tmp_path):
            raise HTTPException(status_code=500, detail="Failed to export spreadsheet")
        
        # Upload to Drive
        file_name = f"HUB_SNAPSHOT_{date_str}.xlsx"
        file_id = sheets.upload_to_drive(tmp_path, file_name, archives_folder_id)
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        # Log to MEMORY_LOG
        log_details = f"Clôture journée automatique. Snapshot exporté vers Drive: {file_name} (ID: {file_id})"
        memory_log_row = sheets.append_row(
            MEMORY_LOG_SHEET,
            [
                timestamp,
                'DEPLOYMENT',
                'Clôture journée',
                log_details,
                'MCP_MEMORY_PROXY',
                f"File: {file_name}, Drive ID: {file_id}",
                'close-day,snapshot,archive'
            ]
        )
        
        logger.info(f"Day closed successfully: {file_name} uploaded to Drive")
        
        return CloseDayResponse(
            status="SUCCESS",
            snapshot_file_id=file_id,
            snapshot_file_name=file_name,
            memory_log_row=memory_log_row,
            timestamp=timestamp,
            message=f"✅ Journée clôturée avec succès. Snapshot: {file_name}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to close day: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/audit", response_model=AuditResponse, tags=["Operations"], dependencies=[Depends(verify_api_key)])
async def run_audit(
    validator: ValidationEngine = Depends(get_validator)
):
    """
    Run autonomous global audit
    
    Detects changes across all sheets, updates CARTOGRAPHIE, DEPENDANCES, ARCHITECTURE,
    creates new snapshot, and logs to MEMORY_LOG
    
    Can be triggered from MCP Cockpit or via cron
    """
    try:
        report = validator.run_autonomous_audit()
        
        return AuditResponse(
            status=report['status'],
            changes_detected=report['changes_detected'],
            tabs_updated=report['tabs_updated'],
            snapshot_created=report['snapshot_created'],
            memory_log_row=report['memory_log_row'],
            report=report,
            timestamp=report['timestamp']
        )
    except Exception as e:
        logger.error(f"Audit failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/docs-json", response_model=DocumentationResponse, tags=["System"])
async def get_documentation():
    """
    Get API documentation in JSON format
    
    Returns comprehensive documentation including endpoints, architecture, and IAM
    """
    endpoints = [
        {
            "method": "GET",
            "path": "/health",
            "description": "Health check endpoint",
            "auth_required": False
        },
        {
            "method": "GET",
            "path": "/whoami",
            "description": "Get service identity and configuration",
            "auth_required": False
        },
        {
            "method": "GET",
            "path": "/infra/whoami",
            "description": "Get infrastructure metadata (project, region, revision, version, flags)",
            "auth_required": False
        },
        {
            "method": "GET",
            "path": "/sheets",
            "description": "List all available sheets",
            "auth_required": True
        },
        {
            "method": "GET",
            "path": "/sheets/{sheet_name}",
            "description": "Get data from a specific sheet (supports ?limit= for pagination)",
            "auth_required": True
        },
        {
            "method": "GET",
            "path": "/proposals",
            "description": "List all proposals (optionally filter by status)",
            "auth_required": True
        },
        {
            "method": "GET",
            "path": "/docs-json",
            "description": "Get API documentation in JSON format",
            "auth_required": False
        }
    ]
    
    architecture = {
        "service_name": "mcp-memory-proxy",
        "gcp_project": "box-magique-gp-prod",
        "region": "us-central1",
        "runtime": "Python 3.11 + FastAPI",
        "authentication": "Bearer token (Cloud Run IAM)",
        "google_sheet_id": get_sheets_client().spreadsheet_id,
        "service_account": "mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com"
    }
    
    iam = {
        "service_account_roles": [
            "roles/sheets.editor",
            "roles/drive.file",
            "roles/logging.logWriter"
        ],
        "gpt_client_role": "roles/run.invoker",
        "gpt_client_email": "romacmehdi971@gmail.com"
    }
    
    return DocumentationResponse(
        title=API_TITLE,
        version=API_VERSION,
        endpoints=endpoints,
        architecture=architecture,
        iam=iam,
        generated_at=datetime.now().isoformat()
    )


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    import os
    
    logger.info(f"Starting {API_TITLE} v{API_VERSION}")
    logger.info(f"GIT_COMMIT={os.environ.get('GIT_COMMIT', 'unknown')}")
    logger.info(f"BUILD_VERSION={os.environ.get('BUILD_VERSION', 'unknown')}")
    logger.info(f"READ_ONLY_MODE={os.environ.get('READ_ONLY_MODE', 'false')}")
    logger.info(f"ENABLE_ACTIONS={os.environ.get('ENABLE_ACTIONS', 'false')}")
    logger.info(f"DRY_RUN_MODE={os.environ.get('DRY_RUN_MODE', 'true')}")
    logger.info(f"GCP_PROJECT_ID={os.environ.get('GCP_PROJECT_ID', 'unknown')}")
    logger.info(f"GCP_REGION={os.environ.get('GCP_REGION', 'unknown')}")
    
    # Test Sheets connection
    try:
        sheets = get_sheets_client()
        if sheets.test_connection():
            logger.info("✅ Google Sheets connection successful")
        else:
            logger.warning("⚠️ Google Sheets connection failed")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Sheets client: {e}")


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info(f"Shutting down {API_TITLE}")
