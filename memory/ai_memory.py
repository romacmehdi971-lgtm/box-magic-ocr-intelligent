"""
AIMemory - stockage local JSON (Cloud Run non persistant)
PHASE 1: création de rule_created exploitable par BOX MAGIC (Sheets IA_MEMORY)
"""

import os
import json
import re
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any


class AIMemory:
    def __init__(self, store_path: str = "memory/rules.json"):
        self.store_path = store_path
        self.rules = []
        self._load()

    def _load(self):
        try:
            if os.path.exists(self.store_path):
                with open(self.store_path, "r", encoding="utf-8") as f:
                    self.rules = json.load(f) or []
        except Exception:
            self.rules = []

    def _save(self):
        try:
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            with open(self.store_path, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def find_matching_rule(self, document, context) -> Optional[Dict[str, Any]]:
        """
        Local match simple (optionnel).
        BOX MAGIC utilisera plutôt son IA_MEMORY Sheet.
        """
        try:
            txt = ""
            try:
                txt = document.get_text() or ""
            except Exception:
                txt = ""

            sig = self._template_signature(txt)
            for r in self.rules:
                if r.get("template_signature") == sig:
                    return r
        except Exception:
            return None
        return None

    def apply(self, fields: dict, doc_type: str, entreprise_source: str):
        """
        API legacy support.
        """
        return None, None

    def create_rule_from_result(self, result, raw_text: str, context) -> Optional[dict]:
        """
        Génère une règle BOX MAGIC compatible IA_MEMORY (Sheets).
        """
        try:
            txt = raw_text or ""
            template_signature = self._template_signature(txt)
            hash_document = self._hash_document(txt)

            def _get(k):
                fv = (result.fields or {}).get(k)
                if not fv:
                    return ""
                return getattr(fv, "value", "") if hasattr(fv, "value") else str(fv)

            rule = {
                "hash_document": hash_document,
                "template_signature": template_signature,
                "created_at": datetime.now().isoformat(),
                "document_type": result.document_type,
                "societe": _get("societe"),
                "client": _get("client_nom") or _get("client"),
                "numero_facture": _get("numero_facture"),
                "date_doc": _get("date_doc"),
                "ttc": _get("ttc"),
                "ht": _get("ht"),
                "tva_taux": _get("tva_taux"),
                "tva_montant": _get("tva_montant"),
                "nb_personnes": _get("nb_personnes"),
                "lieu_livraison": _get("lieu_livraison"),
                "prestation_type": _get("prestation_type"),
                "patterns": {
                    "numero_facture": r"Facture\s+FC\s*[0-9]{4}\s*/\s*[0-9]{1,4}",
                    "client": r"A\s+l[’']attention\s+de\s+([A-Z0-9 \-']+)",
                    "date_doc": r"\b(\d{2})/(\d{2})/(\d{4})\b",
                    "total_ttc": r"TOTAL\s*TTC\s*([0-9\.\s]+[.,][0-9]{2})",
                }
            }

            # stockage local best-effort
            try:
                self.rules.append(rule)
                self._save()
            except Exception:
                pass

            return rule

        except Exception:
            return None

    def _hash_document(self, txt: str) -> str:
        base = re.sub(r"\s+", " ", (txt or "").strip())[:1200]
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def _template_signature(self, txt: str) -> str:
        t = (txt or "").upper()
        bits = []
        if "MARTIN" in t and "TRAITEUR" in t:
            bits.append("MARTINS_TRAITEUR")
        if "BON DE COMMANDE" in t:
            bits.append("BDC")
        if "FACTURE" in t:
            bits.append("FACTURE")
        if "DEVIS" in t:
            bits.append("DEVIS")
        if not bits:
            bits.append("GENERIC")
        return "_".join(bits)
