"""Logger configuration for OCR Engine"""

import logging
import sys
from datetime import datetime


def setup_logger(name: str, level: str = 'INFO') -> logging.Logger:
    """
    Configure un logger pour le système OCR
    
    Args:
        name: Nom du logger
        level: Niveau de log (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Logger configuré
    """
    logger = logging.getLogger(name)
    
    # Éviter duplication si déjà configuré
    if logger.handlers:
        return logger
    
    # Niveau
    log_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(log_level)
    
    # Format
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


def log_ocr_decision(logger: logging.Logger, document_id: str, level: int, decision: str):
    """
    Log une décision OCR de manière structurée
    
    Args:
        logger: Logger à utiliser
        document_id: ID du document
        level: Niveau OCR (1, 2, 3)
        decision: Description de la décision
    """
    logger.info(f"[{document_id}] [Level {level}] DECISION: {decision}")