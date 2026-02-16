"""
MCP Memory Proxy - Proposal Management
Date: 2026-02-15
Purpose: Manage memory entry proposals with human validation workflow
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .sheets import get_sheets_client
from .config import PROPOSITIONS_PENDING_SHEET, MEMORY_LOG_SHEET, PROPOSAL_ID_PREFIX
from .models import (
    ProposeMemoryEntryRequest,
    ProposeMemoryEntryResponse,
    ProposalItem,
    ProposalsListResponse,
    ValidateProposalRequest,
    ValidateProposalResponse,
    ProposalStatus
)

logger = logging.getLogger(__name__)


class ProposalManager:
    """Manages memory entry proposals"""
    
    def __init__(self):
        self.sheets_client = get_sheets_client()
    
    def generate_proposal_id(self) -> str:
        """Generate a unique proposal ID"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"{PROPOSAL_ID_PREFIX}-{timestamp}"
    
    def create_proposal(self, request: ProposeMemoryEntryRequest) -> ProposeMemoryEntryResponse:
        """Create a new memory entry proposal"""
        try:
            proposal_id = self.generate_proposal_id()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Check for duplicates
            existing_proposals = self.sheets_client.get_sheet_as_dict(PROPOSITIONS_PENDING_SHEET)
            for prop in existing_proposals:
                if (prop.get('title', '').strip().lower() == request.title.strip().lower() and
                    prop.get('status', '') == ProposalStatus.PENDING.value):
                    logger.warning(f"Duplicate proposal detected for title: {request.title}")
                    return ProposeMemoryEntryResponse(
                        proposal_id=prop.get('proposal_id', ''),
                        status=ProposalStatus.PENDING.value,
                        message=f"⚠️ Une proposition similaire existe déjà (ID: {prop.get('proposal_id', '')}). Validation humaine requise.",
                        validation_required=True,
                        created_at=prop.get('created_at', '')
                    )
            
            # Prepare row data
            tags_str = ', '.join(request.tags) if request.tags else ''
            row_data = [
                proposal_id,
                timestamp,
                request.entry_type.value,
                request.title,
                request.details,
                request.source,
                tags_str,
                ProposalStatus.PENDING.value,
                '',  # validator
                '',  # validation_timestamp
                ''   # validation_comment
            ]
            
            # Append to PROPOSITIONS_PENDING sheet
            self.sheets_client.append_row(PROPOSITIONS_PENDING_SHEET, row_data)
            
            logger.info(f"Created proposal {proposal_id} for entry type {request.entry_type.value}")
            
            return ProposeMemoryEntryResponse(
                proposal_id=proposal_id,
                status=ProposalStatus.PENDING.value,
                message=f"✅ Proposition créée avec succès. ID: {proposal_id}. En attente de validation humaine.",
                validation_required=True,
                created_at=timestamp
            )
        except Exception as e:
            logger.error(f"Failed to create proposal: {e}")
            raise
    
    def list_proposals(self, status_filter: Optional[str] = None) -> ProposalsListResponse:
        """List all proposals, optionally filtered by status"""
        try:
            proposals_data = self.sheets_client.get_sheet_as_dict(PROPOSITIONS_PENDING_SHEET)
            
            proposals = []
            pending_count = 0
            
            for row in proposals_data:
                proposal_status = row.get('status', '')
                
                # Apply status filter if provided
                if status_filter and proposal_status != status_filter:
                    continue
                
                # Count pending proposals
                if proposal_status == ProposalStatus.PENDING.value:
                    pending_count += 1
                
                # Parse tags
                tags_str = row.get('tags', '')
                tags = [t.strip() for t in tags_str.split(',') if t.strip()] if tags_str else []
                
                proposal = ProposalItem(
                    proposal_id=row.get('proposal_id', ''),
                    entry_type=row.get('entry_type', ''),
                    title=row.get('title', ''),
                    details=row.get('details', ''),
                    source=row.get('source', ''),
                    status=proposal_status,
                    created_at=row.get('created_at', ''),
                    tags=tags
                )
                proposals.append(proposal)
            
            logger.info(f"Listed {len(proposals)} proposals ({pending_count} pending)")
            
            return ProposalsListResponse(
                proposals=proposals,
                total_pending=pending_count
            )
        except Exception as e:
            logger.error(f"Failed to list proposals: {e}")
            raise
    
    def get_proposal_by_id(self, proposal_id: str) -> Optional[Dict[str, Any]]:
        """Get a proposal by its ID"""
        try:
            proposals_data = self.sheets_client.get_sheet_as_dict(PROPOSITIONS_PENDING_SHEET)
            
            for idx, row in enumerate(proposals_data, start=2):  # Start at 2 (skip header)
                if row.get('proposal_id', '') == proposal_id:
                    return {
                        'row_number': idx,
                        'data': row
                    }
            
            return None
        except Exception as e:
            logger.error(f"Failed to get proposal {proposal_id}: {e}")
            raise
    
    def validate_proposal(self, proposal_id: str, request: ValidateProposalRequest) -> ValidateProposalResponse:
        """Validate (approve or reject) a proposal"""
        try:
            # Get the proposal
            proposal = self.get_proposal_by_id(proposal_id)
            
            if not proposal:
                raise ValueError(f"Proposal {proposal_id} not found")
            
            proposal_data = proposal['data']
            row_number = proposal['row_number']
            
            # Check if already validated
            if proposal_data.get('status', '') != ProposalStatus.PENDING.value:
                return ValidateProposalResponse(
                    proposal_id=proposal_id,
                    action=request.action,
                    status=proposal_data.get('status', ''),
                    message=f"⚠️ Cette proposition a déjà été {proposal_data.get('status', '').lower()}."
                )
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            memory_log_row = None
            
            if request.action == "approve":
                # Append to MEMORY_LOG
                memory_log_data = [
                    timestamp,
                    proposal_data.get('entry_type', ''),
                    proposal_data.get('title', ''),
                    proposal_data.get('details', ''),
                    proposal_data.get('source', ''),
                    f"Validated by {request.validator}",
                    proposal_data.get('tags', '')
                ]
                
                memory_log_row = self.sheets_client.append_row(MEMORY_LOG_SHEET, memory_log_data)
                
                new_status = ProposalStatus.APPROVED.value
                message = f"✅ Proposition approuvée et ajoutée à MEMORY_LOG (ligne {memory_log_row})."
            else:
                new_status = ProposalStatus.REJECTED.value
                message = f"❌ Proposition rejetée. Raison: {request.comment or 'Non spécifiée'}"
            
            # Update proposal status
            updated_row = [
                proposal_data.get('proposal_id', ''),
                proposal_data.get('created_at', ''),
                proposal_data.get('entry_type', ''),
                proposal_data.get('title', ''),
                proposal_data.get('details', ''),
                proposal_data.get('source', ''),
                proposal_data.get('tags', ''),
                new_status,
                request.validator,
                timestamp,
                request.comment or ''
            ]
            
            self.sheets_client.update_row(PROPOSITIONS_PENDING_SHEET, row_number, updated_row)
            
            logger.info(f"Validated proposal {proposal_id}: {request.action}")
            
            return ValidateProposalResponse(
                proposal_id=proposal_id,
                action=request.action,
                status=new_status,
                memory_log_row=memory_log_row,
                message=message
            )
        except Exception as e:
            logger.error(f"Failed to validate proposal {proposal_id}: {e}")
            raise


# Global instance
_proposal_manager: Optional[ProposalManager] = None


def get_proposal_manager() -> ProposalManager:
    """Get or create the global ProposalManager instance"""
    global _proposal_manager
    if _proposal_manager is None:
        _proposal_manager = ProposalManager()
    return _proposal_manager
