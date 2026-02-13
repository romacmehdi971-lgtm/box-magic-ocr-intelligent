"""
Logger sécurisé - AUCUNE donnée PII
"""
import logging
import json
import re
from datetime import datetime

class SafeLogger:
    """Logger qui masque automatiquement les données sensibles"""
    
    # Patterns à masquer
    SENSITIVE_PATTERNS = [
        (r'\b\d{16}\b', '****CARD****'),  # Numéro carte
        (r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '****EMAIL****'),  # Email
        (r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b', '****SSN****'),  # SSN-like
        (r'\b\d{2}/\d{2}/\d{4}\b', '****DATE****'),  # Dates
        (r'\bTTC[_\s]+[\d.]+\s*EUR\b', '****AMOUNT****'),  # Montants TTC
        (r'\bIBAN[A-Z0-9\s]{15,34}\b', '****IBAN****'),  # IBAN
    ]
    
    def __init__(self, name, level=logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _sanitize(self, message):
        """Masque les données sensibles"""
        if isinstance(message, dict):
            message = json.dumps(message)
        
        message = str(message)
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        
        return message
    
    def info(self, message, **kwargs):
        """Log info sécurisé"""
        safe_msg = self._sanitize(message)
        self.logger.info(safe_msg, **kwargs)
    
    def warning(self, message, **kwargs):
        """Log warning sécurisé"""
        safe_msg = self._sanitize(message)
        self.logger.warning(safe_msg, **kwargs)
    
    def error(self, message, **kwargs):
        """Log error sécurisé"""
        safe_msg = self._sanitize(message)
        self.logger.error(safe_msg, **kwargs)
    
    def debug(self, message, **kwargs):
        """Log debug sécurisé"""
        safe_msg = self._sanitize(message)
        self.logger.debug(safe_msg, **kwargs)

def get_safe_logger(name):
    """Factory pour créer un SafeLogger"""
    return SafeLogger(name)
