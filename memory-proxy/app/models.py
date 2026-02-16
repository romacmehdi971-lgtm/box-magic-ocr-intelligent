"""
MCP Memory Proxy - Data Models
Date: 2026-02-15
Purpose: Pydantic models for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class ProposalStatus(str, Enum):
    """Proposal status enumeration"""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class MemoryEntryType(str, Enum):
    """Memory entry type enumeration"""
    DECISION = "DECISION"
    RULE = "RULE"
    CONFLICT = "CONFLICT"
    ARCHITECTURE = "ARCHITECTURE"
    AUDIT = "AUDIT"
    DEPLOYMENT = "DEPLOYMENT"
    OTHER = "OTHER"


class HealthCheckResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service health status")
    timestamp: str = Field(..., description="Current timestamp")
    sheets_accessible: bool = Field(..., description="Google Sheets accessibility")
    version: str = Field(..., description="API version")


class SheetInfo(BaseModel):
    """Sheet information"""
    name: str = Field(..., description="Sheet tab name")
    row_count: int = Field(..., description="Number of rows")
    column_count: int = Field(..., description="Number of columns")
    headers: List[str] = Field(default_factory=list, description="Column headers")


class SheetsListResponse(BaseModel):
    """Response for listing all sheets"""
    spreadsheet_id: str = Field(..., description="Google Spreadsheet ID")
    sheets: List[SheetInfo] = Field(..., description="List of sheets")
    total_sheets: int = Field(..., description="Total number of sheets")


class SheetDataResponse(BaseModel):
    """Response for sheet data retrieval"""
    sheet_name: str = Field(..., description="Sheet name")
    headers: List[str] = Field(..., description="Column headers")
    data: List[Dict[str, Any]] = Field(..., description="Sheet data as list of dicts")
    row_count: int = Field(..., description="Number of data rows")


class ProposeMemoryEntryRequest(BaseModel):
    """Request to propose a new memory entry"""
    entry_type: MemoryEntryType = Field(..., description="Type of memory entry")
    title: str = Field(..., min_length=5, max_length=200, description="Entry title")
    details: str = Field(..., min_length=10, description="Entry details/description")
    source: str = Field(default="GPT", description="Source of the entry")
    tags: List[str] = Field(default_factory=list, description="Optional tags")


class ProposeMemoryEntryResponse(BaseModel):
    """Response after proposing a memory entry"""
    proposal_id: str = Field(..., description="Unique proposal ID")
    status: str = Field(..., description="Proposal status")
    message: str = Field(..., description="Human-readable message")
    validation_required: bool = Field(default=True, description="Whether human validation is required")
    created_at: str = Field(..., description="Proposal creation timestamp")


class ProposalItem(BaseModel):
    """Proposal item for listing"""
    proposal_id: str
    entry_type: str
    title: str
    details: str
    source: str
    status: str
    created_at: str
    tags: List[str] = Field(default_factory=list)


class ProposalsListResponse(BaseModel):
    """Response for listing proposals"""
    proposals: List[ProposalItem] = Field(..., description="List of proposals")
    total_pending: int = Field(..., description="Total pending proposals")


class ValidateProposalRequest(BaseModel):
    """Request to validate (approve/reject) a proposal"""
    action: str = Field(..., pattern="^(approve|reject)$", description="Action: approve or reject")
    comment: Optional[str] = Field(None, description="Optional validation comment")
    validator: str = Field(..., description="Name/email of validator")


class ValidateProposalResponse(BaseModel):
    """Response after validating a proposal"""
    proposal_id: str = Field(..., description="Proposal ID")
    action: str = Field(..., description="Action taken")
    status: str = Field(..., description="New status")
    memory_log_row: Optional[int] = Field(None, description="Row number in MEMORY_LOG if approved")
    message: str = Field(..., description="Human-readable message")


class CloseDayResponse(BaseModel):
    """Response after closing the day"""
    status: str = Field(..., description="Closure status")
    snapshot_file_id: str = Field(..., description="Drive file ID of the snapshot")
    snapshot_file_name: str = Field(..., description="Snapshot file name")
    memory_log_row: int = Field(..., description="Row number in MEMORY_LOG")
    timestamp: str = Field(..., description="Closure timestamp")
    message: str = Field(..., description="Human-readable message")


class AuditResponse(BaseModel):
    """Response after running autonomous audit"""
    status: str = Field(..., description="Audit status")
    changes_detected: int = Field(..., description="Number of changes detected")
    tabs_updated: List[str] = Field(..., description="List of tabs updated")
    snapshot_created: bool = Field(..., description="Whether a new snapshot was created")
    memory_log_row: int = Field(..., description="Row number in MEMORY_LOG")
    report: Dict[str, Any] = Field(..., description="Detailed audit report")
    timestamp: str = Field(..., description="Audit timestamp")


class DocumentationResponse(BaseModel):
    """Response for documentation endpoint"""
    title: str = Field(..., description="Documentation title")
    version: str = Field(..., description="API version")
    endpoints: List[Dict[str, Any]] = Field(..., description="List of available endpoints")
    architecture: Dict[str, Any] = Field(..., description="Architecture details")
    iam: Dict[str, Any] = Field(..., description="IAM configuration")
    generated_at: str = Field(..., description="Documentation generation timestamp")
