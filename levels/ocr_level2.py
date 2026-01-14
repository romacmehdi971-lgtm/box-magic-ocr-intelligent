import re
from copy import deepcopy
from datetime import datetime
from typing import List


class OCRLevel2:
    """
    OCR Niveau 2 :
    - Consolidation des champs
    - Extraction structurée via heuristiques avancées
    - Amélioration doc_type
    - Extraction numéro facture type FC + client + TTC (SAFE)

    SAFE:
    - Supporte process(document, context, previous_result=...)
    - Ne casse pas OCR 3 niveaux
    - Si logger mal passé → normalise
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

        # Legacy swap
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

        # SAFE : pas de résultat L1
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

        # Texte
        text = ""
        try:
            text = getattr(document, "text", "") or ""
        except Exception:
            text = ""
        if not text:
            try:
                text = document.get_text() or ""
            except Exception:
                text = ""

        # 1) doc_type amélioré
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
                logs.append("LEVEL2_DOC_TYPE_BC_HINT")

        # 2) Numéro facture FC (robuste OCR)
        if ("numero_facture" not in fields) or (not fields.get("numero_facture")):
            fc_num = self._extract_fc_invoice_number_(text)
            if fc_num:
                fields["numero_facture"] = FieldValue(
                    value=fc_num,
                    confidence=0.92,
                    extraction_method="regex_fc_invoice",
                    position=None,
                    pattern="FC year/number (OCR tolerant)",
                )
                logs.append("LEVEL2_NUM_FACTURE_FC_EXTRACTED")

        # 3) Client “A l’attention de …”
        if ("client" not in fields) or (not fields.get("client")):
            client_name = self._extract_client_attention_(text)
            if client_name:
                fields["client"] = FieldValue(
                    value=client_name,
                    confidence=0.88,
                    extraction_method="keyword_attention",
                    position=None,
                    pattern="A l’attention de",
                )
                logs.append("LEVEL2_CLIENT_ATTENTION_EXTRACTED")

        # 4) TTC / Total TTC / Net à payer
        if ("ttc" not in fields) or (not fields.get("ttc")):
            ttc_value = self._extract_total_ttc_(text)
            if ttc_value is not None and ttc_value > 0:
                fields["ttc"] = FieldValue(
                    value=float(ttc_value),
                    confidence=0.86,
                    extraction_method="keyword_total_ttc",
                    position=None,
                    pattern="TOTAL TTC / NET A PAYER",
                )
                logs.append("LEVEL2_TTC_EXTRACTED")

        # 5) Confiance moyenne
        conf_values = []
        for _, v in fields.items():
            try:
                if hasattr(v, "confidence"):
                    conf_values.append(float(v.confidence))
            except Exception:
                pass

        base_conf = float(getattr(ocr1_result, "confidence", 0.0) or 0.0)
        confidence = float(sum(conf_values) / max(len(conf_values), 1)) if conf_values else base_conf

        # 6) Escalade : confiance OU champs critiques manquants
        critical_missing = False
        if doc_type in ("facture", "devis"):
            critical_missing = (
                ("numero_facture" not in fields or not fields.get("numero_facture")) or
                ("client" not in fields or not fields.get("client")) or
                ("ttc" not in fields or not fields.get("ttc"))
            )
        needs_next_level = (confidence < 0.80) or critical_missing
        if critical_missing:
            logs.append("LEVEL2_CRITICAL_FIELDS_MISSING")

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

    # ----------------------------------------------------------------------
    # Extractors (SAFE)
    # ----------------------------------------------------------------------

    def _extract_fc_invoice_number_(self, text: str) -> str:
        """
        Extrait un numéro facture style:
        - "Facture FC 202 5/143"  -> FC2025/143
        - "Facture FC 2025/143"  -> FC2025/143
        - "Facture FC2025/143"   -> FC2025/143
        """
        if not text:
            return ""

        # Normalise espaces OCR dans les chiffres (ex: 202 5 -> 2025)
        t = re.sub(r"(\d)\s+(\d)", r"\1\2", text)

        patterns = [
            r"\bFACTURE\b.*?\bFC\s*([0-9]{4})\s*/\s*([0-9]{1,6})",
            r"\bFC\s*([0-9]{4})\s*/\s*([0-9]{1,6})",
            r"\bFACTURE\b.*?\bFC\s*([0-9]{2})\s*([0-9]{2})\s*/\s*([0-9]{1,6})",
        ]

        for p in patterns:
            m = re.search(p, t, re.IGNORECASE | re.DOTALL)
            if m:
                if len(m.groups()) == 2:
                    year = m.group(1)
                    num = m.group(2)
                    return f"FC{year}/{num}"
                if len(m.groups()) == 3:
                    year = f"{m.group(1)}{m.group(2)}"
                    num = m.group(3)
                    return f"FC{year}/{num}"

        # Fallback : "Facture FC 2025/143" parfois sans mot FACTURE
        m2 = re.search(r"\bFC\s*([0-9]{4})\s*[-/]\s*([0-9]{1,6})", t, re.IGNORECASE)
        if m2:
            return f"FC{m2.group(1)}/{m2.group(2)}"

        return ""

    def _extract_client_attention_(self, text: str) -> str:
        """
        Extrait le client après "A l’attention de" / "A l'attention de".
        """
        if not text:
            return ""

        lines = [l.strip() for l in text.splitlines() if l.strip()]
        for i, line in enumerate(lines):
            if re.search(r"a\s+l[’']attention\s+de", line, re.IGNORECASE):
                # Cas 1 : le nom est sur la même ligne
                same = re.sub(r"^.*a\s+l[’']attention\s+de\s*[:\-]?\s*", "", line, flags=re.IGNORECASE).strip()
                if same and len(same) >= 2:
                    return self._clean_party_name_(same)

                # Cas 2 : le nom est sur la ligne suivante
                if i + 1 < len(lines):
                    return self._clean_party_name_(lines[i + 1])

        # Fallback regex multi-ligne
        m = re.search(r"a\s+l[’']attention\s+de\s*[:\-]?\s*([A-Z0-9&' \-]{2,})", text, re.IGNORECASE)
        if m:
            return self._clean_party_name_(m.group(1))

        return ""

    def _extract_total_ttc_(self, text: str) -> float:
        """
        Extrait TTC via mots-clés.
        """
        if not text:
            return 0.0

        # Normalisation
        t = text.replace("\u00a0", " ")
        lines = [l.strip() for l in t.splitlines() if l.strip()]

        # Recherche lignes TTC
        keywords = ["total ttc", "net a payer", "net à payer", "montant ttc", "total"]
        for line in lines:
            ll = line.lower()
            if any(k in ll for k in keywords):
                amt = self._extract_euro_amount_(line)
                if amt is not None:
                    return amt

        # Fallback : max montant € si doc facture/devis
        amounts = []
        for line in lines:
            amt = self._extract_euro_amount_(line)
            if amt is not None:
                amounts.append(amt)
        if amounts:
            return float(max(amounts))

        return 0.0

    def _extract_euro_amount_(self, line: str) -> float:
        """
        Extrait un montant type 8 168,00€ ou 8168.00 €
        """
        if not line:
            return None

        # 8 168,00  / 8168,00 / 8168.00
        m = re.findall(r"(\d{1,3}(?:[ \.,]\d{3})*|\d+)[\.,](\d{2})\s*€", line)
        if m:
            val = m[-1]
            int_part = val[0].replace(" ", "").replace(".", "").replace(",", "")
            dec_part = val[1]
            try:
                return float(f"{int_part}.{dec_part}")
            except Exception:
                return None

        m2 = re.findall(r"€\s*(\d{1,3}(?:[ \.,]\d{3})*|\d+)[\.,](\d{2})", line)
        if m2:
            val = m2[-1]
            int_part = val[0].replace(" ", "").replace(".", "").replace(",", "")
            dec_part = val[1]
            try:
                return float(f"{int_part}.{dec_part}")
            except Exception:
                return None

        return None

    def _clean_party_name_(self, s: str) -> str:
        """
        Nettoie un nom client/fournisseur (évite adresse)
        """
        if not s:
            return ""
        s2 = s.strip()
        s2 = re.sub(r"\s{2,}", " ", s2)
        # coupe sur virgule ou double espace + chiffres d'adresse
        s2 = re.split(r",|\d{2,5}\s", s2)[0].strip()
        # coupe si trop long
        if len(s2) > 40:
            s2 = s2[:40].strip()
        return s2

    # ----------------------------------------------------------------------

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
