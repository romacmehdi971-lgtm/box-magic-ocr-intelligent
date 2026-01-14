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

    Fix PRO (Mode Réussite) :
    - Normalisation du texte OCR (répare les espaces dans les nombres : 202 5 → 2025)
    - Extraction PRIORITAIRE du vrai numéro de facture "Facture FC 2025/143"
    - Formatage du numéro : FC000143
    - Remplissage date_doc (depuis date_emission si dispo, sinon regex normalisée)
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
        - Ancien appel : process(document, ocr1_result, context)
        - Nouveau appel : process(document, context, previous_result=ocr1_result)
        """

        # Compat legacy positional swap:
        if context is not None and hasattr(context, "fields") and (previous_result is None or isinstance(previous_result, dict)):
            ocr1_result = context
            context = previous_result if isinstance(previous_result, dict) else {}
            previous_result = None

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
        from utils.logger import log_ocr_decision

        # SAFE: si aucun résultat niveau1
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

        # Texte OCR : selon loader, soit document.text soit document.get_text()
        raw_text = ""
        try:
            raw_text = getattr(document, "text", "") or ""
        except Exception:
            raw_text = ""
        if not raw_text:
            try:
                raw_text = document.get_text() or ""
            except Exception:
                raw_text = ""

        # ✅ Normalisation PRO : corrige "202 5" → "2025" et "FC 202 5/143" → "FC 2025/143"
        text = raw_text
        try:
            text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)  # retire espaces entre chiffres
        except Exception:
            pass

        # Détection type doc améliorée
        doc_type = getattr(ocr1_result, "document_type", "autre") or "autre"
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

        # ============================================================
        # ✅ EXTRACTION PRIORITAIRE : Numéro de facture FC AAAA/NNN
        # Exemple : "Facture FC 2025/143"
        # Format souhaité : FC000143 (padding 6 digits)
        # ============================================================
        facture_match = None
        if text:
            facture_match = re.search(r"Facture\s+FC\s*([0-9]{4})\s*/\s*([0-9]{1,6})", text, re.IGNORECASE)
            if facture_match:
                annee = facture_match.group(1)
                numero = facture_match.group(2)
                try:
                    numero_int = int(numero)
                    numero_final = f"FC{numero_int:06d}"  # FC000143
                except Exception:
                    numero_final = f"FC{numero.zfill(6)}"
                fields["numero_facture"] = FieldValue(
                    value=numero_final,
                    confidence=0.97,
                    extraction_method="regex_priority",
                    position=None,
                    pattern="Facture FC AAAA/NNN",
                )
                logs.append("LEVEL2_NUM_FACTURE_FC_PRIORITY")

        # Fallback : seulement si on n’a pas trouvé mieux
        if ("numero_facture" not in fields) or (not fields.get("numero_facture")):
            ref_match = re.search(r"\bFACTURE\b.*?\bN[°o]\s*([A-Z0-9\-\/]+)", text, re.IGNORECASE)
            if ref_match:
                fields["numero_facture"] = FieldValue(
                    value=ref_match.group(1),
                    confidence=0.80,
                    extraction_method="regex_fallback",
                    position=None,
                    pattern="FACTURE ... N°",
                )
                logs.append("LEVEL2_NUM_FACTURE_FALLBACK_FACTURE_CONTEXT")

        # ============================================================
        # ✅ DATE DOC : si OCR1 a date_emission -> on copie vers date_doc
        # sinon extraction regex dd/mm/yyyy (après normalisation)
        # ============================================================
        if "date_doc" not in fields or not fields.get("date_doc"):
            if "date_emission" in fields and fields.get("date_emission"):
                try:
                    fields["date_doc"] = FieldValue(
                        value=fields["date_emission"].value,
                        confidence=0.90,
                        extraction_method="alias",
                        position=None,
                        pattern="date_emission->date_doc",
                    )
                    logs.append("LEVEL2_DATE_DOC_FROM_DATE_EMISSION")
                except Exception:
                    pass

        if "date_doc" not in fields or not fields.get("date_doc"):
            date_match = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", text)
            if date_match:
                fields["date_doc"] = FieldValue(
                    value=f"{date_match.group(1)}/{date_match.group(2)}/{date_match.group(3)}",
                    confidence=0.92,
                    extraction_method="regex",
                    position=None,
                    pattern="dd/mm/yyyy",
                )
                logs.append("LEVEL2_DATE_DOC_EXTRACTED_REGEX")

        # ============================================================
        # Confiance moyenne des champs
        # ============================================================
        conf_values = []
        for _, v in fields.items():
            try:
                if hasattr(v, "confidence"):
                    conf_values.append(float(v.confidence))
            except Exception:
                pass

        base_conf = float(getattr(ocr1_result, "confidence", 0.0) or 0.0)
        confidence = float(sum(conf_values) / max(len(conf_values), 1)) if conf_values else base_conf

        # Escalade seulement si champs critiques manquent
        critical = ["numero_facture", "client", "ttc", "date_doc"]
        missing_critical = any(k not in fields or not fields.get(k) for k in critical)
        needs_next_level = missing_critical or (confidence < 0.78)

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
