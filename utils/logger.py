"""Logger configuration for OCR Engine"""

import logging
import sys
from typing import Any, Optional


def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Configure un logger pour le système OCR.

    Objectifs :
    - Sortie console compatible Cloud Run
    - Pas de duplication de handlers (reload)
    - Niveau paramétrable

    Args:
        name: Nom du logger
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Logger configuré
    """
    logger = logging.getLogger(name)

    # Evite la duplication de handlers en cas de reload Cloud Run
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, str(level).upper(), logging.INFO))

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Console handler (Cloud Run logs)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    logger.propagate = False
    return logger


def log_ocr_decision(
    logger: logging.Logger,
    document_id: str,
    level: int,
    confidence: float,
    needs_next_level: bool,
) -> None:
    """
    Log une décision OCR de manière structurée.

    Args:
        logger: Logger à utiliser
        document_id: ID du document
        level: Niveau OCR (1, 2, 3)
        confidence: Score de confiance (0.0 à 1.0)
        needs_next_level: Si vrai, le niveau suivant est nécessaire
    """
    try:
        decision = "CONTINUE" if needs_next_level else "STOP"
        logger.info(
            f"[{document_id}] [Level {level}] DECISION: {decision} "
            f"| CONFIDENCE: {confidence:.2f}"
        )
    except Exception:
        # Ultra-safe : ne jamais casser le pipeline à cause d'un log
        try:
            logger.info(f"[{document_id}] [Level {level}] Confidence: {confidence}")
        except Exception:
            pass
