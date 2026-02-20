"""
Governance module for Phase 2 MCP
Handles run_id generation, logging, DRY_RUN/APPLY modes
"""

import time
import random
import string
from typing import Dict, Any, Optional
from enum import Enum


class ActionMode(str, Enum):
    READ_ONLY = "READ_ONLY"
    WRITE_DRY_RUN = "WRITE_DRY_RUN"
    WRITE_APPLY = "WRITE_APPLY"


def generate_run_id(domain: str, action: str) -> str:
    """
    Generate unique run_id
    Format: {domain}_{action}_{timestamp}_{random6}
    """
    timestamp = int(time.time())
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"{domain}_{action}_{timestamp}_{random_suffix}"


def should_apply_action(mode: ActionMode, dry_run: bool) -> bool:
    """Determine if action should be applied"""
    if mode == ActionMode.READ_ONLY:
        return True  # Read actions always apply
    elif mode == ActionMode.WRITE_DRY_RUN or dry_run:
        return False  # Dry run = no apply
    elif mode == ActionMode.WRITE_APPLY and not dry_run:
        return True  # Apply only if explicitly requested
    return False


def build_governed_response(
    run_id: str,
    action: str,
    mode: ActionMode,
    dry_run: bool,
    result: Dict[str, Any],
    message: Optional[str] = None
) -> Dict[str, Any]:
    """Build standardized governed response"""
    response = {
        "ok": True,
        "run_id": run_id,
        "action": action,
        "mode": mode.value,
        "dry_run": dry_run,
    }
    
    if message:
        response["message"] = message
    elif dry_run:
        response["message"] = f"DRY_RUN: Action '{action}' simulated (not applied)"
    
    # Add to_apply hint for DRY_RUN
    if dry_run:
        response["to_apply"] = {
            "set_dry_run_false": True,
            "confirm_action": action
        }
    
    # Merge result data
    response.update(result)
    
    return response


def validate_quota(
    quota_key: str,
    max_quota: int,
    current_count: int = 0
) -> tuple[bool, Optional[str]]:
    """Validate quota limits"""
    if current_count >= max_quota:
        return False, f"Quota exceeded for {quota_key}: {current_count}/{max_quota}"
    return True, None


def build_memory_log_entry(
    run_id: str,
    domain: str,
    action: str,
    mode: ActionMode,
    params: Dict[str, Any],
    result_summary: str
) -> Dict[str, Any]:
    """Build MEMORY_LOG entry payload"""
    entry_type = "DECISION" if mode == ActionMode.WRITE_APPLY else "CONSTAT"
    mode_label = "[APPLIED]" if mode == ActionMode.WRITE_APPLY else f"[{mode.value}]"
    
    return {
        "type": entry_type,
        "title": f"MCP {domain} — {action} {mode_label}",
        "details": f"run_id={run_id}, params={str(params)[:100]}, result={result_summary}",
        "source": "MCP_ACTIONS_EXTENDED",
        "tags": f"MCP;{domain.upper()};{action.upper()};{mode.value}"
    }
