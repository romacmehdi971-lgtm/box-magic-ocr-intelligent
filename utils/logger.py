"""
Logger configuration for OCR Engine
- setup_logger(): logger standard Cloud Run (stdout)
- log_ocr_decision(): ultra-safe, compatible multi signatures
"""

import json
import logging
import sys
from typing import Any, Optional


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Configure a logger for Cloud Run (stdout).
    Avoid handler duplication on reload.
    """
    logger = logging.getLogger(name)

    # Prevent duplicate handlers (Cloud Run reload)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    logger.propagate = False
    return logger


def log_ocr_decision(
    logger: logging.Logger,
    document_id: str,
    level: int,
    *args: Any,
    **kwargs: Any
) -> None:
    """
    Ultra-safe OCR decision logging.

    Supported signatures:
    - Legacy: (logger, document_id, level, decision: str, details: Optional[Any])
    - New:    (logger, document_id, level, confidence: float, needs_next_level: bool)

    Must never break the pipeline.
    """
    try:
        decision = None
        confidence = None
        needs_next_level = None
        details = None

        # Handle kwargs (if used)
        if "decision" in kwargs:
            decision = kwargs.get("decision")
        if "confidence" in kwargs:
            confidence = kwargs.get("confidence")
        if "needs_next_level" in kwargs:
            needs_next_level = kwargs.get("needs_next_level")
        if "details" in kwargs:
            details = kwargs.get("details")

        # Handle positional args
        if len(args) >= 1:
            # If arg0 is str -> legacy decision
            if isinstance(args[0], str):
                decision = args[0]
                if len(args) >= 2:
                    details = args[1]
            else:
                # Otherwise -> new signature confidence/needs_next_level
                confidence = args[0]
                if len(args) >= 2:
                    needs_next_level = args[1]

        # Derive decision if missing
        if decision is None and needs_next_level is not None:
            decision = "CONTINUE" if bool(needs_next_level) else "STOP"

        # Format confidence
        conf_str = ""
        try:
            if confidence is not None:
                conf_str = f" | CONFIDENCE: {float(confidence):.3f}"
        except Exception:
            conf_str = ""

        # Format details
        details_str = ""
        try:
            if details is not None:
                if isinstance(details, (dict, list)):
                    details_str = f" | DETAILS: {json.dumps(details, ensure_ascii=False)}"
                else:
                    details_str = f" | DETAILS: {details}"
        except Exception:
            details_str = ""

        # Final log
        try:
            logger.info(f"[{document_id}] [Level {level}] DECISION: {decision}{conf_str}{details_str}")
        except Exception:
            pass

    except Exception:
        # Ultra safe: never throw
        try:
            logger.info(f"[{document_id}] [Level {level}] DECISION: UNKNOWN")
        except Exception:
            pass
