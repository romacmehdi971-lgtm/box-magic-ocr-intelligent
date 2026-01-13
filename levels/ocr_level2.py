import re
from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional

from utils.logger import log_ocr_decision


class OCRLevel2:
    """
    OCR Niveau 2 :
    - Consolidation des champs
    - Extraction structurée via heuristiques avancées
    - Amélioration du type de document
    """

    def __init__(self, logger, validators=None):
        self.logger = logger
        self.validators = validators
        self.logger.info("OCR Level 2 initialized")

    def process(self, document, context=None, previous_result=None, ocr1_result=None, **kwargs) -> "OCRResult":
        """
        Traite un document au niveau 2, en s'appuyant sur les résultats du niveau 1.

        Compatibilité :
        - Ancien appel : process(document, ocr1_result, context)
        - Nouveau appel : process(document, context, previous_result=ocr1_result)
        """

        # Compat: support both legacy call (document, ocr1_result, context) and new call (document, context, previous_result=...)
        # Legacy positional swap detection
        if context is not None and hasattr(context, "fields") and (previous_result is None or isinstance(previous_result, dict)):
            ocr1_result = context
            context = previous_result if isinstance(previous_result, dict) else {}
            previous_result = None

        # Keyword aliases
        if context is None and "context" in kwargs:
            context = kwargs.get("context")

        if ocr1_result is None and "ocr1_result" in kwargs:
            ocr1_result = kwargs.get("ocr1_result")

        if ocr1_result is None and previous_result is not None and hasattr(previous_result, "fields"):
            ocr1_result = previous_result

        if ocr1_result is None and "previous_result" in kwargs and hasattr(kwargs.get("previous_result"), "fields"):
            ocr1_result = kwargs.get("previous_result")

        if context is None:
            context = {}

        from ocr_engine import OCRResult, FieldValue

        # Ultra-safe: if OCR1 result is missing, return a minimal level-2 result instead of crashing
        if ocr1_result is None:
            doc_id = getattr(document, "document_id", None)
            if not doc_id and isinstance(context, dict):
                doc_id = context.get("document_id")
            document_id = str(doc_id or "unknown")
            entreprise_source = str((context.get("entreprise_source") if isinstance(context, dict) else "") or "")
            return OCRResult(
                document_id=document_id,
                document_type="autre",
                level=2,
                confidence=0.0,
                entreprise_source=entreprise_source,
                fields={},
                processing_date=datetime.now(),
                needs_next_level=False,
                improved_fields=[],
                corrections=None,
                rule_created=None,
                logs=["LEVEL2_NO_PREVIOUS_RESULT"],
            )

        fields = deepcopy(getattr(ocr1_result, "fields", {}))
        logs: List[str] = []

        document_id = getattr(ocr1_result, "document_id", "") or getattr(document, "document_id", "unknown")
        entreprise_source = getattr(ocr1_result, "entreprise_source", "") or context.get("entreprise_source", "")

        # ---------------------------
        # Extraction type doc (amélioration)
        # ---------------------------
        doc_type = getattr(ocr1_result, "document_type", "autre") or "autre"
        text = getattr(document, "text", "") or ""

        if text:
            if re.search(r"\bFACTURE\b", text, re.IGNORECASE):
                doc_type = "facture"
                logs.append("LEVEL2_DOC_TYPE_FACTURE")
            elif re.search(r"\bDEVIS\b", text, re.IGNORECASE):
                doc_type = "devis"
                logs.append("LEVEL2_DOC_TYPE_DEVIS")
            elif re.search(r"\bBON\s+DE\s+LIVRAISON\b", text, re.IGNORECASE):
                doc_type = "bon_livraison"
                logs.append("LEVEL2_DOC_TYPE_BL")

        # ---------------------------
        # Extraction référence / numéro facture
        # ---------------------------
        if "numero_facture" not in fields or not fields.get("numero_facture"):
            ref_match = re.search(r"N[°o]\s*([A-Z0-9-]+)", text, re.IGNORECASE)
            if ref_match:
                fields["numero_facture"] = FieldValue(
                    value=ref_match.group(1),
                    confidence=0.85,
                    extraction_method="regex",
                    position=None,
                    pattern="N[°o]\\s*([A-Z0-9-]+)",
                )
                logs.append("LEVEL2_NUM_FACTURE_EXTRACTED")

        # ---------------------------
        # Calcul de confiance (moyenne champs)
        # ---------------------------
        conf_values = []
        for k, v in fields.items():
            try:
                if hasattr(v, "confidence"):
                    conf_values.append(float(v.confidence))
            except Exception:
                pass

        confidence = float(sum(conf_values) / max(len(conf_values), 1)) if conf_values else float(getattr(ocr1_result, "confidence", 0.0))
        needs_next_level = confidence < 0.75

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
