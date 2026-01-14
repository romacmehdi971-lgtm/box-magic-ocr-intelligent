#!/usr/bin/env python3
"""
BOX MAGIC OCR ENGINE - Point d'entrée principal
Architecture 3 niveaux : Rapide → Approfondi → Mémoire (rules)
PHASE 1 - MODE RÉUSSITE:
- document_id stable
- OCR3 extrait les champs manquants via texte
- OCR3 génère rule_created + template_signature + hash_document
- Réponse JSON compatible BOX MAGIC (fields normalisés)
"""

import os
import re
import hashlib
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml

from levels.ocr_level1 import OCRLevel1
from levels.ocr_level2 import OCRLevel2
from levels.ocr_level3 import OCRLevel3
from memory.ai_memory import AIMemory
from connectors.google_sheets import GoogleSheetsConnector
from connectors.document_loader import DocumentLoader
from utils.logger import setup_logger, log_ocr_decision
from utils.validators import validate_ocr_result


# ======================================================================
# DATA MODELS
# ======================================================================

@dataclass
class FieldValue:
    value: Any
    confidence: float
    extraction_method: Optional[str] = None
    position: Optional[dict] = None
    pattern: Optional[str] = None


@dataclass
class OCRResult:
    """Résultat complet d'un traitement OCR"""
    document_id: str
    document_type: str
    level: int  # 1, 2 ou 3
    confidence: float  # 0.0 à 1.0
    entreprise_source: str
    fields: Dict[str, FieldValue]
    processing_date: datetime
    text: str = ""  # TEXTE OCR BRUT
    needs_next_level: bool = False
    improved_fields: Optional[List[str]] = None
    corrections: Optional[List[str]] = None
    rule_created: Optional[dict] = None
    logs: List[str] = field(default_factory=list)

    def to_dict(self):
        """Convertit en dictionnaire JSON friendly"""
        result = asdict(self)
        result['processing_date'] = self.processing_date.isoformat()
        result['text_length'] = len(self.text or "")
        return result


@dataclass
class ProcessingContext:
    source_entreprise: str
    entreprise_config: dict
    options: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


# ======================================================================
# OCR ENGINE
# ======================================================================

