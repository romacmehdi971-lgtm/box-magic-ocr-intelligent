from copy import deepcopy
from datetime import datetime
from typing import List


class OCRLevel3:
    """
    OCR Niveau 3 (RARE) :
    - Extraction la plus poussée
    - Correction + IA Memory
    - Création potentielle de règle

    Patch SAFE:
    - Normalise self.logger si un dict (ou autre) a été passé à la place d’un logger.
    - Supporte les 2 signatures process() (legacy + nouveau previous_result).
    """

    def __init__(self, logger, ai_memory=None):
        self.logger = self._ensure_logger_(logger, "OCREngine.Level3")
        self.ai_memory = ai_memory
        try:
            self.logger.info("OCR Level 3 initialized")
            self.logger.warning("Level 3 is RARE and creates memory rules")
        except Exception:
            pass

    def process(self, document, context=None, previous_result=None, ocr2_result=None, **kwargs) -> "OCRResult":
        """
        Compatibilité :
        - Ancien appel : process(document, ocr2_result, context)
        - Nouveau appel : process(document, context, previous_result=ocr2_result)
        """

        # Compat legacy positional swap:
        if context is not None and hasattr(context, "fields") and (previous_result is None or isinstance(previous_result, dict)):
            ocr2_result = context
            context = previous_result if isinstance(previous_result, dict) else {}
            previous_result = None

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
        from utils.logger import log_ocr_decision

        # SAFE: si aucun résultat niveau2
        if ocr2_result is None:
            doc_id = getattr(document, "document_id", None) or (context.get("document_id") if isinstance(context, dict) else None)
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
        entreprise_source = getattr(ocr2_result, "entreprise_source", "") or (context.get("entreprise_source") if isinstance(context, dict) else "")

        confidence = float(getattr(ocr2_result, "confidence", 0.0) or 0.0)
        needs_next_level = False  # Level 3 final

        # IA Memory (si dispo)
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

    def _ensure_logger_(self, maybe_logger, name: str):
        """
        Normalise un logger : si dict/None/objet invalide → crée un logger standard.
        """
        try:
            if maybe_logger and hasattr(maybe_logger, "info") and hasattr(maybe_logger, "warning") and hasattr(maybe_logger, "error"):
                return maybe_logger
        except Exception:
            pass

        try:
            from utils.logger import setup_logger
            return setup_logger(name)
        except Exception:
            import logging
            logger = logging.getLogger(name)
            if not logger.handlers:
                logging.basicConfig(level=logging.INFO)
            return logger
