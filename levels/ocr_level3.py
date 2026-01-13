from copy import deepcopy
from datetime import datetime
from typing import List

from utils.logger import log_ocr_decision


class OCRLevel3:
    """
    OCR Niveau 3 (RARE) :
    - Extraction la plus poussée
    - Correction + IA Memory
    - Création potentielle de règle
    """

    def __init__(self, logger, ai_memory=None):
        self.logger = logger
        self.ai_memory = ai_memory
        self.logger.info("OCR Level 3 initialized")
        self.logger.warning("Level 3 is RARE and creates memory rules")

    def process(self, document, context=None, previous_result=None, ocr2_result=None, **kwargs) -> "OCRResult":
        """
        Traite un document au niveau 3, en s'appuyant sur les résultats du niveau 2.

        Compatibilité :
        - Ancien appel : process(document, ocr2_result, context)
        - Nouveau appel : process(document, context, previous_result=ocr2_result)
        """

        # Compat: support both legacy call (document, ocr2_result, context) and new call (document, context, previous_result=...)
        # Legacy positional swap detection
        if context is not None and hasattr(context, "fields") and (previous_result is None or isinstance(previous_result, dict)):
            ocr2_result = context
            context = previous_result if isinstance(previous_result, dict) else {}
            previous_result = None

        # Keyword aliases
        if context is None and "context" in kwargs:
            context = kwargs.get("context")

        if ocr2_result is None and "ocr2_result" in kwargs:
            ocr2_result = kwargs.get("ocr2_result")

        if ocr2_result is None and previous_result is not None and hasattr(previous_result, "fields"):
            ocr2_result = previous_result

        if ocr2_result is None and "previous_result" in kwargs and hasattr(kwargs.get("previous_result"), "fields"):
            ocr2_result = kwargs.get("previous_result")

        if context is None:
            context = {}

        from ocr_engine import OCRResult

        # Ultra-safe: if OCR2 result is missing, return a minimal level-3 result instead of crashing
        if ocr2_result is None:
            doc_id = getattr(document, "document_id", None)
            if not doc_id and isinstance(context, dict):
                doc_id = context.get("document_id")
            document_id = str(doc_id or "unknown")
            entreprise_source = str((context.get("entreprise_source") if isinstance(context, dict) else "") or "")
            return OCRResult(
                document_id=document_id,
                document_type="autre",
                level=3,
                confidence=0.0,
                entreprise_source=entreprise_source,
                fields={},
                processing_date=datetime.now(),
                needs_next_level=False,
                improved_fields=[],
                corrections=None,
                rule_created=None,
                logs=["LEVEL3_NO_PREVIOUS_RESULT"],
            )

        fields = deepcopy(getattr(ocr2_result, "fields", {}))
        logs: List[str] = list(getattr(ocr2_result, "logs", []) or [])

        document_id = getattr(ocr2_result, "document_id", "") or getattr(document, "document_id", "unknown")
        doc_type = getattr(ocr2_result, "document_type", "autre") or "autre"
        entreprise_source = getattr(ocr2_result, "entreprise_source", "") or context.get("entreprise_source", "")

        confidence = float(getattr(ocr2_result, "confidence", 0.0))
        needs_next_level = False  # Level3 = final

        # --- IA Memory (si disponible) ---
        try:
            if self.ai_memory:
                correction, rule = self.ai_memory.apply(fields, doc_type, entreprise_source)
                if correction:
                    logs.append("LEVEL3_MEMORY_CORRECTION_APPLIED")
                if rule:
                    logs.append("LEVEL3_RULE_CREATED")
        except Exception:
            logs.append("LEVEL3_MEMORY_ERROR")

        try:
            log_ocr_decision(self.logger, document_id, 3, confidence, needs_next_level)
        except Exception:
            pass

        return OCRResult(
            document_id=document_id,
            document_type=doc_type,
            level=3,
            confidence=confidence,
            entreprise_source=entreprise_source,
            fields=fields,
            processing_date=datetime.now(),
            needs_next_level=needs_next_level,
            improved_fields=[],
            corrections=None,
            rule_created=None,
            logs=logs,
        )
