import re
from copy import deepcopy
from datetime import datetime
from typing import List, Optional, Dict


class OCRLevel2:
    """
    OCR Niveau 2 (BOX MAGIC OCR v1.0.0) :
    - Consolidation + rattrapage champs critiques
    - Extraction structurée via heuristiques avancées
    - Nettoyage / correction des champs Level1
    - Maintient le contrat BOX MAGIC :
      type, numero_facture, societe, client, date_doc, ht, tva_montant, ttc, tva_taux

    SAFE:
    - Normalise self.logger si un dict (ou autre) a été passé à la place d’un logger.
    - Supporte les 2 signatures process() (legacy + nouveau previous_result).
    """

    # Client “A l’attention de …”
    CLIENT_PATTERNS = [
        r"A\s*l['’]attention\s*de\s*([A-Z0-9&'’\-\s]{2,60})",
        r"À\s*l['’]attention\s*de\s*([A-Z0-9&'’\-\s]{2,60})",
        r"CLIENT\s*[:\-]\s*([A-Z0-9&'’\-\s]{2,60})",
        r"DESTINATAIRE\s*[:\-]\s*([A-Z0-9&'’\-\s]{2,60})",
    ]

    # Numéro facture / devis Martin’s : "Facture FC 202 5/143" ou "FC 2025/143"
    NUM_FACTURE_PATTERNS = [
        r"FACTURE\s+FC\s*([0-9]{2,4}\s*/\s*[0-9]{1,6})",
        r"\bFC\s*([0-9]{2,4}\s*/\s*[0-9]{1,6})\b",
        r"\bFACTURE\s*FC\s*([0-9]{1,6})\b",
        r"\bFC\s*([0-9]{1,6})\b",
        # Cas OCR bruité : "FC 202 5/143"
        r"FC\s*([0-9]{1,2})\s*([0-9]{1})\s*/\s*([0-9]{1,6})",
    ]

    NUM_DEVIS_PATTERNS = [
        r"DEVIS\s+DV\s*([0-9]{2,4}\s*/\s*[0-9]{1,6})",
        r"\bDV\s*([0-9]{2,4}\s*/\s*[0-9]{1,6})\b",
        r"\bDEVIS\s*DV\s*([0-9]{1,6})\b",
        r"\bDV\s*([0-9]{1,6})\b",
        r"DV\s*([0-9]{1,2})\s*([0-9]{1})\s*/\s*([0-9]{1,6})",
    ]

    # Date robuste (priorité à “Le 12/06/2025”)
    DATE_PATTERNS = [
        r"\bLE\s+(\d{2})[/-](\d{2})[/-](\d{4})\b",
        r"\b(\d{2})[/-](\d{2})[/-](\d{4})\b",
        r"\b(\d{4})[/-](\d{2})[/-](\d{2})\b",
    ]

    # Montants (capture montant + contexte TTC/HT/TVA)
    AMOUNT_PATTERN = r"(\d{1,3}(?:[,\s]\d{3})*|\d+)[.,](\d{2})\s*€?"

    TTC_KEYWORDS = ["TOTAL TTC", "NET A PAYER", "NET À PAYER", "TOTAL A PAYER", "TOTAL À PAYER", "TTC"]
    HT_KEYWORDS = ["TOTAL HT", "HORS TAXE", "SOUS-TOTAL", "SUBTOTAL", "HT"]
    TVA_MONTANT_KEYWORDS = ["MONTANT TVA", "TVA", "VAT AMOUNT"]

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

        text = getattr(document, "text", "") or ""
        text_upper = text.upper()

        # 1) Type doc amélioré
        doc_type = getattr(ocr1_result, "document_type", "autre") or "autre"
        if "FACTURE" in text_upper:
            doc_type = "facture"
            logs.append("LEVEL2_DOC_TYPE_FACTURE")
        elif "DEVIS" in text_upper:
            doc_type = "devis"
            logs.append("LEVEL2_DOC_TYPE_DEVIS")
        elif re.search(r"\bBON\s+DE\s+LIVRAISON\b", text_upper):
            doc_type = "bon_livraison"
            logs.append("LEVEL2_DOC_TYPE_BL")

        # 2) Harmonisation champ type (contrat BOX MAGIC)
        if "type" not in fields or not getattr(fields.get("type"), "value", None):
            fields["type"] = FieldValue(value=doc_type, confidence=0.80, extraction_method="derived", pattern="doc_type")
            logs.append("LEVEL2_FIELD_TYPE_SET")

        # 3) Numéro facture/devis (crucial)
        if ("numero_facture" not in fields) or (not getattr(fields.get("numero_facture"), "value", None)):
            num = self._extract_numero(text_upper, doc_type)
            if num:
                fields["numero_facture"] = FieldValue(
                    value=num,
                    confidence=0.90,
                    extraction_method="regex",
                    position=None,
                    pattern="NUM_DOC",
                )
                logs.append("LEVEL2_NUMERO_FACTURE_EXTRACTED")

        # 4) Client (destinataire) - priorité “A l’attention de”
        if ("client" not in fields) or (not getattr(fields.get("client"), "value", None)) or str(getattr(fields.get("client"), "value", "")).strip().upper() in ["UNKNOWN", "CLIENT_INCONNU", ""]:
            client = self._extract_client(text_upper)
            if client:
                fields["client"] = FieldValue(
                    value=client,
                    confidence=0.88,
                    extraction_method="client_block",
                    position=None,
                    pattern="CLIENT_BLOCK",
                )
                logs.append("LEVEL2_CLIENT_EXTRACTED")

        # 5) Date doc (date_doc)
        if ("date_doc" not in fields) or (not getattr(fields.get("date_doc"), "value", None)):
            date_doc = self._extract_date_doc(text_upper)
            if date_doc:
                fields["date_doc"] = FieldValue(
                    value=date_doc,
                    confidence=0.90,
                    extraction_method="regex",
                    position=None,
                    pattern="DATE_DOC",
                )
                logs.append("LEVEL2_DATE_DOC_EXTRACTED")

        # 6) Montants (ttc, ht, tva_montant) - si manquants
        self._fill_amounts_if_missing(fields, text_upper, logs)

        # 7) TVA taux mapping (si tva_rate existe)
        if ("tva_taux" not in fields) or (not getattr(fields.get("tva_taux"), "value", None)):
            if "tva_rate" in fields and getattr(fields.get("tva_rate"), "value", None) is not None:
                fields["tva_taux"] = FieldValue(
                    value=getattr(fields["tva_rate"], "value", None),
                    confidence=0.85,
                    extraction_method="mapped",
                    position=None,
                    pattern="tva_rate->tva_taux",
                )
                logs.append("LEVEL2_TVA_TAUX_MAPPED")

        # 8) Confiance & décision Level3 = basé sur champs critiques
        confidence = self._compute_confidence(fields, getattr(ocr1_result, "confidence", 0.0))
        needs_next_level = self._needs_level3(fields, confidence)

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

    # ============================================================
    # EXTRACTIONS
    # ============================================================

    def _extract_client(self, text_upper: str) -> Optional[str]:
        for pat in self.CLIENT_PATTERNS:
            m = re.search(pat, text_upper, re.IGNORECASE)
            if m:
                name = (m.group(1) or "").strip()
                name = re.sub(r"\s+", " ", name)
                name = re.sub(r"[^A-Z0-9&'’\-\s]", "", name).strip()
                if len(name) >= 2:
                    return name
        return None

    def _extract_numero(self, text_upper: str, doc_type: str) -> Optional[str]:
        patterns = self.NUM_FACTURE_PATTERNS if doc_type == "facture" else self.NUM_DEVIS_PATTERNS if doc_type == "devis" else []
        for pat in patterns:
            m = re.search(pat, text_upper, re.IGNORECASE)
            if m:
                # Cas “FC 2 5/143” => group(1)=2 group(2)=5 group(3)=143
                if m.lastindex and m.lastindex >= 3 and len(m.groups()) >= 3 and "FC" in pat or "DV" in pat:
                    g1 = (m.group(1) or "").strip()
                    g2 = (m.group(2) or "").strip()
                    g3 = (m.group(3) or "").strip()
                    if g1.isdigit() and g2.isdigit() and g3.isdigit():
                        year = f"{g1}{g2}"
                        return f"{year}/{g3}"
                raw = (m.group(1) or "").strip()
                raw = raw.replace(" ", "")
                return raw
        return None

    def _extract_date_doc(self, text_upper: str) -> Optional[str]:
        for pat in self.DATE_PATTERNS:
            m = re.search(pat, text_upper, re.IGNORECASE)
            if m:
                # Pattern LE DD/MM/YYYY
                if len(m.groups()) == 3 and m.group(1).isdigit() and m.group(2).isdigit() and m.group(3).isdigit():
                    dd, mm, yyyy = m.group(1), m.group(2), m.group(3)
                    if len(yyyy) == 4:
                        return f"{yyyy}-{mm}-{dd}"
                # YYYY-MM-DD
                if len(m.groups()) == 3 and m.group(1).isdigit() and len(m.group(1)) == 4:
                    yyyy, mm, dd = m.group(1), m.group(2), m.group(3)
                    return f"{yyyy}-{mm}-{dd}"
        return None

    def _fill_amounts_if_missing(self, fields: Dict, text_upper: str, logs: List[str]):
        from ocr_engine import FieldValue

        def parse_amount(s: str) -> Optional[float]:
            try:
                parts = re.findall(self.AMOUNT_PATTERN, s)
                if not parts:
                    return None
                integer_part, decimal_part = parts[-1][0], parts[-1][1]
                integer_part = str(integer_part).replace(" ", "").replace(",", "")
                return float(f"{integer_part}.{decimal_part}")
            except Exception:
                return None

        lines = text_upper.split("\n")

        # TTC
        if ("ttc" not in fields) or (getattr(fields.get("ttc"), "value", 0) in [None, 0, "0", "0.0", 0.0]):
            for line in lines:
                if any(k in line for k in self.TTC_KEYWORDS):
                    amt = parse_amount(line)
                    if amt is not None and amt > 0:
                        fields["ttc"] = FieldValue(value=float(amt), confidence=0.90, extraction_method="context_keyword", pattern="TTC")
                        logs.append("LEVEL2_TTC_EXTRACTED")
                        break

        # HT
        if ("ht" not in fields) or (getattr(fields.get("ht"), "value", 0) in [None, 0, "0", "0.0", 0.0]):
            for line in lines:
                if any(k in line for k in self.HT_KEYWORDS):
                    amt = parse_amount(line)
                    if amt is not None and amt > 0:
                        fields["ht"] = FieldValue(value=float(amt), confidence=0.85, extraction_method="context_keyword", pattern="HT")
                        logs.append("LEVEL2_HT_EXTRACTED")
                        break

        # TVA montant (attention : “TVA” peut aussi être taux, donc on cherche montant “€”)
        if ("tva_montant" not in fields) or (getattr(fields.get("tva_montant"), "value", 0) in [None, 0, "0", "0.0", 0.0]):
            for line in lines:
                if any(k in line for k in self.TVA_MONTANT_KEYWORDS) and re.search(self.AMOUNT_PATTERN, line):
                    amt = parse_amount(line)
                    if amt is not None and amt > 0:
                        fields["tva_montant"] = FieldValue(value=float(amt), confidence=0.80, extraction_method="context_keyword", pattern="TVA_MONTANT")
                        logs.append("LEVEL2_TVA_MONTANT_EXTRACTED")
                        break

        # Calcul TTC si HT+TVA présents mais TTC absent
        try:
            if ("ttc" not in fields or getattr(fields.get("ttc"), "value", 0) in [0, 0.0, None]) and ("ht" in fields and "tva_montant" in fields):
                ht = float(getattr(fields["ht"], "value", 0) or 0)
                tva = float(getattr(fields["tva_montant"], "value", 0) or 0)
                if ht > 0 and tva >= 0:
                    fields["ttc"] = FieldValue(value=float(ht + tva), confidence=0.80, extraction_method="calculation", pattern="HT+TVA")
                    logs.append("LEVEL2_TTC_CALCULATED")
        except Exception:
            pass

    def _compute_confidence(self, fields: Dict, fallback: float) -> float:
        conf_values = []
        for _, v in fields.items():
            try:
                if hasattr(v, "confidence"):
                    conf_values.append(float(v.confidence))
            except Exception:
                pass
        return float(sum(conf_values) / max(len(conf_values), 1)) if conf_values else float(fallback or 0.0)

    def _needs_level3(self, fields: Dict, confidence: float) -> bool:
        # Champs indispensables pour générer Nom_Final
        critical = ["type", "numero_facture", "client", "date_doc", "ttc"]
        missing = any(
            (k not in fields) or (not getattr(fields.get(k), "value", None))
            or (str(getattr(fields.get(k), "value", "")).strip().upper() in ["UNKNOWN", "CLIENT_INCONNU"])
            for k in critical
        )
        low_conf = confidence < 0.78
        return missing or low_conf

    # ============================================================
    # LOGGER NORMALIZATION
    # ============================================================

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
