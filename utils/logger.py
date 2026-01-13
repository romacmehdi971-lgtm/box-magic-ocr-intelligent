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
    decision: str,
    details: Optional[Any] = None,
) -> None:
    """
    Log une décision OCR de manière structurée.

    Compatibilité :
    - Signature historique : (logger, document_id, level, decision)
    - Signature tolérante : (logger, document_id, level, decision, details)

    Args:
        logger: Logger à utiliser
        document_id: ID du document
        level: Niveau OCR (1, 2, 3)
        decision: Description de la décision
        details: Détails optionnels (dict/str/obj) pour enrichir les logs
    """
    try:
        if details is None:
            logger.info(f"[{document_id}] [Level {level}] DECISION: {decision}")
        else:
            logger.info(f"[{document_id}] [Level {level}] DECISION: {decision} | DETAILS: {details}")
    except Exception:
        # Ultra-safe : ne jamais casser le pipeline à cause d'un log
        try:
            logger.info(f"[{document_id}] [Level {level}] DECISION: {decision}")
        except Exception:
            pass
