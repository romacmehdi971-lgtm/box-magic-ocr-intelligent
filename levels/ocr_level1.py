"""
OCR LEVEL 1 - RAPIDE & STABLE
Objectif : Traiter 80% des documents standards en < 2 secondes
"""

import re
import logging
from datetime import datetime
from typing import Dict, Optional, List, Tuple
from copy import deepcopy

logger = logging.getLogger("OCREngine.Level1")


class OCRLevel1:
    """
    OCR Niveau 1 : Extraction rapide et stable
    
    Fonctions :
    - Détection type document (facture, devis, ticket, reçu, BL)
    - Extraction dates (émission, échéance)
    - Extraction montants (HT / TVA / TTC)
    - Extraction TVA si unique et évidente
    - Détection émetteur/destinataire
    - Score de confiance par champ
    - Séparation ENTREPRISE SOURCE / CLIENT / FOURNISSEUR
    """
    
    # Patterns de détection de type
    TYPE_PATTERNS = {
        'facture': [
            r'\bFACTURE\b',
            r'\bINVOICE\b',
            r'\bFACT\.\s*N[°o]',
            r'\bN[°o]\s*FACTURE'
        ],
        'devis': [
            r'\bDEVIS\b',
            r'\bQUOTE\b',
            r'\bESTIMATE\b',
            r'\bDEV\.\s*N[°o]'
        ],
        'ticket': [
            r'\bTICKET\b',
            r'\bRECEIPT\b',
            r'\bTICKET\s*DE\s*CAISSE\b'
        ],
        'recu': [
            r'\bRE[ÇC]U\b',
            r'\bRECEIPT\b',
            r'\bREC\.\s*N[°o]'
        ],
        'bon_livraison': [
            r'\bBON\s*DE\s*LIVRAISON\b',
            r'\bDELIVERY\s*NOTE\b',
            r'\bBL\s*N[°o]'
        ]
    }
    
    # Patterns de dates
    DATE_PATTERNS = [
        r'\b(\d{2})[/-](\d{2})[/-](\d{4})\b',  # DD/MM/YYYY
        r'\b(\d{4})[/-](\d{2})[/-](\d{2})\b',  # YYYY-MM-DD
        r'\b(\d{2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})\b'
    ]
    
    # Patterns de montants
    AMOUNT_PATTERNS = [
        r'(\d+[,\s]\d{3}|\d+)[.,](\d{2})\s*€',  # 1234.56 €
        r'€\s*(\d+[,\s]\d{3}|\d+)[.,](\d{2})',  # € 1234.56
        r'(\d+[,\s]\d{3}|\d+)[.,](\d{2})\s*EUR',  # 1234.56 EUR
    ]
    
    # Patterns TVA
    TVA_PATTERNS = [
        r'TVA\s*(\d+)[.,]?(\d*)\s*%',
        r'VAT\s*(\d+)[.,]?(\d*)\s*%',
        r'(\d+)[.,]?(\d*)\s*%\s*TVA'
    ]
    
    # Mots-clés pour identification
    EMETTEUR_KEYWORDS = [
        'émetteur', 'emetteur', 'fournisseur', 'supplier', 'from', 
        'société', 'company', 'entreprise'
    ]
    
        CLIENT_KEYWORDS = [
        'client', 'customer', 'destinataire', 'to', 'facturé à',
        'billed to', 'ship to', "à l'attention de", "a l'attention de", "à l’attention de", "a l’attention de"
    ]

    
    def __init__(self, config: dict):
        """
        Initialise OCR Level 1
        
        Args:
            config: Configuration globale du système
        """
        self.config = config
        self.confidence_threshold = config.get('ocr_level1', {}).get('confidence_threshold', 0.7)
        logger.info("OCR Level 1 initialized")
    
    def process(self, document, context) -> 'OCRResult':
        """
        Traite un document au niveau 1
        
        Args:
            document: Document chargé (avec méthode get_text())
            context: ProcessingContext avec entreprise source
        
        Returns:
            OCRResult avec champs extraits et scores de confiance
        """
        from ocr_engine import OCRResult, FieldValue
        
        text = document.get_text()
        text_lower = text.lower()
        
        fields = {}
        
        # 1. Détection type document
        doc_type, type_conf = self._detect_document_type(text)
        logger.info(f"Document type detected: {doc_type} (confidence: {type_conf:.2f})")
        
        # 2. Extraction dates
        date_field = self._extract_date(text, text_lower)
        if date_field:
            fields['date_emission'] = date_field
        
        # 3. Extraction montants
        montants = self._extract_amounts(text, text_lower)
        fields.update(montants)
        
        # 4. Extraction TVA
        tva = self._extract_tva(text, text_lower)
        if tva:
            fields['tva_rate'] = tva
        
        # 5. Extraction émetteur/destinataire
        parties = self._extract_parties(text, text_lower, context)
        fields.update(parties)
        
        # 6. Extraction référence document
        reference = self._extract_reference(text, doc_type)
        if reference:
            fields['reference'] = reference
        
        # 7. Calcul confiance globale
        global_confidence = self._calculate_global_confidence(fields)
        
        # 8. Décision niveau suivant
        needs_level2 = self._needs_escalation(fields, global_confidence)
        
        result = OCRResult(
            document_id="",  # Sera rempli par l'engine
            document_type=doc_type,
            level=1,
            confidence=global_confidence,
            entreprise_source=context.source_entreprise,
            fields=fields,
            processing_date=datetime.now(),
            needs_next_level=needs_level2
        )
        
        logger.info(f"OCR Level 1 completed: {len(fields)} fields, confidence: {global_confidence:.2f}")
        
        return result
    
    def _detect_document_type(self, text: str) -> Tuple[str, float]:
        """Détecte le type de document via patterns"""
        text_upper = text.upper()
        
        scores = {}
        for doc_type, patterns in self.TYPE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, text_upper, re.IGNORECASE)
                score += len(matches) * 10  # 10 points par match
            scores[doc_type] = score
        
        if not scores or max(scores.values()) == 0:
            return 'unknown', 0.3
        
        best_type = max(scores, key=scores.get)
        confidence = min(scores[best_type] / 20.0, 1.0)  # Normalisation
        
        return best_type, confidence
    
        def _extract_date(self, text: str, text_lower: str) -> Optional['FieldValue']:
        """Extrait la date d'émission (priorise haut de page et ignore dates de paiement/acompte)"""
        from ocr_engine import FieldValue

        lines = text.split('\n')
        # On priorise le haut du document (factures classiques : date en haut)
        head_lines = lines[:25] if len(lines) > 25 else lines

        # Mots-clés qui indiquent une vraie date de facture (haut de page)
        date_context_keywords = [
            'date', 'le ', 'émise', 'emise', 'facture', 'invoice'
        ]

        # Mots-clés de paiement à exclure (dates d’acompte/solde)
        payment_keywords = [
            'acompte', 'versé', 'verse', 'virement', 'règlement', 'reglement',
            'payé', 'paye', 'solde', 'chèque', 'cheque', 'bnp'
        ]

        def parse_match(match) -> Optional[str]:
            """Retourne YYYY-MM-DD ou None"""
            if not match or len(match) != 3:
                return None
            # Cas numérique
            if str(match[0]).isdigit() and str(match[1]).isdigit():
                if len(str(match[0])) == 4:  # YYYY-MM-DD
                    return f"{match[0]}-{match[1]}-{match[2]}"
                # DD/MM/YYYY
                return f"{match[2]}-{match[1]}-{match[0]}"
            # Mois en lettres
            mois_map = {
                'janvier': '01', 'février': '02', 'fevrier': '02', 'mars': '03',
                'avril': '04', 'mai': '05', 'juin': '06', 'juillet': '07',
                'août': '08', 'aout': '08', 'septembre': '09',
                'octobre': '10', 'novembre': '11', 'décembre': '12', 'decembre': '12'
            }
            mois = mois_map.get(str(match[1]).lower(), None)
            if not mois:
                return None
            return f"{match[2]}-{mois}-{match[0]}"

        # 1) Recherche prioritaire dans le haut de page avec contexte "date/facture/le"
        for line in head_lines:
            ll = line.lower()
            if any(pk in ll for pk in payment_keywords):
                continue
            if not any(ck in ll for ck in date_context_keywords):
                continue

            for pattern in self.DATE_PATTERNS:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    date_str = parse_match(matches[0])
                    if date_str:
                        return FieldValue(
                            value=date_str,
                            confidence=0.93,
                            extraction_method='regex_context_head',
                            pattern=pattern
                        )

        # 2) Fallback : première date trouvée dans le haut de page hors paiement
        for line in head_lines:
            ll = line.lower()
            if any(pk in ll for pk in payment_keywords):
                continue

            for pattern in self.DATE_PATTERNS:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    date_str = parse_match(matches[0])
                    if date_str:
                        return FieldValue(
                            value=date_str,
                            confidence=0.85,
                            extraction_method='regex_head_fallback',
                            pattern=pattern
                        )

        # 3) Dernier fallback : recherche globale (mais toujours exclusion paiement)
        for line in lines:
            ll = line.lower()
            if any(pk in ll for pk in payment_keywords):
                continue

            for pattern in self.DATE_PATTERNS:
                matches = re.findall(pattern, line, re.IGNORECASE)
                if matches:
                    date_str = parse_match(matches[0])
                    if date_str:
                        return FieldValue(
                            value=date_str,
                            confidence=0.75,
                            extraction_method='regex_global_fallback',
                            pattern=pattern
                        )

        return None

    
    def _extract_amounts(self, text: str, text_lower: str) -> Dict[str, 'FieldValue']:
        """Extrait les montants HT, TVA, TTC"""
        from ocr_engine import FieldValue
        
        amounts = {}
        
        # Recherche montants avec contexte
        lines = text.split('\n')
        
                payment_keywords = ['acompte', 'versé', 'verse', 'virement', 'règlement', 'reglement', 'payé', 'paye', 'solde', 'chèque', 'cheque', 'bnp']

        for i, line in enumerate(lines):
            line_lower = line.lower()

            # ⚠️ Ne jamais prendre de montants sur des lignes de paiement/acompte
            if any(pk in line_lower for pk in payment_keywords):
                continue

            # Total TTC (éviter le mot "total" seul, trop dangereux)
            if any(kw in line_lower for kw in ['total ttc', 'net à payer', 'amount due', 'total à payer', 'total a payer']):
                amount = self._extract_amount_from_line(line)
                if amount:
                    amounts['total_ttc'] = FieldValue(
                        value=amount,
                        confidence=0.95,
                        extraction_method='context_keyword',
                        pattern='total_ttc'
                    )

            # Total HT
            elif any(kw in line_lower for kw in ['total ht', 'subtotal', 'hors taxe', 'total hors taxe', 'total hors-taxe']):
                amount = self._extract_amount_from_line(line)
                if amount:
                    amounts['total_ht'] = FieldValue(
                        value=amount,
                        confidence=0.9,
                        extraction_method='context_keyword',
                        pattern='total_ht'
                    )

            # Montant TVA (éviter de matcher "tva" trop large sur d’autres contextes)
            elif any(kw in line_lower for kw in ['montant tva', 'vat amount', 'tva :', 'tva:']):
                amount = self._extract_amount_from_line(line)
                if amount:
                    amounts['montant_tva'] = FieldValue(
                        value=amount,
                        confidence=0.85,
                        extraction_method='context_keyword',
                        pattern='montant_tva'
                    )

        
        # Vérification cohérence HT + TVA = TTC
        if 'total_ht' in amounts and 'montant_tva' in amounts and 'total_ttc' not in amounts:
            ttc_calculated = amounts['total_ht'].value + amounts['montant_tva'].value
            amounts['total_ttc'] = FieldValue(
                value=ttc_calculated,
                confidence=0.85,
                extraction_method='calculation',
                pattern='ht_plus_tva'
            )
        
        return amounts
    
    def _extract_amount_from_line(self, line: str) -> Optional[float]:
        """Extrait un montant d'une ligne"""
        for pattern in self.AMOUNT_PATTERNS:
            matches = re.findall(pattern, line)
            if matches:
                # Prendre le dernier montant de la ligne (souvent le total)
                match = matches[-1]
                if isinstance(match, tuple):
                    integer_part = match[0].replace(',', '').replace(' ', '')
                    decimal_part = match[1] if len(match) > 1 else '00'
                    amount_str = f"{integer_part}.{decimal_part}"
                else:
                    amount_str = match.replace(',', '.')
                
                try:
                    return float(amount_str)
                except ValueError:
                    continue
        
        return None
    
    def _extract_tva(self, text: str, text_lower: str) -> Optional['FieldValue']:
        """Extrait le taux de TVA si unique et évident"""
        from ocr_engine import FieldValue
        
        tva_rates = []
        
        for pattern in self.TVA_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    rate_str = f"{match[0]}.{match[1]}" if match[1] else match[0]
                else:
                    rate_str = match
                
                try:
                    rate = float(rate_str)
                    tva_rates.append(rate)
                except ValueError:
                    continue
        
        # Si un seul taux trouvé, confiance haute
        if len(set(tva_rates)) == 1:
            return FieldValue(
                value=tva_rates[0],
                confidence=0.95,
                extraction_method='regex',
                pattern='tva_unique'
            )
        
        # Si plusieurs taux différents, confiance basse
        elif len(set(tva_rates)) > 1:
            # Prendre le plus fréquent
            most_common = max(set(tva_rates), key=tva_rates.count)
            return FieldValue(
                value=most_common,
                confidence=0.5,
                extraction_method='regex_multiple',
                pattern='tva_multiple'
            )
        
        return None
    
    def _extract_parties(self, text: str, text_lower: str, context) -> Dict[str, 'FieldValue']:
        """
        Extrait émetteur et destinataire
        CRUCIAL : Sépare entreprise source / client / fournisseur
        """
        from ocr_engine import FieldValue
        
        parties = {}
        lines = text.split('\n')
        
        # Patterns entreprise source
        source_patterns = []
        if context.entreprise_config:
            identity = context.entreprise_config.get('identity', {})
            source_patterns.extend(identity.get('logo_patterns', []))
            source_patterns.extend(identity.get('footer_patterns', []))
            source_siret = context.entreprise_config.get('siret', '')
        else:
            source_siret = ''
        
        # Recherche émetteur
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Si ligne contient pattern entreprise source
            is_source_line = any(pattern.lower() in line_lower for pattern in source_patterns)
            is_source_siret = source_siret and source_siret in line
            
            # Émetteur
            if any(kw in line_lower for kw in self.EMETTEUR_KEYWORDS):
                # Extraire nom sur cette ligne ou suivantes
                name = self._extract_name_from_context(lines, i)
                
                if is_source_line or is_source_siret:
                    # C'est l'entreprise source, pas un client
                    parties['emetteur'] = FieldValue(
                        value=context.source_entreprise,
                        confidence=0.95,
                        extraction_method='source_entreprise_match'
                    )
                else:
                    # C'est un fournisseur
                    parties['fournisseur'] = FieldValue(
                        value=name,
                        confidence=0.7,
                        extraction_method='keyword_context'
                    )
            
            # Client
            elif any(kw in line_lower for kw in self.CLIENT_KEYWORDS):
                name = self._extract_name_from_context(lines, i)
                
                if not (is_source_line or is_source_siret):
                    # C'est bien un client, pas l'entreprise source
                    parties['client'] = FieldValue(
                        value=name,
                        confidence=0.8,
                        extraction_method='keyword_context'
                    )
        
        return parties
    
    def _extract_name_from_context(self, lines: List[str], start_index: int) -> str:
        """Extrait un nom depuis le contexte (lignes suivantes)"""
        # Prendre les 3 lignes suivantes
        name_lines = []
        for i in range(start_index + 1, min(start_index + 4, len(lines))):
            line = lines[i].strip()
            if line and not any(kw in line.lower() for kw in ['siret', 'tva', 'adresse', 'tel', 'email']):
                name_lines.append(line)
            if len(name_lines) >= 1:
                break
        
        return ' '.join(name_lines) if name_lines else 'Unknown'
    
    def _extract_reference(self, text: str, doc_type: str) -> Optional['FieldValue']:
        """Extrait la référence du document"""
        from ocr_engine import FieldValue
        
        patterns = {
            'facture': [r'FACTURE\s*N[°o]?\s*:?\s*([A-Z0-9-]+)', r'N[°o]\s*([A-Z0-9-]+)'],
            'devis': [r'DEVIS\s*N[°o]?\s*:?\s*([A-Z0-9-]+)'],
            'ticket': [r'TICKET\s*N[°o]?\s*:?\s*([A-Z0-9-]+)'],
        }
        
        type_patterns = patterns.get(doc_type, [])
        
        for pattern in type_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return FieldValue(
                    value=matches[0],
                    confidence=0.85,
                    extraction_method='regex',
                    pattern=pattern
                )
        
        return None
    
    def _calculate_global_confidence(self, fields: Dict) -> float:
        """Calcule la confiance globale du résultat"""
        if not fields:
            return 0.0
        
        confidences = [
            field.confidence for field in fields.values() 
            if hasattr(field, 'confidence')
        ]
        
        if not confidences:
            return 0.3
        
        # Moyenne pondérée
        return sum(confidences) / len(confidences)
    
    def _needs_escalation(self, fields: Dict, global_confidence: float) -> bool:
        """Détermine si le niveau 2 est nécessaire"""
                # Champs critiques manquants
        critical_fields = ['date_emission', 'total_ttc']
        missing_critical = any(f not in fields or not fields.get(f) for f in critical_fields)

        # Confiance trop basse
        low_confidence = global_confidence < self.confidence_threshold

        # ============================================================
        # ✅ FORCE_OCR2_IF_RISK (MINIMAL, RÉVERSIBLE)
        # Objectif : si des champs sont "remplis" mais manifestement toxiques
        # (ex: client="Acompte versé...", reference/numero="Services"),
        # on force OCR2 pour éviter un arrêt en LEVEL 1.
        # ============================================================
        force_ocr2_if_risk = False
        try:
            # Client suspect = ligne de paiement/acompte
            client_val = ""
            if "client" in fields and fields.get("client") and hasattr(fields["client"], "value"):
                client_val = str(fields["client"].value or "")
            client_low = client_val.lower()

            paiement_keywords = ["acompte", "versé", "verse", "virement", "reglement", "règlement", "payé", "paye", "solde"]
            if client_low and any(k in client_low for k in paiement_keywords):
                force_ocr2_if_risk = True

            # Reference suspecte = "Services" ou sans chiffres
            ref_val = ""
            if "reference" in fields and fields.get("reference") and hasattr(fields["reference"], "value"):
                ref_val = str(fields["reference"].value or "")
            ref_low = ref_val.lower()

            if ref_low in ["service", "services"]:
                force_ocr2_if_risk = True
            elif ref_val and not re.search(r"\d", ref_val):
                force_ocr2_if_risk = True

        except Exception:
            pass

        return missing_critical or low_confidence or force_ocr2_if_risk

