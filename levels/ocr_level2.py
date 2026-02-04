"""
OCR LEVEL 2 - ANALYSE APPROFONDIE
Objectif : Améliorer les résultats OCR1 sans les dégrader
"""

import re
import logging
from datetime import datetime
from typing import Dict, Optional, List
from copy import deepcopy

logger = logging.getLogger("OCREngine.Level2")


class OCRLevel2:
    """
    OCR Niveau 2 : Analyse approfondie et amélioration ciblée
    
    Déclenché si :
    - Confiance OCR1 < seuil (défaut 0.7)
    - Champs critiques manquants
    - Ambiguïtés détectées
    
    Fonctions :
    - Analyse contextuelle avancée
    - Recherche croisée d'informations
    - Amélioration champ par champ
    - Préservation des champs fiables OCR1
    - Calculs et vérifications de cohérence
    """
    
    def __init__(self, config: dict):
        """
        Initialise OCR Level 2
        
        Args:
            config: Configuration globale du système
        """
        self.config = config
        self.confidence_threshold = config.get('ocr_level2', {}).get('confidence_threshold', 0.6)
        logger.info("OCR Level 2 initialized")
    
    def process(self, document, ocr1_result: 'OCRResult', context) -> 'OCRResult':
        """
        Améliore les résultats OCR1
        
        Args:
            document: Document original
            ocr1_result: Résultat OCR Level 1
            context: ProcessingContext
        
        Returns:
            OCRResult amélioré
        """
        from ocr_engine import OCRResult, FieldValue
        
        # 1. PRÉSERVATION des résultats OCR1
        fields = deepcopy(ocr1_result.fields)
        improved_fields = []
        
        text = document.get_text()
        text_lower = text.lower()
        
        # 2. Extraction contexte avancé
        context_data = self._extract_advanced_context(text, text_lower)
        
        # 3. Amélioration ciblée des champs faibles
        for field_name, field_value in fields.items():
            if field_value.confidence < 0.7 or field_value.value is None:
                logger.debug(f"Attempting to improve field: {field_name} (current confidence: {field_value.confidence:.2f})")
                
                improved = self._improve_field(
                    field_name, 
                    document, 
                    context_data,
                    ocr1_result.document_type
                )
                
                if improved and improved.confidence > field_value.confidence:
                    fields[field_name] = improved
                    improved_fields.append(field_name)
                    logger.info(f"Field improved: {field_name} (confidence: {field_value.confidence:.2f} → {improved.confidence:.2f})")
        
        # 4. Recherche champs manquants critiques
        missing_fields = self._find_missing_critical_fields(fields, ocr1_result.document_type)
        for field_name in missing_fields:
            logger.debug(f"Attempting to extract missing field: {field_name}")
            
            extracted = self._extract_missing_field(
                field_name,
                document,
                context_data,
                ocr1_result.document_type
            )
            
            if extracted:
                fields[field_name] = extracted
                improved_fields.append(field_name)
                logger.info(f"Missing field extracted: {field_name} (confidence: {extracted.confidence:.2f})")
        
        # 4.5 🎯 ENRICHISSEMENT SPÉCIAL TICKET CB (SNIPER MODE)
        if ocr1_result.document_type == "TICKET":
            ticket_enriched = self._enrich_ticket_cb(text, fields, context_data)
            for field_name, field_value in ticket_enriched.items():
                # NE PAS ÉCRASER les champs déjà renseignés
                if field_name not in fields or not fields[field_name].value:
                    fields[field_name] = field_value
                    if field_name not in improved_fields:
                        improved_fields.append(field_name)
                    logger.info(f"TICKET enrichment: {field_name} = {field_value.value} (confidence: {field_value.confidence:.2f})")
        
            # Ticket-specific normalization (prevent SIREN/SIRET leaking into client)
            try:
                client_v = (fields.get("client").value if fields.get("client") else "") or ""
                if "siren" in str(client_v).lower():
                    # move to fournisseur_siret if empty
                    if not fields.get("fournisseur_siret") or not fields.get("fournisseur_siret").value:
                        fields["fournisseur_siret"] = FieldValue(
                            value=str(client_v).replace("~", "").strip(),
                            confidence=fields.get("client").confidence if fields.get("client") else 0.6,
                            extraction_method="ticket_postprocess",
                            position=None,
                            pattern=None
                        )
                    # client should be the entreprise_source
                    if context_data.get("entreprise_source"):
                        fields["client"] = FieldValue(
                            value=context_data.get("entreprise_source"),
                            confidence=0.9,
                            extraction_method="ticket_postprocess",
                            position=None,
                            pattern=None
                        )
                # ensure fournisseur is present (fallback to societe if available)
                if (not fields.get("fournisseur") or not fields.get("fournisseur").value) and fields.get("societe") and fields.get("societe").value:
                    fields["fournisseur"] = fields.get("societe")
            except Exception:
                pass


        # 5. Croisement et validation
        fields = self._cross_validate_fields(fields, context_data)
        
        # 6. Calculs manquants (HT ↔ TTC ↔ TVA)
        if self._can_calculate_missing_values(fields):
            calculated_fields = self._calculate_missing_amounts(fields)
            for field_name, field_value in calculated_fields.items():
                if field_name not in fields or fields[field_name].confidence < field_value.confidence:
                    fields[field_name] = field_value
                    if field_name not in improved_fields:
                        improved_fields.append(field_name)
                    logger.info(f"Field calculated: {field_name} = {field_value.value}")
        
        # 7. Calcul confiance globale
        global_confidence = self._calculate_global_confidence(fields)
        
        # 8. Décision niveau suivant
        needs_level3 = self._needs_escalation(
            fields, 
            global_confidence, 
            document,
            context
        )
        
        result = OCRResult(
            document_id=ocr1_result.document_id,
            document_type=ocr1_result.document_type,
            level=2,
            confidence=global_confidence,
            entreprise_source=context.source_entreprise,
            fields=fields,
            processing_date=datetime.now(),
            needs_next_level=needs_level3,
            improved_fields=improved_fields
        )
        
        logger.info(f"OCR Level 2 completed: improved {len(improved_fields)} fields, confidence: {global_confidence:.2f}")
        
        return result
    
    def _extract_advanced_context(self, text: str, text_lower: str) -> dict:
        """
        Extrait le contexte avancé du document
        
        Returns:
            dict avec structure, zones, patterns détectés
        """
        lines = text.split('\n')
        
        context = {
            'lines': lines,
            'total_lines': len(lines),
            'header': lines[:5] if len(lines) >= 5 else lines,
            'footer': lines[-5:] if len(lines) >= 5 else lines,
            'line_groups': self._group_lines_by_proximity(lines),
            'tables': self._detect_tables(lines),
            'siret_locations': self._find_siret_locations(text),
            'amounts_map': self._map_all_amounts(lines),
            'dates_map': self._map_all_dates(lines)
        }
        
        return context
    
    def _group_lines_by_proximity(self, lines: List[str]) -> List[List[str]]:
        """Groupe les lignes proches (même section)"""
        groups = []
        current_group = []
        
        for line in lines:
            if line.strip():
                current_group.append(line)
            else:
                if current_group:
                    groups.append(current_group)
                    current_group = []
        
        if current_group:
            groups.append(current_group)
        
        return groups
    
    def _detect_tables(self, lines: List[str]) -> List[dict]:
        """Détecte les structures tabulaires"""
        tables = []
        in_table = False
        current_table = []
        
        for i, line in enumerate(lines):
            # Détection tableau : plusieurs espaces/tabs ou alignement
            has_multiple_columns = len(re.split(r'\s{2,}|\t', line.strip())) >= 3
            
            if has_multiple_columns:
                if not in_table:
                    in_table = True
                    current_table = [line]
                else:
                    current_table.append(line)
            else:
                if in_table and current_table:
                    tables.append({
                        'lines': current_table,
                        'start_index': i - len(current_table),
                        'end_index': i - 1
                    })
                    current_table = []
                in_table = False
        
        return tables
    
    def _find_siret_locations(self, text: str) -> List[dict]:
        """Localise tous les SIRET dans le document"""
        siret_pattern = r'\b\d{3}\s?\d{3}\s?\d{3}\s?\d{5}\b'
        locations = []
        
        for match in re.finditer(siret_pattern, text):
            siret = match.group().replace(' ', '')
            locations.append({
                'siret': siret,
                'position': match.start(),
                'context': text[max(0, match.start()-50):match.end()+50]
            })
        
        return locations
    
    def _map_all_amounts(self, lines: List[str]) -> List[dict]:
        """Cartographie tous les montants avec leur contexte"""
        amounts_map = []
        
        amount_pattern = r'(\d+[,\s]\d{3}|\d+)[.,](\d{2})\s*€?'
        
        for i, line in enumerate(lines):
            for match in re.finditer(amount_pattern, line):
                amount_str = match.group()
                try:
                    # Parse amount
                    amount_clean = amount_str.replace(',', '.').replace(' ', '').replace('€', '').strip()
                    amount_value = float(amount_clean)
                    
                    amounts_map.append({
                        'value': amount_value,
                        'line_index': i,
                        'line_text': line,
                        'position': match.start()
                    })
                except ValueError:
                    continue
        
        return amounts_map
    
    def _map_all_dates(self, lines: List[str]) -> List[dict]:
        """Cartographie toutes les dates avec leur contexte"""
        dates_map = []
        
        date_patterns = [
            r'\b(\d{2})[/-](\d{2})[/-](\d{4})\b',
            r'\b(\d{4})[/-](\d{2})[/-](\d{2})\b'
        ]
        
        for i, line in enumerate(lines):
            for pattern in date_patterns:
                for match in re.finditer(pattern, line):
                    dates_map.append({
                        'raw': match.group(),
                        'line_index': i,
                        'line_text': line,
                        'position': match.start()
                    })
        
        return dates_map
    
    def _improve_field(self, field_name: str, document, context_data: dict, doc_type: str) -> Optional['FieldValue']:
        """Améliore un champ spécifique"""
        from ocr_engine import FieldValue
        
        # Stratégies d'amélioration par type de champ
        if 'date' in field_name:
            return self._improve_date_field(field_name, context_data)
        
        elif 'montant' in field_name or 'total' in field_name:
            return self._improve_amount_field(field_name, context_data)
        
        elif field_name in ['client', 'fournisseur']:
            return self._improve_party_field(field_name, document, context_data)
        
        elif 'tva' in field_name:
            return self._improve_tva_field(context_data)
        
        return None
    
    def _improve_date_field(self, field_name: str, context_data: dict) -> Optional['FieldValue']:
        """Améliore l'extraction de date"""
        from ocr_engine import FieldValue
        
        dates_map = context_data.get('dates_map', [])
        
        if not dates_map:
            return None
        
        # Prendre la première date (souvent date d'émission)
        if 'emission' in field_name and dates_map:
            first_date = dates_map[0]
            return FieldValue(
                value=first_date['raw'],
                confidence=0.75,
                extraction_method='context_first_date',
                position={'line': first_date['line_index']}
            )
        
        # Date d'échéance (souvent après "échéance" ou en fin)
        elif 'echeance' in field_name:
            for date_info in dates_map:
                if 'échéance' in date_info['line_text'].lower() or 'due' in date_info['line_text'].lower():
                    return FieldValue(
                        value=date_info['raw'],
                        confidence=0.80,
                        extraction_method='context_keyword',
                        position={'line': date_info['line_index']}
                    )
        
        return None
    
    def _improve_amount_field(self, field_name: str, context_data: dict) -> Optional['FieldValue']:
        """Améliore l'extraction de montant"""
        from ocr_engine import FieldValue
        
        amounts_map = context_data.get('amounts_map', [])
        
        if not amounts_map:
            return None
        
        # Recherche par contexte
        for amount_info in amounts_map:
            line_lower = amount_info['line_text'].lower()
            
            if field_name == 'total_ttc' and any(kw in line_lower for kw in ['total', 'net à payer', 'amount due']):
                return FieldValue(
                    value=amount_info['value'],
                    confidence=0.85,
                    extraction_method='context_deep',
                    position={'line': amount_info['line_index']}
                )
            
            elif field_name == 'total_ht' and any(kw in line_lower for kw in ['total ht', 'subtotal', 'hors']):
                return FieldValue(
                    value=amount_info['value'],
                    confidence=0.80,
                    extraction_method='context_deep',
                    position={'line': amount_info['line_index']}
                )
            
            elif field_name == 'montant_tva' and 'tva' in line_lower and 'rate' not in line_lower:
                return FieldValue(
                    value=amount_info['value'],
                    confidence=0.75,
                    extraction_method='context_deep',
                    position={'line': amount_info['line_index']}
                )
        
        return None
    
    def _improve_party_field(self, field_name: str, document, context_data: dict) -> Optional['FieldValue']:
        """Améliore l'extraction client/fournisseur"""
        from ocr_engine import FieldValue
        
        # Recherche SIRET puis nom associé
        siret_locations = context_data.get('siret_locations', [])
        
        for siret_info in siret_locations:
            context_text = siret_info['context']
            # Extraire nom avant SIRET
            lines_before = context_text[:context_text.find(siret_info['siret'])].split('\n')
            if lines_before:
                potential_name = lines_before[-1].strip()
                if potential_name and len(potential_name) > 3:
                    return FieldValue(
                        value=potential_name,
                        confidence=0.70,
                        extraction_method='siret_context',
                        pattern=siret_info['siret']
                    )
        
        return None
    
    def _improve_tva_field(self, context_data: dict) -> Optional['FieldValue']:
        """Améliore l'extraction du taux TVA"""
        from ocr_engine import FieldValue
        
        # Si on a HT et TTC, calculer le taux
        # Sera fait dans calculate_missing_amounts
        
        return None
    
    def _find_missing_critical_fields(self, fields: Dict, doc_type: str) -> List[str]:
        """Identifie les champs critiques manquants"""
        critical_by_type = {
            'facture': ['date_emission', 'total_ttc', 'client', 'reference'],
            'devis': ['date_emission', 'total_ttc', 'client', 'reference'],
            'ticket': ['date_emission', 'total_ttc'],
            'recu': ['date_emission', 'total_ttc']
        }
        
        required = critical_by_type.get(doc_type, ['date_emission', 'total_ttc'])
        missing = [field for field in required if field not in fields]
        
        return missing
    
    def _extract_missing_field(self, field_name: str, document, context_data: dict, doc_type: str) -> Optional['FieldValue']:
        """Extrait un champ manquant"""
        # Utilise les mêmes méthodes que improve_field
        return self._improve_field(field_name, document, context_data, doc_type)
    
    def _cross_validate_fields(self, fields: Dict, context_data: dict) -> Dict:
        """Valide et ajuste les champs entre eux"""
        # Exemple : si client contient le pattern de l'entreprise source, c'est une erreur
        
        # Vérification montants
        if all(k in fields for k in ['total_ht', 'montant_tva', 'total_ttc']):
            calculated_ttc = fields['total_ht'].value + fields['montant_tva'].value
            actual_ttc = fields['total_ttc'].value
            
            # Tolérance 1%
            if abs(calculated_ttc - actual_ttc) / actual_ttc > 0.01:
                logger.warning(f"TTC inconsistency: calculated={calculated_ttc}, actual={actual_ttc}")
                # Garder le TTC (plus fiable) et recalculer les autres si besoin
        
        return fields
    
    def _can_calculate_missing_values(self, fields: Dict) -> bool:
        """Vérifie si on peut calculer des valeurs manquantes"""
        # Si on a 2 sur 3 de [HT, TVA, TTC], on peut calculer le 3ème
        has_ht = 'total_ht' in fields and fields['total_ht'].value
        has_tva = 'montant_tva' in fields and fields['montant_tva'].value
        has_ttc = 'total_ttc' in fields and fields['total_ttc'].value
        has_rate = 'tva_rate' in fields and fields['tva_rate'].value
        
        count = sum([has_ht, has_tva, has_ttc])
        
        return count >= 2 or (has_ttc and has_rate)
    
    def _calculate_missing_amounts(self, fields: Dict) -> Dict:
        """Calcule les montants manquants"""
        from ocr_engine import FieldValue
        
        calculated = {}
        
        has_ht = 'total_ht' in fields and fields['total_ht'].value
        has_tva = 'montant_tva' in fields and fields['montant_tva'].value
        has_ttc = 'total_ttc' in fields and fields['total_ttc'].value
        has_rate = 'tva_rate' in fields and fields['tva_rate'].value
        
        # HT + TVA → TTC
        if has_ht and has_tva and not has_ttc:
            calculated['total_ttc'] = FieldValue(
                value=round(fields['total_ht'].value + fields['montant_tva'].value, 2),
                confidence=0.85,
                extraction_method='calculation_ht_plus_tva'
            )
        
        # TTC - TVA → HT
        elif has_ttc and has_tva and not has_ht:
            calculated['total_ht'] = FieldValue(
                value=round(fields['total_ttc'].value - fields['montant_tva'].value, 2),
                confidence=0.85,
                extraction_method='calculation_ttc_minus_tva'
            )
        
        # TTC - HT → TVA
        elif has_ttc and has_ht and not has_tva:
            calculated['montant_tva'] = FieldValue(
                value=round(fields['total_ttc'].value - fields['total_ht'].value, 2),
                confidence=0.85,
                extraction_method='calculation_ttc_minus_ht'
            )
        
        # TTC + rate → HT + TVA
        elif has_ttc and has_rate:
            rate = fields['tva_rate'].value / 100
            ht = round(fields['total_ttc'].value / (1 + rate), 2)
            tva = round(fields['total_ttc'].value - ht, 2)
            
            if not has_ht:
                calculated['total_ht'] = FieldValue(
                    value=ht,
                    confidence=0.80,
                    extraction_method='calculation_from_ttc_rate'
                )
            
            if not has_tva:
                calculated['montant_tva'] = FieldValue(
                    value=tva,
                    confidence=0.80,
                    extraction_method='calculation_from_ttc_rate'
                )
        
        return calculated
    
    def _calculate_global_confidence(self, fields: Dict) -> float:
        """Calcule la confiance globale"""
        if not fields:
            return 0.0
        
        confidences = [
            field.confidence for field in fields.values() 
            if hasattr(field, 'confidence')
        ]
        
        if not confidences:
            return 0.3
        
        return sum(confidences) / len(confidences)
    
    def _enrich_ticket_cb(self, text: str, fields: Dict, context_data: dict) -> Dict:
        """
        🎯 ENRICHISSEMENT SPÉCIAL TICKET CB (SNIPER MODE)
        
        Objectif : compléter les champs manquants UNIQUEMENT pour les TICKETS CB
        Sans casser les factures/BL existants
        
        Extraction :
        - SIRET fournisseur (14 chiffres) → fournisseur_siret
        - Mode paiement CB/CARTE → mode_paiement
        - 4 derniers chiffres carte → carte_last4
        - Statut paiement → statut_paiement (PAYE si CB détecté)
        - Montant CB → montant_encaisse
        
        Règles :
        1. CONDITION STRICTE : document_type == "TICKET"
        2. NE PAS ÉCRASER les champs déjà renseignés
        3. Confiance modérée (0.75-0.85) car patterns spécifiques
        """
        from ocr_engine import FieldValue
        
        enriched = {}
        text_upper = text.upper()
        text_lines = text.split('\n')
        
        logger.debug("🎯 TICKET CB enrichment: starting analysis...")
        
        # 1. Détection SIRET fournisseur (14 chiffres)
        # Pattern: \d{3}\s?\d{3}\s?\d{3}\s?\d{5}
        siret_pattern = r'\b(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})\b'
        siret_matches = re.findall(siret_pattern, text)
        if siret_matches:
            # Prendre le premier SIRET (souvent en header)
            siret_clean = siret_matches[0].replace(' ', '')
            if len(siret_clean) == 14:
                enriched['fournisseur_siret'] = FieldValue(
                    value=siret_clean,
                    confidence=0.85,
                    extraction_method='pattern_siret_14digits',
                    position=None,
                    pattern=siret_pattern
                )
                logger.info(f"✓ SIRET fournisseur détecté: {siret_clean}")
        
        # 2. Détection Mode Paiement CB/CARTE
        cb_keywords = ['CARTE BANCAIRE', 'CB', 'CARTE', 'VISA', 'MASTERCARD', 'AMEX', 'DEBIT', 'CREDIT']
        mode_paiement_detected = None
        for keyword in cb_keywords:
            if keyword in text_upper:
                mode_paiement_detected = 'CB'
                break
        
        if mode_paiement_detected:
            enriched['mode_paiement'] = FieldValue(
                value='CB',
                confidence=0.80,
                extraction_method='keyword_carte_bancaire',
                position=None,
                pattern='|'.join(cb_keywords)
            )
            logger.info(f"✓ Mode paiement détecté: CB")
            
            # Si CB détecté → Statut PAYE
            enriched['statut_paiement'] = FieldValue(
                value='PAYE',
                confidence=0.85,
                extraction_method='derived_from_cb',
                position=None,
                pattern=None
            )
            logger.info(f"✓ Statut paiement: PAYE (dérivé de CB)")
        
        # 3. Détection 4 derniers chiffres carte
        # Patterns: **** 1234, XXXX 1234, ...1234
        carte_patterns = [
            r'[\*X]{4}\s?[\*X]{4}\s?[\*X]{4}\s?(\d{4})',  # **** **** **** 1234
            r'[\*X]{4}\s?(\d{4})',                          # **** 1234
            r'\.\.\.(\d{4})',                               # ...1234
            r'CARTE\s+(\d{4})',                             # CARTE 1234
        ]
        
        carte_last4 = None
        for pattern in carte_patterns:
            matches = re.findall(pattern, text_upper)
            if matches:
                carte_last4 = matches[0]
                break
        
        if carte_last4 and len(carte_last4) == 4:
            enriched['carte_last4'] = FieldValue(
                value=carte_last4,
                confidence=0.75,
                extraction_method='pattern_carte_masquee',
                position=None,
                pattern='carte_last4_digits'
            )
            logger.info(f"✓ Carte détectée (4 derniers chiffres): ****{carte_last4}")
        
        # 4. Détection Montant CB (si ligne contient "MONTANT" ou "TOTAL" près de CB)
        montant_cb = None
        for line in text_lines:
            line_upper = line.upper()
            if ('MONTANT' in line_upper or 'TOTAL' in line_upper) and any(k in line_upper for k in ['CB', 'CARTE', 'EUR', '€']):
                # Extraire montant : pattern \d+[,.]\d{2}
                amount_matches = re.findall(r'(\d+[,\.]\d{2})', line)
                if amount_matches:
                    try:
                        montant_str = amount_matches[0].replace(',', '.')
                        montant_cb = float(montant_str)
                        break
                    except ValueError:
                        continue
        
        if montant_cb:
            enriched['montant_encaisse'] = FieldValue(
                value=str(montant_cb),
                confidence=0.80,
                extraction_method='extraction_montant_cb_line',
                position=None,
                pattern='montant_near_cb'
            )
            logger.info(f"✓ Montant encaissé CB: {montant_cb} EUR")
        
        # 5. Date encaissement = Date document (si disponible dans fields)
        if 'date_doc' in fields and fields['date_doc'].value:
            enriched['date_encaissement'] = FieldValue(
                value=fields['date_doc'].value,
                confidence=0.80,
                extraction_method='derived_from_date_doc',
                position=None,
                pattern=None
            )
            logger.info(f"✓ Date encaissement: {fields['date_doc'].value}")
        
        logger.debug(f"🎯 TICKET CB enrichment: extracted {len(enriched)} new fields")
        return enriched
    
    def _needs_escalation(self, fields: Dict, global_confidence: float, document, context) -> bool:
        """Détermine si le niveau 3 est nécessaire"""
        # Seuil de confiance
        if global_confidence < self.confidence_threshold:
            logger.warning(f"Low confidence ({global_confidence:.2f}), may need Level 3")
            return True
        
        # Pattern inconnu (détection future)
        # Pour l'instant, Level 3 uniquement si très basse confiance
        if global_confidence < 0.5:
            return True
        
        return False

