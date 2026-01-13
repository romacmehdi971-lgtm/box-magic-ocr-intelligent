#!/usr/bin/env python3
"""
BOX MAGIC OCR ENGINE - Point d'entrée principal
Architecture 3 niveaux : Rapide → Approfondi → Mémoire
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml

from levels.ocr_level1 import OCRLevel1
from levels.ocr_level2 import OCRLevel2
from levels.ocr_level3 import OCRLevel3
from memory.ai_memory import AIMemory
from connectors.google_sheets import GoogleSheetsConnector
from connectors.document_loader import DocumentLoader
from utils.logger import setup_logger, log_ocr_decision
from utils.validators import validate_ocr_result
from utils.document_types import DocumentType


# ======================================================================
# DATA MODELS
# ======================================================================

@dataclass
class FieldValue:
    value: any
    confidence: float
    extraction_method: Optional[str] = None
    position: Optional[dict] = None
    pattern: Optional[str] = None


@dataclass
class OCRResult:
    """Résultat complet d'un traitement OCR"""
    document_id: str
    document_type: str
    level: int  # 1, 2 ou 3
    confidence: float  # 0.0 à 1.0
    entreprise_source: str
    fields: Dict[str, FieldValue]
    processing_date: datetime
    text: str = ""  # ✅ TEXTE OCR BRUT (PHASE 2.1)
    needs_next_level: bool = False
    improved_fields: Optional[List[str]] = None
    corrections: Optional[List[str]] = None
    rule_created: Optional[dict] = None
    logs: List[str] = field(default_factory=list)

    def to_dict(self):
        """Convertit en dictionnaire"""
        result = asdict(self)
        result['processing_date'] = self.processing_date.isoformat()
        result['text_length'] = len(self.text or "")
        return result


@dataclass
class ProcessingContext:
    source_entreprise: str
    entreprise_config: dict
    options: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


# ======================================================================
# OCR ENGINE
# ======================================================================

class OCREngine:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.logger = setup_logger("OCREngine", self.config.get('log_level', 'INFO'))

        self.ocr_level1 = OCRLevel1(self.config)
        self.ocr_level2 = OCRLevel2(self.config)
        self.ocr_level3 = OCRLevel3(self.config)

        self.document_loader = DocumentLoader(self.config)
        self.memory = AIMemory(self.config.get('memory_store_path', 'memory/rules.json'))
        self.sheets_connector = self._init_sheets_connector()

    def _load_config(self, config_path: str) -> dict:
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logging.warning(f"Config load warning: {e}")
        return {}

    def _init_sheets_connector(self):
        try:
            if self.config.get('google_sheets', {}).get('enabled', False):
                return GoogleSheetsConnector(self.config)
        except Exception as e:
            self.logger.warning(f"Sheets connector init warning: {e}")
        return None

    def _prepare_context(self, source_entreprise: str, options: dict) -> ProcessingContext:
        entreprise_config = self.config.get('entreprises', {}).get(source_entreprise, {})
        return ProcessingContext(
            source_entreprise=source_entreprise,
            entreprise_config=entreprise_config,
            options=options or {}
        )

    def process_document(self,
                         file_path: str,
                         source_entreprise: str,
                         options: Optional[dict] = None) -> OCRResult:
        """
        Process a document with progressive OCR (levels 1-3)
        """
        options = options or {}

        document_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{Path(file_path).stem}"
        self.logger.info(f"[{document_id}] Starting OCR processing")
        self.logger.info(f"[{document_id}] File: {file_path}")

        try:
            # 1. Chargement du document
            document = self.document_loader.load(file_path)
            self.logger.info(f"[{document_id}] Document loaded successfully")

            # ✅ TEXTE OCR BRUT (PHASE 2.1)
            raw_text = document.get_text() or ""

            # 2. Préparation contexte
            context = self._prepare_context(source_entreprise, options)

            # 3. Détection entreprise source si auto
            if source_entreprise == 'auto-detect':
                detected = self.ocr_level1.detect_entreprise_source(document, context)
                context.source_entreprise = detected
                context.entreprise_config = self.config.get('entreprises', {}).get(detected, {})

            # 4. Vérification règles mémoire (si disponible)
            matching_rule = self.memory.find_matching_rule(document, context)
            if matching_rule and not options.get('force_full_ocr'):
                result = self._apply_memory_rule(document, matching_rule, context, document_id)
            else:
                # 5. Traitement OCR progressif
                result = self._progressive_ocr(document, context, document_id)

            # ✅ Injecte le texte OCR brut dans le résultat (toujours)
            try:
                result.text = raw_text
            except Exception:
                pass

            # 6. Validation finale
            validation_result = validate_ocr_result(result)
            if not validation_result.is_valid:
                self.logger.warning(f"[{document_id}] Validation warnings: {validation_result.warnings}")

            # 7. Écriture dans Google Sheets
            if self.sheets_connector:
                self._write_to_sheets(result)
                self.logger.info(f"[{document_id}] Results written to Google Sheets")

            # 8. Log final
            self._log_final_result(result)

            return result

        except Exception as e:
            self.logger.error(f"[{document_id}] OCR processing failed: {e}", exc_info=True)
            raise

    def _progressive_ocr(self, document, context: ProcessingContext, document_id: str) -> OCRResult:
        """
        Run OCR in progressive levels based on confidence and missing fields.
        """
        # LEVEL 1
        l1 = self.ocr_level1.process(document, context)
        log_ocr_decision(self.logger, document_id, 1, l1.confidence, l1.needs_next_level)

        if not l1.needs_next_level:
            return l1

        # LEVEL 2
        l2 = self.ocr_level2.process(document, context, previous_result=l1)
        log_ocr_decision(self.logger, document_id, 2, l2.confidence, l2.needs_next_level)

        if not l2.needs_next_level:
            return l2

        # LEVEL 3
        l3 = self.ocr_level3.process(document, context, previous_result=l2)
        log_ocr_decision(self.logger, document_id, 3, l3.confidence, l3.needs_next_level)

        return l3

    def _apply_memory_rule(self, document, rule, context: ProcessingContext, document_id: str) -> OCRResult:
        """
        Apply an existing memory rule (Level 3 learned rules)
        """
        try:
            result = self.ocr_level3.apply_rule(document, context, rule)
            result.document_id = document_id
            return result
        except Exception as e:
            self.logger.warning(f"[{document_id}] Memory rule failed, fallback OCR: {e}")
            return self._progressive_ocr(document, context, document_id)

    def _write_to_sheets(self, result: OCRResult):
        try:
            self.sheets_connector.write_ocr_result(result)
        except Exception as e:
            self.logger.warning(f"Write to sheets warning: {e}")

    def _log_final_result(self, result: OCRResult):
        try:
            self.logger.info(
                f"[{result.document_id}] Final Result: "
                f"type={result.document_type} level={result.level} "
                f"confidence={result.confidence} text_len={len(result.text or '')}"
            )
        except Exception:
            pass