class OCREngine:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config = self._load_config(config_path)
        self.logger = setup_logger("OCREngine", self.config.get('log_level', 'INFO'))

        # ✅ Correction critique: passer un logger réel aux niveaux 2/3 (pas self.config dict)
        self.ocr_level1 = OCRLevel1(self.config)
        self.ocr_level2 = OCRLevel2(self.logger, validators=None)
        self.memory = AIMemory(self.config.get('memory_store_path', 'memory/rules.json'))
        self.ocr_level3 = OCRLevel3(self.logger, ai_memory=self.memory)

        self.document_loader = DocumentLoader(self.config)
        self.sheets_connector = self._init_sheets_connector()

    def _load_config(self, config_path: str) -> dict:
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
        except Exception as e:
            logging.warning(f"Config load warning: {e}")
        return {}

    def _init_sheets_connector(self):
        try:
            if self.config.get('google_sheets', {}).get('enabled', False):
                return GoogleSheetsConnector(self.config)
        except Exception as e:
            self.logger.warning(f"Sheets connector init warning: {e}")
        return None

    def _prepare_context(self, source_entreprise: str, options: dict) -> ProcessingContext:
        entreprise_config = self.config.get('entreprises', {}).get(source_entreprise, {})
        return ProcessingContext(
            source_entreprise=source_entreprise,
            entreprise_config=entreprise_config,
            options=options or {}
        )

    def process_document(self,
                         file_path: str,
                         source_entreprise: str,
                         options: Optional[dict] = None) -> OCRResult:
        """
        Process a document with progressive OCR (levels 1-3)
        """
        options = options or {}

        # document_id stable + court
        document_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.sha1(Path(file_path).stem.encode('utf-8')).hexdigest()[:12]}"
        self.logger.info(f"[{document_id}] Starting OCR processing")
        self.logger.info(f"[{document_id}] File: {file_path}")

        try:
            # 1) Chargement document
            document = self.document_loader.load(file_path)

            # FIX: attacher un id au document (évite "unknown")
            try:
                setattr(document, "document_id", document_id)
            except Exception:
                pass

            # texte brut
            raw_text = ""
            try:
                raw_text = document.get_text() or ""
            except Exception:
                raw_text = ""

            # 2) Contexte
            context = self._prepare_context(source_entreprise, options)

            # 3) Mémoire existante (local) — SAFE
            matching_rule = None
            try:
                matching_rule = self.memory.find_matching_rule(document, context)
            except Exception:
                matching_rule = None

            if matching_rule and not options.get('force_full_ocr'):
                result = self._apply_memory_rule(document, matching_rule, context, document_id)
            else:
                result = self._progressive_ocr(document, context, document_id)

            # injecter texte
            result.text = raw_text

            # 4) Normalisation BOX MAGIC (champs attendus)
            result = self._boxmagic_normalize_result(result, raw_text, context)

            # 5) Si Level3 → générer rule_created
            if result.level == 3:
                try:
                    rule = self.memory.create_rule_from_result(result, raw_text, context)
                    if rule:
                        result.rule_created = rule
                        result.logs.append("RULE_CREATED_LEVEL3")
                except Exception as e:
                    result.logs.append(f"RULE_CREATE_ERROR:{type(e).__name__}")

            # 6) Validation (warning only)
            try:
                validation_result = validate_ocr_result(result)
                if hasattr(validation_result, "is_valid") and not validation_result.is_valid:
                    self.logger.warning(f"[{document_id}] Validation warnings: {getattr(validation_result, 'warnings', [])}")
            except Exception:
                pass

            # 7) Optionnel: write sheets (désactivé par défaut)
            if self.sheets_connector:
                try:
                    self._write_to_sheets(result)
                except Exception:
                    pass

            # 8) log final
            self._log_final_result(result)
            return result

        except Exception as e:
            self.logger.error(f"[{document_id}] OCR processing failed: {e}", exc_info=True)
            raise

    def _progressive_ocr(self, document, context: ProcessingContext, document_id: str) -> OCRResult:
        """
        Run OCR in progressive levels based on confidence and missing fields.
        """
        # LEVEL 1
        l1 = self.ocr_level1.process(document, context)
        l1.document_id = document_id
        log_ocr_decision(self.logger, document_id, 1, l1.confidence, l1.needs_next_level)

        if not l1.needs_next_level:
            return l1

        # LEVEL 2
        l2 = self.ocr_level2.process(document, context, previous_result=l1)
        l2.document_id = document_id
        log_ocr_decision(self.logger, document_id, 2, l2.confidence, l2.needs_next_level)

        if not l2.needs_next_level:
            return l2

        # LEVEL 3
        l3 = self.ocr_level3.process(document, context, previous_result=l2)
        l3.document_id = document_id
        log_ocr_decision(self.logger, document_id, 3, l3.confidence, l3.needs_next_level)

        return l3

    def _apply_memory_rule(self, document, rule, context: ProcessingContext, document_id: str) -> OCRResult:
        """
        Apply an existing memory rule (Level 3 learned rules)
        """
        try:
            result = self.ocr_level3.apply_rule(document, context, rule)
            result.document_id = document_id
            return result
        except Exception as e:
            self.logger.warning(f"[{document_id}] Memory rule failed, fallback OCR: {e}")
            return self._progressive_ocr(document, context, document_id)

    def _write_to_sheets(self, result: OCRResult):
        try:
            self.sheets_connector.write_ocr_result(result)
        except Exception as e:
            self.logger.warning(f"Write to sheets warning: {e}")

    def _log_final_result(self, result: OCRResult):
        try:
            self.logger.info(
                f"[{result.document_id}] Final Result: "
                f"type={result.document_type} level={result.level} "
                f"confidence={result.confidence} text_len={len(result.text or '')}"
            )
        except Exception:
            pass

    # ==================================================================
    # BOX MAGIC NORMALISATION
    # ==================================================================
    def _boxmagic_normalize_result(self, result: OCRResult, raw_text: str, context: ProcessingContext) -> OCRResult:
        """
        Crée/garantit des clés de fields compatibles avec BOX MAGIC:
        type, numero_facture, societe, client, client_nom, date_doc, ht, tva_montant, ttc, tva_taux,
        nb_personnes, lieu_livraison, prestation_type, prestation_inclus
        """
        def _fv(val, conf=0.8, method="normalized", pattern=None):
            return FieldValue(value=val, confidence=conf, extraction_method=method, pattern=pattern)

        fields = dict(result.fields or {})
        txt = raw_text or ""

        # doc type
        if "type" not in fields:
            fields["type"] = _fv(result.document_type or "autre", conf=0.95, method="derived", pattern="doc_type")

        # societe (si texte contient MARTIN’S TRAITEUR)
        if "societe" not in fields or not getattr(fields.get("societe"), "value", ""):
            if re.search(r"MARTIN[’']?S\s+TRAITEUR", txt, re.IGNORECASE):
                fields["societe"] = _fv("MARTIN’S TRAITEUR", conf=0.92, method="text_detect", pattern="MARTINS_TRAITEUR")
            else:
                # fallback entreprise_source
                if result.entreprise_source:
                    fields["societe"] = _fv(result.entreprise_source, conf=0.75, method="context", pattern="entreprise_source")

        # numero_facture : accepter "reference" ou extraction Level3
        if "numero_facture" not in fields or not getattr(fields.get("numero_facture"), "value", ""):
            ref = fields.get("reference")
            if ref and getattr(ref, "value", ""):
                fields["numero_facture"] = _fv(getattr(ref, "value"), conf=getattr(ref, "confidence", 0.8), method="mapped", pattern="reference->numero_facture")

        # client_nom / client
        if "client_nom" not in fields or not getattr(fields.get("client_nom"), "value", ""):
            c = fields.get("client")
            if c and getattr(c, "value", "") and getattr(c, "value") not in ["Unknown", ""]:
                fields["client_nom"] = _fv(getattr(c, "value"), conf=getattr(c, "confidence", 0.8), method="mapped", pattern="client->client_nom")

        if "client" not in fields:
            if "client_nom" in fields:
                fields["client"] = _fv(getattr(fields["client_nom"], "value"), conf=getattr(fields["client_nom"], "confidence", 0.8), method="alias", pattern="client_nom")

        # tva_taux
        if "tva_taux" not in fields or not getattr(fields.get("tva_taux"), "value", None):
            tr = fields.get("tva_rate")
            if tr and getattr(tr, "value", None) is not None:
                fields["tva_taux"] = _fv(getattr(tr, "value"), conf=getattr(tr, "confidence", 0.85), method="mapped", pattern="tva_rate->tva_taux")

        # date_doc
        if "date_doc" not in fields or not getattr(fields.get("date_doc"), "value", ""):
            m = re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", txt)
            if m:
                fields["date_doc"] = _fv(f"{m.group(1)}/{m.group(2)}/{m.group(3)}", conf=0.9, method="regex", pattern="DD/MM/YYYY")

        # montants ht / tva_montant / ttc
        def _parse_amount(s: str) -> Optional[float]:
            try:
                s = s.replace("€", "").replace(" ", "").replace("\u00A0", "").strip()
                s = s.replace(",", ".")
                return float(s)
            except Exception:
                return None

        if "ht" not in fields or getattr(fields.get("ht"), "value", None) in [None, ""]:
            mh = re.search(r"TARIF\s*HT.*?([0-9\.\s]+[.,][0-9]{2})", txt, re.IGNORECASE)
            if mh:
                val = _parse_amount(mh.group(1))
                if val is not None:
                    fields["ht"] = _fv(val, conf=0.95, method="regex", pattern="TARIF_HT")

        if "tva_montant" not in fields or getattr(fields.get("tva_montant"), "value", None) in [None, ""]:
            mt = re.search(r"TVA\s*[0-9\.,]+\s*%.*?([0-9\.\s]+[.,][0-9]{2})\s*€?", txt, re.IGNORECASE)
            if mt:
                val = _parse_amount(mt.group(1))
                if val is not None:
                    fields["tva_montant"] = _fv(val, conf=0.9, method="regex", pattern="TVA_MONTANT")

        if "ttc" not in fields or getattr(fields.get("ttc"), "value", None) in [None, ""]:
            mtc = re.search(r"TOTAL\s*TTC\s*([0-9\.\s]+[.,][0-9]{2})", txt, re.IGNORECASE)
            if mtc:
                val = _parse_amount(mtc.group(1))
                if val is not None:
                    fields["ttc"] = _fv(val, conf=0.98, method="regex", pattern="TOTAL_TTC")

        # nb_personnes
        if "nb_personnes" not in fields or getattr(fields.get("nb_personnes"), "value", None) in [None, ""]:
            mp = re.search(r"/\s*(\d+)\s*Pers", txt, re.IGNORECASE)
            if mp:
                fields["nb_personnes"] = _fv(int(mp.group(1)), conf=0.9, method="regex", pattern="NB_PERSONNES")

        # prestation_type
        if "prestation_type" not in fields or not getattr(fields.get("prestation_type"), "value", ""):
            mo = re.search(r"Objet\s*:\s*(.+)", txt, re.IGNORECASE)
            if mo:
                fields["prestation_type"] = _fv(mo.group(1).strip(), conf=0.9, method="regex", pattern="OBJET")

        # lieu_livraison
        if "lieu_livraison" not in fields or not getattr(fields.get("lieu_livraison"), "value", ""):
            ml = re.search(r"Lieu\s*:\s*(.+)", txt, re.IGNORECASE)
            if ml:
                fields["lieu_livraison"] = _fv(ml.group(1).strip(), conf=0.88, method="regex", pattern="LIEU")

        # client_nom depuis "A l’attention de"
        if "client_nom" not in fields or not getattr(fields.get("client_nom"), "value", "") or getattr(fields.get("client_nom"), "value") in ["Unknown", ""]:
            mc = re.search(r"A\s+l[’']attention\s+de\s+([A-Z0-9 \-']+)", txt, re.IGNORECASE)
            if mc:
                fields["client_nom"] = _fv(mc.group(1).strip(), conf=0.95, method="regex", pattern="A_L_ATTENTION_DE")
                fields["client"] = _fv(mc.group(1).strip(), conf=0.95, method="alias", pattern="client_nom")

        # numero_facture depuis "Facture FC 2025/143" -> FC000143
        if "numero_facture" not in fields or not getattr(fields.get("numero_facture"), "value", ""):
            mf = re.search(r"Facture\s+FC\s*([0-9]{4})\s*/\s*([0-9]{1,4})", txt, re.IGNORECASE)
            if mf:
                seq = int(mf.group(2))
                fields["numero_facture"] = _fv(f"FC{seq:06d}", conf=0.96, method="regex", pattern="FACTURE_FC_YYYY_SEQ")

        result.fields = fields
        return result
