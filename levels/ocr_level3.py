# levels/ocr_level3.py

import re
from copy import deepcopy
from datetime import datetime
from typing import List


class OCRLevel3:
    """
    OCR Niveau 3 (RARE) :
    - Extraction la plus poussée
    - Correction + IA Memory
    - Création potentielle de règle

    SAFE:
    - Accepte les signatures legacy et previous_result
    - Ne casse jamais le moteur
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
        - Legacy : process(document, ocr2_result, context)
        - Nouveau : process(document, context, previous_result=ocr2_result)
        """

        if context is not None and hasattr(context, "fields") and (previous_result is None or isinstance(previous_result, dict)):
            ocr2_result = context
            context = previous_result if isinstance(previous_result, dict) else {}
            previous_result = None

        if context is None:
            context = kwargs.get("context") if "context" in kwargs else {}

        if ocr2_result is None:
            ocr2_result = kwargs.get("ocr2_result")

        if ocr2_result is None and previous_result is not None and hasattr(previous_result, "fields"):
            ocr2_result = previous_result

        if ocr2_result is None and "previous_result" in kwargs and hasattr(kwargs.get("previous_result"), "fields"):
            ocr2_result = kwargs.get("previous_result")

        from ocr_engine import OCRResult, FieldValue
        from utils.logger import log_ocr_decision

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

        # Texte
        text = ""
        try:
            if hasattr(document, "get_text"):
                text = document.get_text() or ""
            else:
                text = getattr(document, "text", "") or ""
        except Exception:
            text = ""

        # Date prestation (souvent "Date : Le 12 Juin 2025" ou "Date : Le 12/06/2025")
        if "date_prestation" not in fields or not fields.get("date_prestation"):
            m = re.search(r"\bDate\s*:\s*Le\s*(\d{1,2})\s*(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s*(\d{4})\b", text, re.IGNORECASE)
            if m:
                mois_map = {
                    "janvier": "01", "février": "02", "mars": "03", "avril": "04", "mai": "05", "juin": "06",
                    "juillet": "07", "août": "08", "septembre": "09", "octobre": "10", "novembre": "11", "décembre": "12"
                }
                dd = str(m.group(1)).zfill(2)
                mm = mois_map.get(m.group(2).lower(), "01")
                yyyy = m.group(3)
                fields["date_prestation"] = FieldValue(
                    value=f"{yyyy}-{mm}-{dd}",
                    confidence=0.9,
                    extraction_method="regex",
                    position=None,
                    pattern="DATE_LETTERS",
                )
                logs.append("LEVEL3_DATE_PRESTATION_EXTRACTED")

        # fallback : si date_prestation vide mais date_doc existe -> copier
        if ("date_prestation" not in fields or not fields.get("date_prestation")) and ("date_doc" in fields and fields.get("date_doc")):
            try:
                fields["date_prestation"] = FieldValue(
                    value=getattr(fields["date_doc"], "value", ""),
                    confidence=0.75,
                    extraction_method="derived",
                    position=None,
                    pattern="FROM_DATE_DOC",
                )
                logs.append("LEVEL3_DATE_PRESTATION_FROM_DATE_DOC")
            except Exception:
                pass

        confidence = float(getattr(ocr2_result, "confidence", 0.0) or 0.0)
        needs_next_level = False

        # IA Memory : applique + crée règle
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
