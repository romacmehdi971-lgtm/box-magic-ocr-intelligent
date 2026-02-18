"""
MCP Memory Proxy - Hub Memory Writer (P0)
Date: 2026-02-18
Purpose: STRICT memory log writer with format governance
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Literal
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, validator

from .sheets import get_sheets_client, SheetsClient
from .config import MEMORY_LOG_SHEET

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/hub", tags=["Hub Memory"])


# ==================== MODELS ====================

# Strict type enum
MemoryLogType = Literal[
    "STATUS",
    "DECISION",
    "CONSTATS",
    "NEXT_STEP",
    "ARCHITECTURE",
    "INCIDENT",
    "RISK"
]


class MemoryLogWriteRequest(BaseModel):
    """Strict request for memory log write"""
    type: MemoryLogType = Field(..., description="Entry type (STATUS|DECISION|CONSTATS|NEXT_STEP|ARCHITECTURE|INCIDENT|RISK)")
    title: str = Field(..., min_length=1, max_length=200, description="Entry title (1-200 chars)")
    details: str = Field(..., min_length=1, description="Entry details")
    tags: str = Field(..., min_length=1, description="Tags separated by semicolons (e.g., 'tag1;tag2;tag3')")
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags format"""
        if not v:
            raise ValueError("Tags cannot be empty")
        
        # Check for semicolon separator
        if ';' not in v and ',' in v:
            raise ValueError("Tags must be separated by semicolons (;), not commas")
        
        # Split and validate
        tags_list = [t.strip() for t in v.split(';') if t.strip()]
        if not tags_list:
            raise ValueError("At least one tag is required")
        
        # Check for invalid characters in tags
        for tag in tags_list:
            if '\t' in tag or '\n' in tag:
                raise ValueError(f"Tag '{tag}' contains invalid characters (tabs or newlines)")
        
        return v
    
    @validator('title', 'details')
    def validate_no_tabs_newlines(cls, v):
        """Validate no tabs or newlines in title/details (breaks TSV format)"""
        if '\t' in v or '\n' in v:
            raise ValueError("Title and details cannot contain tabs or newlines")
        return v


class MemoryLogWriteResponse(BaseModel):
    """Response for memory log write"""
    status: str = "OK"
    ts_iso: str
    row_index: int
    correlation_id: str


# ==================== ENDPOINTS ====================

def get_sheets() -> SheetsClient:
    """Dependency: Get sheets client"""
    return get_sheets_client()


@router.post("/memory_log/write", response_model=MemoryLogWriteResponse)
async def write_memory_log(
    request: MemoryLogWriteRequest,
    sheets: SheetsClient = Depends(get_sheets)
):
    """
    Write MEMORY_LOG entry (STRICT format governance)
    
    ANTI-ERROR FORMAT:
    - Auto-generates ts_iso (UTC now)
    - Auto-sets author = "ORION"
    - Auto-sets source = "MCP"
    - Validates type (must be in allowed list)
    - Rejects if column injection detected
    - Rejects if format violation detected
    
    Format: ts_iso\ttype\ttitle\tdetails\tauthor\tsource\ttags
    
    Returns:
    - status: "OK"
    - ts_iso: Generated timestamp
    - row_index: Row number in sheet
    - correlation_id: Request correlation ID
    """
    correlation_id = str(uuid.uuid4())
    logger.info(f"[{correlation_id}] POST /hub/memory_log/write: type={request.type}, title={request.title}")
    
    try:
        # Generate timestamp (UTC ISO 8601)
        ts_iso = datetime.now(timezone.utc).isoformat()
        
        # Set fixed values
        author = "ORION"
        source = "MCP"
        
        # Validate no column injection
        forbidden_chars = ['\t', '\n', '\r']
        fields_to_check = [request.title, request.details, request.tags]
        
        for field in fields_to_check:
            for char in forbidden_chars:
                if char in field:
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "correlation_id": correlation_id,
                            "error": "column_injection_detected",
                            "message": f"Field contains forbidden character: {repr(char)}",
                            "hint": "Remove tabs, newlines, or carriage returns from your input"
                        }
                    )
        
        # Build row (STRICT column order)
        row = [
            ts_iso,         # Column A: ts_iso
            request.type,   # Column B: type
            request.title,  # Column C: title
            request.details,  # Column D: details
            author,         # Column E: author
            source,         # Column F: source
            request.tags    # Column G: tags
        ]
        
        # Append to sheet
        try:
            row_index = sheets.append_row(MEMORY_LOG_SHEET, row)
            logger.info(f"[{correlation_id}] Memory log written successfully: row {row_index}, type={request.type}")
            
            return MemoryLogWriteResponse(
                status="OK",
                ts_iso=ts_iso,
                row_index=row_index,
                correlation_id=correlation_id
            )
        
        except Exception as append_error:
            logger.error(f"[{correlation_id}] Failed to append row to MEMORY_LOG: {append_error}")
            raise HTTPException(
                status_code=500,
                detail={
                    "correlation_id": correlation_id,
                    "error": "sheet_append_failed",
                    "message": str(append_error)
                }
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{correlation_id}] Memory log write failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "correlation_id": correlation_id,
                "error": "memory_log_write_failed",
                "message": str(e)
            }
        )
