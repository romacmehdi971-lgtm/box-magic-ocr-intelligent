"""
MCP Memory Proxy - FastAPI Main Application
Date: 2026-02-15
Purpose: REST API for GPT access to IAPF Memory Hub
"""
import logging
import os
import tempfile
from typing import Optional, List
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import (
    API_VERSION,
    API_TITLE,
    API_DESCRIPTION,
    ALLOWED_ORIGINS,
    LOG_LEVEL,
    LOG_FORMAT,
    MEMORY_LOG_SHEET,
    SETTINGS_SHEET
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
    version=API_VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

@app.get("/health", response_model=HealthCheckResponse, tags=["System"])
async def health_check(sheets: SheetsClient = Depends(get_sheets)):
    """
    Health check endpoint
    
    Returns service health status and Google Sheets connectivity
    """
    sheets_accessible = sheets.test_connection()
    
    return HealthCheckResponse(
        status="healthy" if sheets_accessible else "degraded",
        timestamp=datetime.now().isoformat(),
        sheets_accessible=sheets_accessible,
        version=API_VERSION
    )


@app.get("/sheets", response_model=SheetsListResponse, tags=["Sheets"])
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


@app.get("/sheets/{sheet_name}", response_model=SheetDataResponse, tags=["Sheets"])
async def get_sheet_data(
    sheet_name: str,
    limit: Optional[int] = Query(None, description="Maximum number of rows to return"),
    sheets: SheetsClient = Depends(get_sheets)
):
    """
    Get data from a specific sheet
    
    Returns sheet data as a list of dictionaries (one per row)
    """
    try:
        data = sheets.get_sheet_as_dict(sheet_name)
        
        # Apply limit if specified
        if limit is not None and limit > 0:
            data = data[:limit]
        
        # Get headers
        headers = sheets.get_headers(sheet_name)
        
        return SheetDataResponse(
            sheet_name=sheet_name,
            headers=headers,
            data=data,
            row_count=len(data)
        )
    except Exception as e:
        logger.error(f"Failed to get sheet data for {sheet_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/propose", response_model=ProposeMemoryEntryResponse, tags=["Proposals"])
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


@app.get("/proposals", response_model=ProposalsListResponse, tags=["Proposals"])
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


@app.post("/proposals/{proposal_id}/validate", response_model=ValidateProposalResponse, tags=["Proposals"])
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


@app.post("/close-day", response_model=CloseDayResponse, tags=["Operations"])
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


@app.post("/audit", response_model=AuditResponse, tags=["Operations"])
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
            "path": "/sheets",
            "description": "List all available sheets",
            "auth_required": True
        },
        {
            "method": "GET",
            "path": "/sheets/{sheet_name}",
            "description": "Get data from a specific sheet",
            "auth_required": True
        },
        {
            "method": "POST",
            "path": "/propose",
            "description": "Propose a new memory entry (requires human validation)",
            "auth_required": True
        },
        {
            "method": "GET",
            "path": "/proposals",
            "description": "List all proposals (optionally filter by status)",
            "auth_required": True
        },
        {
            "method": "POST",
            "path": "/proposals/{proposal_id}/validate",
            "description": "Validate (approve/reject) a proposal",
            "auth_required": True
        },
        {
            "method": "POST",
            "path": "/close-day",
            "description": "Close the day (export snapshot, upload to Drive, log)",
            "auth_required": True
        },
        {
            "method": "POST",
            "path": "/audit",
            "description": "Run autonomous global audit",
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
    logger.info(f"Starting {API_TITLE} v{API_VERSION}")
    
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


# Root endpoint
@app.get("/", tags=["System"])
async def root():
    """Root endpoint - returns basic service information"""
    return {
        "service": API_TITLE,
        "version": API_VERSION,
        "status": "running",
        "documentation": "/docs",
        "health_check": "/health"
    }
