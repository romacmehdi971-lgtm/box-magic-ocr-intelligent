"""
BOX MAGIC OCR INTELLIGENT
Version 1.0.0

OCR Engine intelligent à 3 niveaux pour traitement documentaire automatisé.
"""

__version__ = "1.0.0"
__author__ = "BOX MAGIC 2026 - IA PROCESS FACTORY"

from .ocr_engine import OCREngine, OCRResult, FieldValue, ProcessingContext

__all__ = [
    'OCREngine',
    'OCRResult',
    'FieldValue',
    'ProcessingContext',
    '__version__'
]
