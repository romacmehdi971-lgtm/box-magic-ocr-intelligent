"""
OCR LEVEL 3 - CONTRÔLE & MÉMOIRE (RARE)
Objectif : Résoudre cas complexes + créer règle réutilisable

⚠️ CE NIVEAU EST EXCEPTIONNEL
Activé uniquement si OCR2 insuffisant ou pattern inconnu
"""

import re
import logging
from datetime import datetime
from typing import Dict, Optional, List
from copy import deepcopy

logger = logging.getLogger("OCREngine.Level3")


class OCRLevel3:
    """
    OCR Niveau 3 : Contrôle final et création de mémoire
    
    Fonctions :
    - Vérification cohérence globale
    - Correction champs FAUX
    - Complétion champs ABSENTS
    - CRÉATION RÈGLE MÉMOIRE
    
    Objectif : Éliminer l'apprentissage répétitif
    """
    
    def __init__(self, config: dict):
        """
        Initialise OCR Level 3
        
        Args:
            config: Configuration globale du système
        """
        self.config = config
        logger.info("OCR Level 3 initialized")
        logger.warning("Level 3 is RARE and creates memory rules")
    
    def process(self, document, ocr2_result: 'OCRResult', context) -> 'OCRResult':
        """
        Traitement Level 3 : Validation + Création règle
        
        Args:
            document: Document original
            ocr2_result: Résultat OCR Level 2
            context: ProcessingContext
        
        Returns:
            OCRResult validé avec règle créée
        """
        from ocr_engine import OCRResult, FieldValue
        
        logger.warning(f"[{ocr2_result.document_id}] OCR Level 3 activated - Creating memory rule")
        
        # 1. ANALYSE PATTERN DOCUMENT
        pattern = self._analyze_document_pattern(document, context)
        logger.info(f"Document pattern analyzed: {pattern.get('signature', 'unknown')}")
        
        # 2. PRÉSERVATION résultats OCR2
        fields = deepcopy(ocr2_result.fields)
        corrections = []
        
        # 3. VÉRIFICATION COHÉRENCE GLOBALE
        inconsistencies = self._find_inconsistencies(fields, pattern)
        logger.info(f"Found {len(inconsistencies)} inconsistencies")
        
        # 4. CORRECTIONS CIBLÉES
        for issue in inconsistencies:
            logger.debug(f"Correcting field: {issue['field']} - {issue['reason']}")
            
            correction = self._correct_field(
                issue,
                document,
                pattern,
                context
            )
            
            if correction:
                fields[issue['field']] = correction
                corrections.append(issue['field'])
                logger.info(f"Field corrected: {issue['field']}")
        
        # 5. COMPLÉTION CHAMPS ABSENTS
        missing = self._find_missing_critical_fields(fields, ocr2_result.document_type)
        logger.info(f"Missing critical fields: {missing}")
        
        for field_name in missing:
            value = self._extract_missing_field_advanced(
                field_name,
                document,
                pattern,
                context
            )
            
            if value:
                fields[field_name] = value
                corrections.append(field_name)
                logger.info(f"Missing field extracted: {field_name}")
        
        # 6. CRÉATION RÈGLE MÉMOIRE (CRUCIAL)
        rule = self._create_memory_rule(
            pattern=pattern,
            document=document,
            fields=fields,
            context=context,
            document_type=ocr2_result.document_type
        )
        
        logger.info(f"Memory rule created: {rule['id']}")
        logger.info(f"Rule conditions: {len(rule['conditions'])} conditions")
        logger.info(f"Rule actions: {len(rule['actions'])} extraction actions")
        
        # 7. ENREGISTREMENT RÈGLE
        # Sera fait par le memory store via l'engine
        
        # 8. CONSTRUCTION RÉSULTAT
        result = OCRResult(
            document_id=ocr2_result.document_id,
            document_type=ocr2_result.document_type,
            level=3,
            confidence=0.92,  # Confiance haute car validé manuellement
            entreprise_source=context.source_entreprise,
            fields=fields,
            processing_date=datetime.now(),
            needs_next_level=False,  # Level 3 est le dernier
            corrections=corrections,
            rule_created=rule
        )
        
        result.logs.append(f"OCR Level 3 completed")
        result.logs.append(f"Rule created: {rule['id']}")
        result.logs.append(f"Future similar documents will bypass OCR1/OCR2")
        
        logger.info(f"OCR Level 3 completed: {len(corrections)} corrections, rule created")
        
        return result
    
    def _analyze_document_pattern(self, document, context) -> dict:
        """
        Analyse le pattern unique du document
        
        Returns:
            dict avec signature, caractéristiques, identifiants
        """
        text = document.get_text()
        lines = text.split('\n')
        
        # Extraction caractéristiques uniques
        pattern = {
            'signature': '',
            'header_lines': [],
            'footer_lines': [],
            'siret_found': [],
            'logo_keywords': [],
            'structure_type': '',
            'unique_keywords': [],
            'layout_features': {}
        }
        
        # Header (5 premières lignes non vides)
        header_lines = [l.strip() for l in lines[:10] if l.strip()][:5]
        pattern['header_lines'] = header_lines
        
        # Footer (5 dernières lignes non vides)
        footer_lines = [l.strip() for l in lines[-10:] if l.strip()][-5:]
        pattern['footer_lines'] = footer_lines
        
        # Recherche SIRET
        siret_pattern = r'\b\d{3}\s?\d{3}\s?\d{3}\s?\d{5}\b'
        sirets = re.findall(siret_pattern, text)
        pattern['siret_found'] = [s.replace(' ', '') for s in sirets]
        
        # Logo/identité visuelle (mots-clés répétés en header)
        word_freq = {}
        for line in header_lines:
            for word in line.split():
                if len(word) > 3:
                    word_freq[word] = word_freq.get(word, 0) + 1
        
        pattern['logo_keywords'] = [w for w, freq in word_freq.items() if freq >= 2]
        
        # Type de structure (tableau, liste, etc.)
        has_tables = any(len(re.split(r'\s{2,}|\t', l)) >= 3 for l in lines)
        pattern['structure_type'] = 'table' if has_tables else 'linear'
        
        # Mots-clés uniques (capitalisés, répétés)
        unique_keywords = set()
        for line in lines:
            # Mots en majuscules de plus de 4 lettres
            caps_words = re.findall(r'\b[A-Z]{4,}\b', line)
            unique_keywords.update(caps_words)
        
        pattern['unique_keywords'] = list(unique_keywords)[:10]  # Top 10
        
        # Signature unique (hash du header + footer)
        signature_text = ' '.join(header_lines[:3] + footer_lines[-2:])
        pattern['signature'] = hash(signature_text) % 1000000  # Hash simplifié
        
        return pattern
    
    def _find_inconsistencies(self, fields: Dict, pattern: dict) -> List[dict]:
        """
        Détecte les incohérences dans les champs extraits
        
        Returns:
            Liste d'incohérences avec raison
        """
        inconsistencies = []
        
        # Vérification montants
        if all(k in fields for k in ['total_ht', 'montant_tva', 'total_ttc']):
            ht = fields['total_ht'].value
            tva = fields['montant_tva'].value
            ttc = fields['total_ttc'].value
            
            calculated_ttc = ht + tva
            
            # Tolérance 2€ ou 1%
            tolerance = max(2.0, ttc * 0.01)
            
            if abs(calculated_ttc - ttc) > tolerance:
                inconsistencies.append({
                    'field': 'total_ttc',
                    'reason': f'TTC inconsistent: HT({ht}) + TVA({tva}) = {calculated_ttc} != {ttc}',
                    'suggested_value': calculated_ttc
                })
        
        # Vérification TVA rate vs montant
        if all(k in fields for k in ['total_ht', 'montant_tva', 'tva_rate']):
            ht = fields['total_ht'].value
            tva = fields['montant_tva'].value
            rate = fields['tva_rate'].value
            
            calculated_tva = round(ht * rate / 100, 2)
            
            if abs(calculated_tva - tva) > 0.5:
                inconsistencies.append({
                    'field': 'tva_rate',
                    'reason': f'TVA rate inconsistent: {ht} * {rate}% = {calculated_tva} != {tva}',
                    'suggested_value': round((tva / ht) * 100, 1) if ht > 0 else None
                })
        
        # Vérification dates (émission < échéance)
        if all(k in fields for k in ['date_emission', 'date_echeance']):
            # Comparaison simple (format ISO)
            if fields['date_emission'].value > fields['date_echeance'].value:
                inconsistencies.append({
                    'field': 'date_echeance',
                    'reason': 'Date échéance avant date émission',
                    'suggested_value': None
                })
        
        # Vérification client != entreprise source
        if 'client' in fields:
            client_name = fields['client'].value.lower()
            source_patterns = pattern.get('logo_keywords', [])
            
            for keyword in source_patterns:
                if keyword.lower() in client_name:
                    inconsistencies.append({
                        'field': 'client',
                        'reason': f'Client contains source entreprise keyword: {keyword}',
                        'suggested_value': None
                    })
                    break
        
        return inconsistencies
    
    def _correct_field(self, issue: dict, document, pattern: dict, context) -> Optional['FieldValue']:
        """
        Corrige un champ incohérent
        
        Args:
            issue: Incohérence détectée avec raison
            document: Document original
            pattern: Pattern du document
            context: Contexte
        
        Returns:
            FieldValue corrigé ou None
        """
        from ocr_engine import FieldValue
        
        field_name = issue['field']
        
        # Si valeur suggérée disponible, l'utiliser
        if issue.get('suggested_value') is not None:
            return FieldValue(
                value=issue['suggested_value'],
                confidence=0.90,
                extraction_method='correction_calculation'
            )
        
        # Sinon, ré-extraction avec stratégie différente
        # Pour l'instant, retourner None (pas de correction automatique)
        logger.warning(f"No automatic correction for: {field_name} - {issue['reason']}")
        
        return None
    
    def _find_missing_critical_fields(self, fields: Dict, doc_type: str) -> List[str]:
        """Identifie champs critiques manquants"""
        critical_by_type = {
            'facture': ['date_emission', 'total_ttc', 'client', 'reference'],
            'devis': ['date_emission', 'total_ttc', 'client', 'reference'],
            'ticket': ['date_emission', 'total_ttc'],
            'recu': ['date_emission', 'total_ttc']
        }
        
        required = critical_by_type.get(doc_type, ['date_emission', 'total_ttc'])
        missing = [field for field in required if field not in fields or fields[field].value is None]
        
        return missing
    
    def _extract_missing_field_advanced(self, field_name: str, document, pattern: dict, context) -> Optional['FieldValue']:
        """
        Extraction avancée d'un champ manquant
        
        Utilise le pattern du document pour affiner l'extraction
        """
        from ocr_engine import FieldValue
        
        text = document.get_text()
        
        # Stratégie par champ
        if field_name == 'reference':
            # Recherche dans header
            for line in pattern['header_lines']:
                # Pattern général : suite de chiffres/lettres après N°, Ref, etc.
                ref_match = re.search(r'(?:N[°o]|REF|REFERENCE|FACTURE|DEVIS)[:\s]+([A-Z0-9-]+)', line, re.IGNORECASE)
                if ref_match:
                    return FieldValue(
                        value=ref_match.group(1),
                        confidence=0.75,
                        extraction_method='pattern_header'
                    )
        
        elif field_name == 'client':
            # Recherche dans zone entre header et milieu
            lines = text.split('\n')
            # Zone entre ligne 5 et 15 généralement
            for i in range(5, min(15, len(lines))):
                line = lines[i].strip()
                if line and len(line) > 5 and not any(kw in line.lower() for kw in ['siret', 'tva', 'adresse', 'tel']):
                    # Première ligne non-vide non-technique
                    return FieldValue(
                        value=line,
                        confidence=0.60,
                        extraction_method='pattern_position'
                    )
        
        # Autres champs : stratégie générique
        logger.warning(f"No advanced extraction strategy for: {field_name}")
        return None
    
    def _create_memory_rule(self, pattern: dict, document, fields: Dict, context, document_type: str) -> dict:
        """
        FONCTION CRUCIALE : Crée une règle mémoire réutilisable
        
        Cette règle permettra de traiter les documents similaires
        directement sans passer par OCR1/OCR2
        
        Returns:
            dict représentant la règle
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rule_id = f"rule_{timestamp}_{pattern.get('signature', '000000')}"
        
        # CONDITIONS de déclenchement
        conditions = {
            'document_type': document_type,
            'signature': pattern.get('signature'),
            'header_contains': pattern['header_lines'][:2] if pattern['header_lines'] else [],
            'footer_contains': pattern['footer_lines'][-1:] if pattern['footer_lines'] else [],
        }
        
        # Si SIRET présent, condition forte
        if pattern['siret_found']:
            conditions['siret_matches'] = pattern['siret_found'][0]
        
        # Si mots-clés uniques
        if pattern['logo_keywords']:
            conditions['logo_keywords'] = pattern['logo_keywords'][:3]
        
        # ACTIONS d'extraction
        actions = {}
        
        for field_name, field_value in fields.items():
            if field_value.confidence >= 0.75:  # Seulement les champs fiables
                action = {
                    'method': field_value.extraction_method or 'unknown',
                    'value': field_value.value,
                    'confidence': field_value.confidence
                }
                
                # Ajouter détails selon la méthode
                if field_value.extraction_method == 'regex':
                    action['pattern'] = field_value.pattern
                
                if field_value.position:
                    action['position'] = field_value.position
                
                actions[field_name] = action
        
        # MÉTADONNÉES
        metadata = {
            'created_at': datetime.now().isoformat(),
            'created_by': 'OCR_Level3',
            'entreprise': context.source_entreprise,
            'document_type': document_type,
            'usage_count': 0,
            'success_rate': 1.0,  # Initial
            'last_used': None,
            'fields_count': len(actions),
            'pattern_signature': pattern.get('signature')
        }
        
        # Nom descriptif de la règle
        name = self._generate_rule_name(pattern, document_type, context)
        
        rule = {
            'id': rule_id,
            'name': name,
            'conditions': conditions,
            'actions': actions,
            'metadata': metadata
        }
        
        return rule
    
    def _generate_rule_name(self, pattern: dict, doc_type: str, context) -> str:
        """Génère un nom descriptif pour la règle"""
        # Utiliser logo keywords si disponibles
        if pattern['logo_keywords']:
            identifier = pattern['logo_keywords'][0]
        elif pattern['siret_found']:
            identifier = f"SIRET_{pattern['siret_found'][0][:6]}"
        else:
            identifier = f"Pattern_{pattern.get('signature', 'unknown')}"
        
        return f"{doc_type.capitalize()} - {identifier} - {context.source_entreprise}"
