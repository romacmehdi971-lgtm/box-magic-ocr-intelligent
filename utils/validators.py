"""Validators for OCR results"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ValidationResult:
    """Résultat d'une validation"""
    is_valid: bool
    warnings: List[str]
    errors: List[str]


def validate_ocr_result(ocr_result: 'OCRResult') -> ValidationResult:
    """
    Valide un résultat OCR
    
    Vérifie :
    - Cohérence des montants
    - Présence champs critiques
    - Cohérence dates
    - Séparation entreprise/client
    
    Args:
        ocr_result: Résultat à valider
    
    Returns:
        ValidationResult avec warnings/errors
    """
    warnings = []
    errors = []
    
    fields = ocr_result.fields
    
    # Vérification montants
    if all(k in fields for k in ['total_ht', 'montant_tva', 'total_ttc']):
        ht = fields['total_ht'].value
        tva = fields['montant_tva'].value
        ttc = fields['total_ttc'].value
        
        calculated_ttc = ht + tva
        tolerance = max(1.0, ttc * 0.01)  # 1€ ou 1%
        
        if abs(calculated_ttc - ttc) > tolerance:
            warnings.append(
                f"Amount inconsistency: HT({ht}) + TVA({tva}) = {calculated_ttc} != TTC({ttc})"
            )
    
    # Vérification champs critiques
    critical_fields = ['date_emission', 'total_ttc']
    missing_critical = [f for f in critical_fields if f not in fields or fields[f].value is None]
    
    if missing_critical:
        warnings.append(f"Missing critical fields: {', '.join(missing_critical)}")
    
    # Vérification dates
    if all(k in fields for k in ['date_emission', 'date_echeance']):
        date_emission = fields['date_emission'].value
        date_echeance = fields['date_echeance'].value
        
        if date_emission and date_echeance and date_emission > date_echeance:
            warnings.append(f"Date inconsistency: emission ({date_emission}) > echeance ({date_echeance})")
    
    # Vérification séparation entreprise/client
    if 'client' in fields:
        client_name = fields['client'].value.lower()
        source_entreprise = ocr_result.entreprise_source.lower()
        
        # Vérification simple de mots communs
        source_words = set(source_entreprise.split())
        client_words = set(client_name.split())
        common_words = source_words.intersection(client_words)
        
        # Exclure mots courts communs
        common_words = {w for w in common_words if len(w) > 3}
        
        if common_words:
            warnings.append(
                f"Client name may contain source entreprise keywords: {common_words}"
            )
    
    # Vérification confiance globale
    if ocr_result.confidence < 0.5:
        warnings.append(f"Low overall confidence: {ocr_result.confidence:.2%}")
    
    # Déterminer validité globale
    is_valid = len(errors) == 0
    
    return ValidationResult(
        is_valid=is_valid,
        warnings=warnings,
        errors=errors
    )