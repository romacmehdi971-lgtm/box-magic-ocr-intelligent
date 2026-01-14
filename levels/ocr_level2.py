# levels/ocr_level2.py

import re
from copy import deepcopy
from datetime import datetime
from typing import List, Optional


class OCRLevel2:
    """
    OCR Niveau 2 :
    - Consolidation des champs
    - Extraction structurée via heuristiques avancées
    - Amélioration du type de document

    SAFE:
    - Accepte les signatures legacy et le paramètre previous_result
    - Ne casse jamais le pipeline si un champ est absent
    """

    def __init__(self, logger, validators=None):
        self.logger = self._ensure_logger_(logger, "OCREngine.Level2")
        self.validators = validators
        try:
            self.logger.info("OCR Level 2 initialized")
        except Exception:
            pass

    def process(self, document, context=None, previous_result=None, ocr1_result=None, **kwargs) -> "OCRResult":
        """
        Compatibilité :
        - Legacy : process(document, ocr1_result, context)
        - Nouveau : process(document, context, previous_result=ocr1_result)
        """

        # compat legacy swap
        if context is not None and hasattr(context, "fields") and (previous_result is None or isinstance(previous_result, dict)):
            ocr1_result = context
            context = previous_result if isinstance(previous_result, dict) else {}
            previous_result = None

        if context is None:
            context = kwargs.get("context") if "context" in kwargs else {}

        if ocr1_result is None:
            ocr1_result = kwargs.get("ocr1_result")

        if ocr1_result is None and previous_result is not None and hasattr(previous_result, "fields"):
            ocr1_result = previous_result

        if ocr1_result is None and "previous_result" in kwargs and hasattr(kwargs.get("previous_result"), "fields"):
            ocr1_result = kwargs.get("previous_result")

        from ocr_engine import OCRResult, FieldValue
        from utils.logger import log_ocr_decision

        if ocr1_result is None:
            doc_id = getattr(document, "document_id", None) or (context.get("document_id") if isinstance(context, dict) else None)
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
        entreprise_source = getattr(ocr1_result, "entreprise_source", "") or (context.get("entreprise_source") if isinstance(context, dict) else "")

        # Récupération du texte
        text = ""
        try:
            if hasattr(document, "get_text"):
                text = document.get_text() or ""
            else:
                text = getattr(document, "text", "") or ""
        except Exception:
            text = ""

        # Détection type améliorée
        doc_type = getattr(ocr1_result, "document_type", "autre") or "autre"
        if text:
            if re.search(r"\bFACTURE\b", text, re.IGNORECASE) or re.search(r"\bFC\b", text):
                doc_type = "facture"
                logs.append("LEVEL2_DOC_TYPE_FACTURE")
            elif re.search(r"\bDEVIS\b", text, re.IGNORECASE):
                doc_type = "devis"
                logs.append("LEVEL2_DOC_TYPE_DEVIS")
            elif re.search(r"\bBON\s+DE\s+LIVRAISON\b", text, re.IGNORECASE):
                doc_type = "bon_livraison"
                logs.append("LEVEL2_DOC_TYPE_BL")

        # Extraction client_nom (A l’attention de)
        if "client_nom" not in fields or not fields.get("client_nom"):
            m = re.search(r"A\s*l[’']attention\s*de\s*([A-Z0-9&'’\-\s]{2,})", text, re.IGNORECASE)
            if m:
                client_nom = m.group(1).strip()
                client_nom = re.split(r"\n", client_nom)[0].strip()
                fields["client_nom"] = FieldValue(
                    value=client_nom,
                    confidence=0.95,
                    extraction_method="regex",
                    position=None,
                    pattern="A_L_ATTENTION_DE",
                )
                logs.append("LEVEL2_CLIENT_NOM_EXTRACTED")

        # Extraction numero_facture format FC 2025/143 -> FC000143
        if "numero_facture" not in fields or not fields.get("numero_facture"):
            m = re.search(r"\bFC\s*([0-9]{2,4})\s*/\s*([0-9]{1,6})\b", text, re.IGNORECASE)
            if m:
                num = m.group(2).strip()
                num_norm = "FC" + num.zfill(6)
                fields["numero_facture"] = FieldValue(
                    value=num_norm,
                    confidence=0.95,
                    extraction_method="regex",
                    position=None,
                    pattern="FC_YYYY_NUM",
                )
                logs.append("LEVEL2_NUM_FACTURE_FC_EXTRACTED")

        # Extraction date_doc (Le 12/06/2025)
        if "date_doc" not in fields or not fields.get("date_doc"):
            m = re.search(r"\bLe\s*(\d{2})/(\d{2})/(\d{4})\b", text, re.IGNORECASE)
            if m:
                date_iso = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
                fields["date_doc"] = FieldValue(
                    value=date_iso,
                    confidence=0.9,
                    extraction_method="regex",
                    position=None,
                    pattern="LE_DDMMYYYY",
                )
                logs.append("LEVEL2_DATE_DOC_EXTRACTED")

        # Confiance
        conf_values = []
        for _, v in fields.items():
            try:
                if hasattr(v, "confidence"):
                    conf_values.append(float(v.confidence))
            except Exception:
                pass

        base_conf = float(getattr(ocr1_result, "confidence", 0.0) or 0.0)
        confidence = float(sum(conf_values) / max(len(conf_values), 1)) if conf_values else base_conf
        needs_next_level = confidence < 0.80  # monte l’exigence -> OCR3 seulement si vraiment nécessaire

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