def _postprocess_ticket_fields(data: dict, entreprise_source: str, full_text: str) -> None:
    """Ticket-specific normalization:
    - If OCR put a SIREN/SIRET into client, move it to fournisseur_siret.
    - Ensure client = entreprise_source.
    - Best-effort detect fournisseur name from top lines.
    """
    try:
        ent = (entreprise_source or "").strip()
        if ent:
            data.setdefault("client", ent)

        client_val = str(data.get("client") or "")
        # Move siren/siret from client -> fournisseur_siret
        if ("siren" in client_val.lower()) or re.search(r"\b\d{3}\s?\d{3}\s?\d{3}\b", client_val):
            m = re.search(r"(\d{3})\s?(\d{3})\s?(\d{3})", client_val)
            if m and not data.get("fournisseur_siret"):
                data["fournisseur_siret"] = "".join(m.groups())
            if ent:
                data["client"] = ent
            else:
                data.pop("client", None)

        # If fournisseur empty, guess from header
        if not str(data.get("fournisseur") or "").strip():
            lines = [ln.strip() for ln in (full_text or "").splitlines() if ln.strip()]
            head = lines[:8]
            best = ""
            for ln in head:
                # pick a line with letters and not just numbers
                if len(re.findall(r"[A-Za-zÀ-ÿ]", ln)) >= 4 and len(ln) <= 60:
                    best = ln
                    break
            if best:
                data["fournisseur"] = best

        # If societe is set but fournisseur not, mirror
        if data.get("societe") and not data.get("fournisseur"):
            data["fournisseur"] = data.get("societe")

        # Ensure ticket_cb_detecte boolean exists
        if "ticket_cb_detecte" not in data:
            data["ticket_cb_detecte"] = False
    except Exception:
        pass


