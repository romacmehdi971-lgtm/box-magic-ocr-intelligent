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
        'billed to', 'ship to'
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
        text_original = text  # Garder l'original BRUT pour le JSON final
        
        # [FIX] Normaliser espaces (PyPDF2 peut ajouter espaces entre lettres)
        # "F a c t u r e" → "Facture"
        text = re.sub(r'(?<=[a-zA-Z])\s(?=[a-zA-Z])', '', text)  # Retirer espaces ENTRE lettres
        text = re.sub(r'\s+', ' ', text)  # Normaliser espaces multiples
        
        text_lower = text.lower()
        
        fields = {}
        
        # [MIROIR] 0. AJOUTER TEXTE OCR BRUT COMPLET (PRIORITAIRE)
        fields['texte_ocr_brut'] = FieldValue(
            value=text_original,
            confidence=1.0,
            extraction_method='document_text',
            pattern='raw_text'
        )
        
        # [FIX] 1. Type document déjà détecté par engine (type_detector.py)
        # On ne redétecte pas ici pour éviter les conflits
        # Le type sera assigné par l'engine après ce traitement
        doc_type = "unknown"  # Valeur temporaire, sera écrasée
        logger.info(f"[OCR1] Type document sera assigné par l'engine (type_detector)")
        
        # 2. Extraction dates
        date_field = self._extract_date(text, text_lower)
        if date_field:
            fields['date_emission'] = date_field
        
        # [MIROIR] 2b. Extraction date échéance
        date_echeance = self._extract_date_echeance(text, text_lower)
        if date_echeance:
            fields['date_echeance'] = date_echeance
        
        # 3. Extraction montants
        montants = self._extract_amounts(text, text_lower)
        fields.update(montants)
        
        # 4. Extraction TVA
        tva = self._extract_tva(text, text_lower)
        if tva:
            fields['tva_rate'] = tva
        
        # [MIROIR] 5. Extraction COMPLÈTE entreprise émettrice (PRIORITAIRE)
        # IMPORTANT : utiliser text_original (avec espaces PyPDF2) pour détecter les lignes
        emetteur_full = self._extract_emetteur_complet(text_original, text_lower, context)
        fields.update(emetteur_full)
        
        # [MIROIR] 6. Extraction COMPLÈTE client/destinataire
        client_full = self._extract_client_complet(text, text_lower)
        fields.update(client_full)
        
        # 7. Extraction référence document
        reference = self._extract_reference(text, doc_type)
        if reference:
            fields['numero_facture'] = reference  # Renommer pour clarté
        
        # [MIROIR] 8. Extraction SIRET
        siret = self._extract_siret(text)
        if siret:
            fields['siret'] = siret
        
        # [MIROIR] 9. Extraction TVA intracommunautaire
        num_tva = self._extract_numero_tva(text)
        if num_tva:
            fields['numero_tva_intracommunautaire'] = num_tva
        
        # [MIROIR] 10. Extraction adresses
        adresses = self._extract_adresses(text)
        fields.update(adresses)
        
        # [MIROIR] 11. Extraction devise
        devise = self._extract_devise(text)
        if devise:
            fields['devise'] = devise
        
        # 12. Calcul confiance globale
        global_confidence = self._calculate_global_confidence(fields)
        
        # 13. Décision niveau suivant
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
        """Extrait la date d'émission - MÉTHODE ROBUSTE AVEC CONTEXTE"""
        from ocr_engine import FieldValue
        
        # PATTERNS AVEC CONTEXTE (prioritaires)
        date_context_patterns = [
            r"(?:Date\s*d[''']?émission|Date\s*de\s*facture|Invoice\s*date|Date)\s*:?\s*(\d{1,2})\s*[/-]\s*(\d{1,2})\s*[/-]\s*(\d{4})",
            r"(?:Date\s*d[''']?émission|Date\s*de\s*facture|Invoice\s*date|Date)\s*:?\s*(\d{1,2})\s+(janvier|février|f[ée]vrier|mars|avril|mai|juin|juillet|ao[ûu]t|septembre|octobre|novembre|d[ée]cembre)\s+(\d{4})",
            r"(?:Date\s*d[''']?émission|Date\s*de\s*facture|Invoice\s*date|Date)\s*:?\s*(\d{4})\s*[/-]\s*(\d{1,2})\s*[/-]\s*(\d{1,2})",
        ]
        
        for pattern in date_context_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                groups = match.groups()
                # Parser selon format
                if len(groups) == 3:
                    if groups[0].isdigit() and groups[1].isdigit() and groups[2].isdigit():
                        # Format numérique
                        if len(groups[0]) == 4:  # YYYY-MM-DD
                            date_str = f"{groups[0]}-{groups[1].zfill(2)}-{groups[2].zfill(2)}"
                        else:  # DD/MM/YYYY ou DD-MM-YYYY
                            date_str = f"{groups[2]}-{groups[1].zfill(2)}-{groups[0].zfill(2)}"
                    else:
                        # Format avec mois en lettres
                        mois_map = {
                            'janvier': '01', 'février': '02', 'fevrier': '02', 'mars': '03',
                            'avril': '04', 'mai': '05', 'juin': '06',
                            'juillet': '07', 'août': '08', 'aout': '08', 'septembre': '09',
                            'octobre': '10', 'novembre': '11', 'décembre': '12', 'decembre': '12'
                        }
                        mois = mois_map.get(groups[1].lower(), '01')
                        date_str = f"{groups[2]}-{mois}-{groups[0].zfill(2)}"
                    
                    return FieldValue(
                        value=date_str,
                        confidence=0.95,
                        extraction_method='regex_with_context',
                        pattern='date_emission_context'
                    )
        
        # FALLBACK: patterns génériques (confiance plus faible)
        for pattern in self.DATE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Prendre la première date trouvée
                match = matches[0]
                
                # Parser selon format
                if len(match) == 3:
                    if match[0].isdigit() and match[1].isdigit():
                        # Format numérique
                        if len(match[0]) == 4:  # YYYY-MM-DD
                            date_str = f"{match[0]}-{match[1]}-{match[2]}"
                        else:  # DD/MM/YYYY
                            date_str = f"{match[2]}-{match[1]}-{match[0]}"
                    else:
                        # Format avec mois en lettres
                        mois_map = {
                            'janvier': '01', 'février': '02', 'mars': '03',
                            'avril': '04', 'mai': '05', 'juin': '06',
                            'juillet': '07', 'août': '08', 'septembre': '09',
                            'octobre': '10', 'novembre': '11', 'décembre': '12'
                        }
                        mois = mois_map.get(match[1].lower(), '01')
                        date_str = f"{match[2]}-{mois}-{match[0]}"
                    
                    return FieldValue(
                        value=date_str,
                        confidence=0.75,
                        extraction_method='regex',
                        pattern=pattern
                    )
        
        return None
    
    def _extract_amounts(self, text: str, text_lower: str) -> Dict[str, 'FieldValue']:
        """Extrait les montants HT, TVA, TTC - MÉTHODE ROBUSTE AVEC REGEX"""
        from ocr_engine import FieldValue
        
        amounts = {}
        
        # ========================================================================
        # PATTERNS REGEX POUR MONTANTS (TOUS FORMATS)
        # ========================================================================
        
        # Pattern montant : 140.23 ou 140,23 ou 24.99 ou 24,99 (avec espaces possibles)
        amount_pattern = r'([\d\s]+)[,.]([\d]{2})'
        
        # PATTERN 1: Total TTC / Total / Montant dû / Amount due
        ttc_patterns = [
            r'(?:Total\s*TTC|TOTAL\s*TTC|Total|TOTAL|Montant\s*d[ûu]|Amount\s*due|Net\s*[àa]\s*payer)\s*:?\s*' + amount_pattern,
            r'(?:TTC|TOTAL)\s*:?\s*' + amount_pattern,
            r'MONTANT\s*=?\s*' + amount_pattern,  # Pour Carrefour
        ]
        
        for pattern in ttc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and 'total_ttc' not in amounts:
                montant_str = match.group(1).replace(' ', '') + '.' + match.group(2)
                try:
                    amounts['total_ttc'] = FieldValue(
                        value=float(montant_str),
                        confidence=0.95,
                        extraction_method='regex_pattern',
                        pattern='ttc_pattern'
                    )
                    break
                except:
                    pass
        
        # PATTERN 2: Total HT / Subtotal / Hors taxe
        ht_patterns = [
            r'(?:Total\s*HT|TOTAL\s*HT|Total\s*hors\s*taxe[s]?|Subtotal|Sous-total)\s*:?\s*' + amount_pattern,
            r'(?:HT|Hors\s*taxe)\s*:?\s*' + amount_pattern,
        ]
        
        for pattern in ht_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and 'total_ht' not in amounts:
                montant_str = match.group(1).replace(' ', '') + '.' + match.group(2)
                try:
                    amounts['total_ht'] = FieldValue(
                        value=float(montant_str),
                        confidence=0.90,
                        extraction_method='regex_pattern',
                        pattern='ht_pattern'
                    )
                    break
                except:
                    pass
        
        # PATTERN 3: TVA / Montant TVA / VAT Amount
        tva_patterns = [
            r'(?:Montant\s*TVA|TVA|VAT\s*Amount)\s*:?\s*' + amount_pattern,
            r'(?:TVA|VAT)\s*:?\s*' + amount_pattern,
        ]
        
        for pattern in tva_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match and 'montant_tva' not in amounts:
                montant_str = match.group(1).replace(' ', '') + '.' + match.group(2)
                try:
                    amounts['montant_tva'] = FieldValue(
                        value=float(montant_str),
                        confidence=0.85,
                        extraction_method='regex_pattern',
                        pattern='tva_pattern'
                    )
                    break
                except:
                    pass
        
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
        """Extrait la référence du document - MÉTHODE ROBUSTE AVEC NETTOYAGE"""
        from ocr_engine import FieldValue
        
        # [FIX] Nettoyer le texte : retirer espaces entre lettres/chiffres
        # "N u m é r o  d e  f a c t u r e N 8 W Y" -> "Numéro de facture N8WY"
        text_clean = re.sub(r'(?<=[A-Za-z0-9])\s+(?=[A-Za-z0-9])', '', text)
        
        # PATTERNS GÉNÉRIQUES + SPÉCIFIQUES PAR TYPE
        patterns_all = [
            # Patterns avec label explicite (haute confiance)
            (r'N[°oúu]m[eé]ro\s*(?:de\s*)?facture\s*:?\s*([A-Z0-9\-_\u0000\s]{3,20})', 0.95, 'facture_label_fr'),
            (r'Invoice\s+Number\s*:?\s*([A-Z0-9\-_\u0000\s]{3,20})', 0.95, 'invoice_number'),
            (r'N[°oú]\s*(?:de\s*)?facture\s*:?\s*([A-Z0-9\-_\u0000\s]{3,20})', 0.95, 'facture_label'),
            (r'FACTURE\s*N[°oú]?\s*:?\s*([A-Z0-9\-_\u0000\s]{3,20})', 0.90, 'facture_prefix'),
            (r'N[°oú]\s*FACTURE\s*:?\s*([A-Z0-9\-_\u0000\s]{3,20})', 0.90, 'facture_prefix'),
            
            # Patterns pour tickets
            (r'N[°oú]\s*(?:de\s*)?ticket\s*:?\s*([A-Z0-9\-_]{3,20})', 0.90, 'ticket_label'),
            (r'TICKET\s*N[°oú]?\s*:?\s*([A-Z0-9\-_]{3,20})', 0.85, 'ticket_prefix'),
            
            # Patterns pour devis
            (r'N[°oú]\s*(?:de\s*)?devis\s*:?\s*([A-Z0-9\-_]{3,20})', 0.90, 'devis_label'),
            (r'DEVIS\s*N[°oú]?\s*:?\s*([A-Z0-9\-_]{3,20})', 0.85, 'devis_prefix'),
            
            # Pattern générique: N° suivi de code alphanumérique (>= 5 caractères)
            (r'N[°oú]\s*:?\s*([A-Z0-9\-_]{5,20})', 0.70, 'generic_number'),
        ]
        
        # Essayer tous les patterns sur le texte nettoyé
        for pattern, confidence, pattern_name in patterns_all:
            match = re.search(pattern, text_clean, re.IGNORECASE)
            if match:
                numero = match.group(1).strip()\n                # Nettoyer le numéro extrait (retirer \u0000, espaces multiples)\n                numero = re.sub(r'[\u0000\\s]+', '', numero)\n                # Vérifier longueur minimale (au moins 3 caractères)\n                if len(numero) >= 3 and len(numero) <= 20:\n                    return FieldValue(\n                        value=numero,\n                        confidence=confidence,\n                        extraction_method='regex_pattern_cleaned',\n                        pattern=pattern_name\n                    )\n        \n        return None
    
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
        missing_critical = any(f not in fields for f in critical_fields)
        
        # Confiance trop basse
        low_confidence = global_confidence < self.confidence_threshold
        
        return missing_critical or low_confidence
    
    # ===== NOUVELLES MÉTHODES D'EXTRACTION COMPLÈTE (MIROIR) =====
    
    def _extract_date_echeance(self, text: str, text_lower: str) -> Optional['FieldValue']:
        """Extrait la date d'échéance"""
        from ocr_engine import FieldValue
        
        patterns = [
            r'(?:échéance|due\s+date|payment\s+due)[\s:]+' + p for p in self.DATE_PATTERNS
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                match = matches[0]
                if len(match) == 3:
                    if match[0].isdigit() and match[1].isdigit():
                        if len(match[0]) == 4:  # YYYY-MM-DD
                            date_str = f"{match[0]}-{match[1]}-{match[2]}"
                        else:  # DD/MM/YYYY
                            date_str = f"{match[2]}-{match[1]}-{match[0]}"
                    else:
                        # Format avec mois en lettres
                        mois_map = {
                            'janvier': '01', 'février': '02', 'mars': '03',
                            'avril': '04', 'mai': '05', 'juin': '06',
                            'juillet': '07', 'août': '08', 'septembre': '09',
                            'octobre': '10', 'novembre': '11', 'décembre': '12'
                        }
                        mois = mois_map.get(match[1].lower(), '01')
                        date_str = f"{match[2]}-{mois}-{match[0]}"
                    
                    return FieldValue(
                        value=date_str,
                        confidence=0.85,
                        extraction_method='regex',
                        pattern=pattern
                    )
        
        return None
    
    def _extract_emetteur_complet(self, text: str, text_lower: str, context) -> Dict[str, 'FieldValue']:
        """Extrait TOUTES les infos de l'émetteur (nom, adresse, SIRET, etc.) - MÉTHODE ROBUSTE"""
        from ocr_engine import FieldValue
        
        result = {}
        lines = text.split('\n')
        
        # ========================================================================
        # PATTERNS D'ÉMETTEURS CONNUS (COIN HAUT GAUCHE - 5-10 premières lignes)
        # ========================================================================
        EMETTEURS_CONNUS = {
            # Grandes surfaces / Magasins
            'CARREFOUR': ['carrefour', 'destcarrefour', 'aybaté', 'baie-mahault', 'destreland'],
            'BRICODIA': ['bricodia', 'brico dia'],
            'WELDOM': ['weldom'],
            'INTERMARCHE': ['intermarche', 'intermarché'],
            'LECLERC': ['leclerc', 'e.leclerc', 'e leclerc'],
            
            # Restaurants / Traiteurs
            'MARTINS_TRAITEUR': ["martin's traiteur", 'martins traiteur', 'martin traiteur'],
            
            # Entreprises B2B
            'MAINFUNC_PTE_LTD': ['mainfunc', 'main func', 'pte ltd', 'pte. ltd.'],
            'GENSPARK': ['genspark'],
        }
        
        # ÉTAPE 1: Recherche par patterns connus dans les 10 premières lignes (prioritaire)
        text_haut = ' '.join(lines[:10]).lower()
        
        for nom_normalise, patterns in EMETTEURS_CONNUS.items():
            for pattern in patterns:
                if pattern.lower() in text_haut:
                    # Trouver la ligne exacte pour confiance accrue
                    for i, line in enumerate(lines[:10]):
                        if pattern.lower() in line.lower():
                            result['emetteur_nom'] = FieldValue(
                                value=nom_normalise,
                                confidence=0.95,
                                extraction_method='known_pattern_match',
                                pattern=f"Ligne {i+1}: {pattern}",
                                position={'line': i+1, 'zone': 'top_left'}
                            )
                            logger.info(f"[OCR1] Émetteur détecté PAR PATTERN CONNU: {nom_normalise}")
                            return result  # Retour immédiat si match connu
        
        # ÉTAPE 2: Fallback - Recherche ligne avec suffixe d'entreprise (PTE, LTD, SARL, etc.)
        for i, line in enumerate(lines[:20]):
            line_clean = line.strip()
            # Retirer caractères nulls
            line_clean = re.sub(r'[\x00-\x1F]', '', line_clean)
            line_clean = re.sub(r'\s+', ' ', line_clean)  # Normaliser espaces multiples
            # [FIX PyPDF2] Retirer espaces ENTRE lettres ("M a i n F u n c" → "MainFunc")
            line_clean = re.sub(r'(?<=[a-zA-Z])\s(?=[a-zA-Z])', '', line_clean)
            
            # Pattern: ligne contenant des suffixes d'entreprise ET moins de 100 caractères (pour éviter les paragraphes)
            if (re.search(r'\b(PTE\.?|LTD\.?|SARL|SAS|SA|Inc\.?|LLC|Corp\.?|Company|GmbH)\b', line_clean, re.IGNORECASE) 
                and len(line_clean) < 100  # Ligne courte = nom d'entreprise
                and len(line_clean) > 5):  # Au moins 5 caractères
                
                result['emetteur_nom'] = FieldValue(
                    value=line_clean,
                    confidence=0.75,
                    extraction_method='line_pattern_match',
                    pattern='company_suffix_in_line',
                    position={'line': i+1}
                )
                logger.info(f"[OCR1] Émetteur détecté PAR SUFFIXE: {line_clean}")
                return result
        
        # ÉTAPE 3: Si RIEN trouvé, utiliser contexte MAIS avec confiance FAIBLE
        if context.source_entreprise and context.source_entreprise != "UNKNOWN":
            result['emetteur_nom'] = FieldValue(
                value=context.source_entreprise,
                confidence=0.50,
                extraction_method='context_fallback',
                pattern='source_entreprise'
            )
            logger.warning(f"[OCR1] Émetteur NON DÉTECTÉ, fallback contexte: {context.source_entreprise}")
        else:
            logger.warning("[OCR1] Émetteur NON DÉTECTÉ et aucun contexte disponible")
        
        return result
    
    def _extract_client_complet(self, text: str, text_lower: str) -> Dict[str, 'FieldValue']:
        """Extrait TOUTES les infos du client"""
        from ocr_engine import FieldValue
        
        result = {}
        
        # Patterns client
        client_patterns = [
            r'(?:Client|À|To|Bill\s+to|Facturé\s+à)[\s:]+([A-Z][A-Za-z\s-]+)',
            r'(?:Destinataire)[\s:]+([A-Z][A-Za-z\s-]+)',
        ]
        
        for pattern in client_patterns:
            match = re.search(pattern, text, re.MULTILINE | re.IGNORECASE)
            if match:
                nom_client = match.group(1).strip()
                result['client_nom'] = FieldValue(
                    value=nom_client,
                    confidence=0.85,
                    extraction_method='regex_pattern',
                    pattern=pattern
                )
                break
        
        return result
    
    def _extract_siret(self, text: str) -> Optional['FieldValue']:
        """Extrait le SIRET (14 chiffres) - MÉTHODE ROBUSTE"""
        from ocr_engine import FieldValue
        
        # PATTERN 1: SIRET avec label (SIRET: xxxxx)
        pattern_label = r'(?:SIRET|Siret)[\s:]+([\ d\s]{14,})'
        match = re.search(pattern_label, text, re.IGNORECASE)
        
        if match:
            siret = re.sub(r'\s', '', match.group(1))[:14]  # Retirer espaces, garder 14 chiffres
            if len(siret) == 14 and siret.isdigit():
                return FieldValue(
                    value=siret,
                    confidence=0.95,
                    extraction_method='regex_with_label',
                    pattern=pattern_label
                )
        
        # PATTERN 2: 14 chiffres consécutifs (sans label) - confiance plus faible
        pattern_brut = r'\b(\d{14})\b'
        match = re.search(pattern_brut, text)
        
        if match:
            siret = match.group(1)
            return FieldValue(
                value=siret,
                confidence=0.80,  # Confiance plus faible sans label
                extraction_method='regex_numeric',
                pattern='14_consecutive_digits'
            )
        
        return None
    
    def _extract_numero_tva(self, text: str) -> Optional['FieldValue']:
        """Extrait le numéro de TVA intracommunautaire"""
        from ocr_engine import FieldValue
        
        patterns = [
            r'(?:TVA|VAT|N°\s*TVA)[\s:]+([A-Z]{2}\d+)',
            r'(?:EU\s*OSS\s*VAT|EU\s*VAT)[\s:]+([A-Z]{2}\d+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return FieldValue(
                    value=match.group(1),
                    confidence=0.90,
                    extraction_method='regex',
                    pattern=pattern
                )
        
        return None
    
    def _extract_adresses(self, text: str) -> Dict[str, 'FieldValue']:
        """Extrait les adresses (émetteur et client)"""
        from ocr_engine import FieldValue
        
        result = {}
        
        # Pattern adresse générique : numéro + rue/road/avenue
        adresse_pattern = r'(\d+[,\s]+[A-Z][A-Za-z\s]+(?:Street|Road|Avenue|Rue|Boulevard|Rd|Ave)[^,\n]*(?:,\s*[A-Z\s]+)?(?:,\s*[A-Z]{2}\s*\d+)?)'
        
        matches = re.findall(adresse_pattern, text, re.IGNORECASE)
        
        if matches:
            # Première adresse = émetteur
            result['adresse_emetteur'] = FieldValue(
                value=matches[0].strip(),
                confidence=0.75,
                extraction_method='regex',
                pattern=adresse_pattern
            )
            
            # Deuxième adresse = client (si présente)
            if len(matches) > 1:
                result['adresse_client'] = FieldValue(
                    value=matches[1].strip(),
                    confidence=0.70,
                    extraction_method='regex',
                    pattern=adresse_pattern
                )
        
        return result
    
    def _extract_devise(self, text: str) -> Optional['FieldValue']:
        """Extrait la devise utilisée"""
        from ocr_engine import FieldValue
        
        devise_map = {
            '€': 'EUR',
            'EUR': 'EUR',
            '$': 'USD',
            'USD': 'USD',
            '£': 'GBP',
            'GBP': 'GBP',
        }
        
        for symbole, code in devise_map.items():
            if symbole in text or code in text:
                return FieldValue(
                    value=code,
                    confidence=0.90,
                    extraction_method='symbol_detection',
                    pattern=symbole
                )
        
        return None
