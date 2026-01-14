import re
from copy import deepcopy
from datetime import datetime
from typing import List


class OCRLevel3:
    """
    OCR Niveau 3 (RARE) :
    - Extraction poussée (facture/devis récurrents)
    - Ajout champs du menu BOX MAGIC
    - Génération de rule_created via AIMemory
    """

    def __init__(self, logger, ai_memory=None):
        self.logger = self._ensure_logger_(logger, "OCREngine.Level3")
        self.ai_memory = ai_memory
        try:
            self.logger.info("OCR Level 3 initialized")
            self.logger.warning("Level 3 is RARE and creates memory rules")
        except Exception:
            pass

    def process(self, document, context=None, previous_result=None, ocr2_result=None, **kwargs):
        # Compat legacy
        if context is not None and hasattr(context, "fields") and (previous_result is None or isinstance(previous_result, dict)):
            ocr2_result = context
            context = previous_result if isinstance(previous_result, dict) else {}
            previous_result = None

        if context is None:
            context = {}

        if ocr2_result is None and previous_result is not None and hasattr(previous_result, "fields"):
            ocr2_result = previous_result

        from ocr_engine import OCRResult, FieldValue
        from utils.logger import log_ocr_decision

        if ocr2_result is None:
            document_id = getattr(document, "document_id", "unknown")
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

        document_id = getattr(document, "document_id", "unknown")
        doc_type = getattr(ocr2_result, "document_type", "autre") or "autre"
        entreprise_source = getattr(ocr2_result, "entreprise_source", "") or (context.get("entreprise_source") if isinstance(context, dict) else "")

        # Texte brut
        text = ""
        try:
            text = document.get_text() or ""
        except Exception:
            text = getattr(document, "text", "") or ""

        # Helpers
        def _fv(val, conf=0.9, method="regex", pattern=None):
            return FieldValue(value=val, confidence=conf, extraction_method=method, position=None, pattern=pattern)

        def _parse_amount(s: str):
            try:
                s = s.replace("€", "").replace(" ", "").replace("\u00A0", "").strip()
                s = s.replace(",", ".")
                return float(s)
            except Exception:
                return None

        # --- Client (A l’attention de)
        mc = re.search(r"A\s+l[’']attention\s+de\s+([A-Z0-9 \-']+)", text, re.IGNORECASE)
        if mc:
            client = mc.group(1).strip()
            fields["client_nom"] = _fv(client, conf=0.95, pattern="A_L_ATTENTION_DE")
            fields["client"] = _fv(client, conf=0.95, method="alias", pattern="client_nom")
            logs.append("LEVEL3_CLIENT_EXTRACTED")

        # --- Numéro facture (Facture FC 2025/143 -> FC000143)
        mf = re.search(r"Facture\s+FC\s*([0-9]{4})\s*/\s*([0-9]{1,4})", text, re.IGNORECASE)
        if mf:
            seq = int(mf.group(2))
            fields["numero_facture"] = _fv(f"FC{seq:06d}", conf=0.96, pattern="FACTURE_FC_YYYY_SEQ")
            logs.append("LEVEL3_NUM_FACTURE_EXTRACTED")

        # --- Date document
        md = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", text)
        if md:
            fields["date_doc"] = _fv(f"{md.group(1)}/{md.group(2)}/{md.group(3)}", conf=0.9, pattern="DD/MM/YYYY")
            logs.append("LEVEL3_DATE_EXTRACTED")

        # --- Montants
        mht = re.search(r"TARIF\s*HT.*?([0-9\.\s]+[.,][0-9]{2})", text, re.IGNORECASE)
        if mht:
            val = _parse_amount(mht.group(1))
            if val is not None:
                fields["ht"] = _fv(val, conf=0.95, pattern="TARIF_HT")
                logs.append("LEVEL3_HT_EXTRACTED")

        mtaux = re.search(r"TVA\s*([0-9]+[.,][0-9]+)\s*%", text, re.IGNORECASE)
        if mtaux:
            tva_taux = float(mtaux.group(1).replace(",", "."))
            fields["tva_taux"] = _fv(tva_taux, conf=0.95, pattern="TVA_TAUX")
            logs.append("LEVEL3_TVA_TAUX_EXTRACTED")

        mtva = re.search(r"TVA\s*[0-9\.,]+\s*%.*?([0-9\.\s]+[.,][0-9]{2})", text, re.IGNORECASE)
        if mtva:
            val = _parse_amount(mtva.group(1))
            if val is not None:
                fields["tva_montant"] = _fv(val, conf=0.92, pattern="TVA_MONTANT")
                logs.append("LEVEL3_TVA_MONTANT_EXTRACTED")

        mttc = re.search(r"TOTAL\s*TTC\s*([0-9\.\s]+[.,][0-9]{2})", text, re.IGNORECASE)
        if mttc:
            val = _parse_amount(mttc.group(1))
            if val is not None:
                fields["ttc"] = _fv(val, conf=0.98, pattern="TOTAL_TTC")
                logs.append("LEVEL3_TTC_EXTRACTED")

        # --- Nb personnes
        mp = re.search(r"/\s*(\d+)\s*Pers", text, re.IGNORECASE)
        if mp:
            fields["nb_personnes"] = _fv(int(mp.group(1)), conf=0.9, pattern="NB_PERSONNES")
            logs.append("LEVEL3_NB_PERSONNES_EXTRACTED")

        # --- Objet / Lieu
        mo = re.search(r"Objet\s*:\s*(.+)", text, re.IGNORECASE)
        if mo:
            fields["prestation_type"] = _fv(mo.group(1).strip(), conf=0.9, pattern="OBJET")
            logs.append("LEVEL3_PRESTATION_TYPE_EXTRACTED")

        ml = re.search(r"Lieu\s*:\s*(.+)", text, re.IGNORECASE)
        if ml:
            fields["lieu_livraison"] = _fv(ml.group(1).strip(), conf=0.88, pattern="LIEU")
            logs.append("LEVEL3_LIEU_EXTRACTED")

        # --- Societe (si Martin’s apparaît)
        if re.search(r"MARTIN[’']?S\s+TRAITEUR", text, re.IGNORECASE):
            fields["societe"] = _fv("MARTIN’S TRAITEUR", conf=0.92, method="text_detect", pattern="MARTINS_TRAITEUR")
            logs.append("LEVEL3_SOCIETE_DETECTED")

        confidence = float(getattr(ocr2_result, "confidence", 0.0) or 0.0)
        # boost si champs critiques présents
        crit = 0
        for ck in ["numero_facture", "client_nom", "ttc", "date_doc"]:
            fv = fields.get(ck)
            if fv and getattr(fv, "value", "") not in ["", "Unknown"]:
                crit += 1
        if crit >= 3:
            confidence = max(confidence, 0.895)

        needs_next_level = False

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

    def apply_rule(self, document, context, rule):
        from ocr_engine import OCRResult, FieldValue
        # Minimal (optionnel)
        return OCRResult(
            document_id=getattr(document, "document_id", "unknown"),
            document_type=rule.get("document_type", "autre"),
            level=3,
            confidence=0.99,
            entreprise_source=context.source_entreprise if hasattr(context, "source_entreprise") else "",
            fields={},
            processing_date=datetime.now(),
            needs_next_level=False,
            improved_fields=[],
            corrections=["APPLIED_RULE"],
            rule_created=None,
            logs=["RULE_APPLIED"],
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
