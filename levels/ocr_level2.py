import re
import hashlib
from copy import deepcopy
from datetime import datetime
from typing import List


class OCRLevel2:
    """
    OCR Niveau 2 :
    - Consolidation des champs
    - Extraction structurée via heuristiques avancées
    - Amélioration du type de document

    Patch SAFE:
    - Normalise self.logger si un dict (ou autre) a été passé à la place d’un logger.
    - Supporte les 2 signatures process() (legacy + nouveau previous_result).
    - Extraction intelligente des champs depuis le texte si fields incomplets.
    - Génération document_id stable si "unknown".
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
        Traite un document au niveau 2, en s'appuyant sur les résultats du niveau 1.

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

        raw_doc_id = getattr(ocr1_result, "document_id", "") or getattr(document, "document_id", "") or ""
        entreprise_source = getattr(ocr1_result, "entreprise_source", "") or (context.get("entreprise_source") if isinstance(context, dict) else "")
        text = getattr(document, "text", "") or ""

        # ---------------------------------------------------------------------
        # 1) Document ID stable (si unknown / vide)
        # ---------------------------------------------------------------------
        document_id = str(raw_doc_id).strip() if raw_doc_id else ""
        if (not document_id) or (document_id.lower() in ["unknown", "none", "null"]):
            base = ""
            try:
                base = (getattr(document, "source_name", "") or getattr(document, "filename", "") or "").strip()
            except Exception:
                base = ""
            if not base and isinstance(context, dict):
                base = str(context.get("filename") or context.get("file_name") or "").strip()

            digest_src = (base + "\n" + text[:2000]).encode("utf-8", errors="ignore")
            h = hashlib.sha256(digest_src).hexdigest()[:16]
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            document_id = f"doc_{stamp}_{h}"
            logs.append("LEVEL2_DOCUMENT_ID_STABILIZED")

        # ---------------------------------------------------------------------
        # 2) Type document amélioré
        # ---------------------------------------------------------------------
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
            elif re.search(r"\bBON\s+DE\s+COMMANDE\b", text, re.IGNORECASE):
                doc_type = "bon_commande"
                logs.append("LEVEL2_DOC_TYPE_BC")

        # ---------------------------------------------------------------------
        # 3) Helpers SAFE extraction
        # ---------------------------------------------------------------------
        def _field_is_empty_(k: str) -> bool:
            try:
                v = fields.get(k)
                if v is None:
                    return True
                if hasattr(v, "value"):
                    return str(v.value).strip() == ""
                return str(v).strip() == ""
            except Exception:
                return True

        def _set_field_(k: str, value, conf: float, method: str, pattern: str):
            try:
                fields[k] = FieldValue(
                    value=value,
                    confidence=float(conf),
                    extraction_method=method,
                    position=None,
                    pattern=pattern,
                )
            except Exception:
                pass

        # ---------------------------------------------------------------------
        # 4) Extraction numéro facture / référence (intelligent)
        # ---------------------------------------------------------------------
        if _field_is_empty_("numero_facture"):
            # Ex: "Facture FC 2025/143" ou "Facture FC 2025-143"
            m = re.search(r"\bFacture\s+([A-Z]{1,4}\s*\d{2,4}[\/\-]\d{1,6})\b", text, re.IGNORECASE)
            if m:
                val = re.sub(r"\s+", "", m.group(1)).strip()
                _set_field_("numero_facture", val, 0.92, "regex", r"Facture\s+([A-Z]{1,4}\s*\d{2,4}[\/\-]\d{1,6})")
                logs.append("LEVEL2_NUM_FACTURE_FROM_FACTURE_LINE")

        if _field_is_empty_("numero_facture"):
            # fallback ancien pattern N°
            ref_match = re.search(r"N[°o]\s*([A-Z0-9-]+)", text, re.IGNORECASE)
            if ref_match:
                _set_field_("numero_facture", ref_match.group(1), 0.85, "regex", r"N[°o]\s*([A-Z0-9-]+)")
                logs.append("LEVEL2_NUM_FACTURE_EXTRACTED")

        # ---------------------------------------------------------------------
        # 5) Extraction client (A l’attention de ...)
        # ---------------------------------------------------------------------
        if _field_is_empty_("client"):
            # Capture bloc après "A l’attention de"
            m = re.search(r"A\s*l[’']attention\s+de\s+(.*)", text, re.IGNORECASE)
            if m:
                first_line = m.group(1).strip()
                first_line = re.sub(r"\s{2,}", " ", first_line)
                # Nettoyage
                first_line = re.sub(r"[\|•]+", " ", first_line).strip()
                if first_line:
                    _set_field_("client", first_line, 0.90, "keyword_context", "A l’attention de")
                    logs.append("LEVEL2_CLIENT_FROM_ATTENTION")

        # ---------------------------------------------------------------------
        # 6) Extraction date document
        # ---------------------------------------------------------------------
        if _field_is_empty_("date_doc"):
            # "Le 12/06/2025" ou "Le 12 Juin 2025"
            m = re.search(r"\bLe\s+(\d{2}[\/\-]\d{2}[\/\-]\d{4})\b", text, re.IGNORECASE)
            if m:
                _set_field_("date_doc", m.group(1), 0.88, "regex", r"Le\s+(\d{2}[\/\-]\d{2}[\/\-]\d{4})")
                logs.append("LEVEL2_DATE_DOC_DDMMYYYY")
            else:
                m2 = re.search(r"\bLe\s+(\d{1,2})\s+([A-Za-zéèêàùûîôç]+)\s+(\d{4})\b", text, re.IGNORECASE)
                if m2:
                    _set_field_("date_doc", f"{m2.group(1)} {m2.group(2)} {m2.group(3)}", 0.78, "regex", r"Le\s+(\d{1,2})\s+([A-Za-zéèêàùûîôç]+)\s+(\d{4})")
                    logs.append("LEVEL2_DATE_DOC_TEXTUAL")

        # ---------------------------------------------------------------------
        # 7) TVA taux fallback si tva_rate existe
        # ---------------------------------------------------------------------
        if _field_is_empty_("tva_taux") and ("tva_rate" in fields) and hasattr(fields.get("tva_rate"), "value"):
            try:
                _set_field_("tva_taux", fields["tva_rate"].value, 0.90, "mapped", "tva_rate->tva_taux")
                logs.append("LEVEL2_TVA_TAUX_FROM_TVA_RATE")
            except Exception:
                pass

        # ---------------------------------------------------------------------
        # 8) Normalisation "type" et "societe" (standard attendu Apps Script)
        # ---------------------------------------------------------------------
        if _field_is_empty_("type"):
            _set_field_("type", doc_type, 0.95, "derived", "doc_type")
            logs.append("LEVEL2_TYPE_NORMALIZED")

        if _field_is_empty_("societe") and entreprise_source:
            _set_field_("societe", entreprise_source, 0.92, "context", "entreprise_source")
            logs.append("LEVEL2_SOCIETE_FROM_ENTREPRISE_SOURCE")

        # ---------------------------------------------------------------------
        # 9) Confiance globale + décision level3
        # ---------------------------------------------------------------------
        conf_values = []
        for _, v in fields.items():
            try:
                if hasattr(v, "confidence"):
                    conf_values.append(float(v.confidence))
            except Exception:
                pass

        base_conf = float(getattr(ocr1_result, "confidence", 0.0) or 0.0)
        confidence = float(sum(conf_values) / max(len(conf_values), 1)) if conf_values else base_conf

        # Condition simple pour passer niveau 3 : manque client ou numero_facture ou date_doc
        missing_critical = _field_is_empty_("client") or _field_is_empty_("numero_facture") or _field_is_empty_("date_doc")
        needs_next_level = bool((confidence < 0.78) or missing_critical)

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
