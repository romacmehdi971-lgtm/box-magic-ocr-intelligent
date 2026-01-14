import re
from copy import deepcopy
from datetime import datetime
from typing import List


class OCRLevel2:
    """
    OCR Niveau 2 :
    - Consolidation des champs
    - Extraction structurée via heuristiques avancées
    - Escalade vers niveau 3 si champs critiques manquants
    """

    def __init__(self, logger, validators=None):
        self.logger = self._ensure_logger_(logger, "OCREngine.Level2")
        self.validators = validators
        try:
            self.logger.info("OCR Level 2 initialized")
        except Exception:
            pass

    def process(self, document, context=None, previous_result=None, ocr1_result=None, **kwargs):
        # Compat legacy
        if context is not None and hasattr(context, "fields") and (previous_result is None or isinstance(previous_result, dict)):
            ocr1_result = context
            context = previous_result if isinstance(previous_result, dict) else {}
            previous_result = None

        if context is None:
            context = {}

        if ocr1_result is None and previous_result is not None and hasattr(previous_result, "fields"):
            ocr1_result = previous_result

        from ocr_engine import OCRResult, FieldValue
        from utils.logger import log_ocr_decision

        if ocr1_result is None:
            document_id = getattr(document, "document_id", "unknown")
            entreprise_source = str((context.get("entreprise_source") if isinstance(context, dict) else "") or "")
            return OCRResult(
                document_id=document_id,
                document_type="autre",
                level=2,
                confidence=0.0,
                entreprise_source=entreprise_source,
                fields={},
                processing_date=datetime.now(),
                needs_next_level=True,
                improved_fields=[],
                corrections=None,
                rule_created=None,
                logs=["LEVEL2_NO_PREVIOUS_RESULT"],
            )

        fields = deepcopy(getattr(ocr1_result, "fields", {}))
        logs: List[str] = []

        document_id = getattr(document, "document_id", "unknown")
        entreprise_source = getattr(ocr1_result, "entreprise_source", "") or (context.get("entreprise_source") if isinstance(context, dict) else "")
        doc_type = getattr(ocr1_result, "document_type", "autre") or "autre"

        text = ""
        try:
            text = document.get_text() or ""
        except Exception:
            text = getattr(document, "text", "") or ""

        # Amélioration type doc
        if re.search(r"\bFACTURE\b", text, re.IGNORECASE):
            doc_type = "facture"
            logs.append("LEVEL2_DOC_TYPE_FACTURE")
        elif re.search(r"\bDEVIS\b", text, re.IGNORECASE):
            doc_type = "devis"
            logs.append("LEVEL2_DOC_TYPE_DEVIS")

        # Extraction numéro facture si absent
        if ("numero_facture" not in fields) or (not fields.get("numero_facture")):
            m = re.search(r"Facture\s+FC\s*([0-9]{4})\s*/\s*([0-9]{1,4})", text, re.IGNORECASE)
            if m:
                seq = int(m.group(2))
                fields["numero_facture"] = FieldValue(
                    value=f"FC{seq:06d}",
                    confidence=0.85,
                    extraction_method="regex",
                    position=None,
                    pattern="FACTURE_FC_YYYY_SEQ",
                )
                logs.append("LEVEL2_NUM_FACTURE_EXTRACTED")

        # Confiance moyenne
        conf_values = []
        for _, v in fields.items():
            try:
                if hasattr(v, "confidence"):
                    conf_values.append(float(v.confidence))
            except Exception:
                pass

        base_conf = float(getattr(ocr1_result, "confidence", 0.0) or 0.0)
        confidence = float(sum(conf_values) / max(len(conf_values), 1)) if conf_values else base_conf

        # 🔥 Escalade si champs critiques manquants
        critical_missing = False
        for ck in ["numero_facture", "client_nom", "ttc", "date_doc"]:
            fv = fields.get(ck)
            val = getattr(fv, "value", "") if fv else ""
            if not val or val in ["Unknown", ""]:
                critical_missing = True
                break

        needs_next_level = critical_missing or (confidence < 0.88)

        try:
            log_ocr_decision(self.logger, document_id, 2, confidence, needs_next_level)
        except Exception:
            pass

        return OCRResult(
            document_id=document_id,
            document_type=doc_type,
            level=2,
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
