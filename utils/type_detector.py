"""
Document type detection based on text keywords

Détection simple par mots-clés (pas d'IA)
"""

import logging
import re
from typing import Optional

logger = logging.getLogger("OCREngine.TypeDetector")


def detect_document_type(text: str) -> str:
    """
    Détecte le type de document basé sur le contenu textuel
    
    Règles simples par mots-clés :
    - FACTURE : "facture", "invoice", "total TTC", "TVA"
    - BON_LIVRAISON : "bon de livraison", "delivery note", "BL"
    - DEVIS : "devis", "quotation", "estimation"
    - BON_COMMANDE : "bon de commande", "purchase order", "BC"
    - TICKET : "ticket", "caisse", "magasin", "article(s)"
    - AUTRE : si aucun match
    
    Args:
        text: Texte extrait du document
    
    Returns:
        Type de document (FACTURE, BON_LIVRAISON, DEVIS, BON_COMMANDE, TICKET, AUTRE)
    """
    if not text or not text.strip():
        logger.warning("detect_document_type: empty text, returning AUTRE")
        return 'AUTRE'
    
    # [FIX] LOGGING TEXTE BRUT (premiers 500 caractères)
    text_preview = text[:500].replace('\n', ' ')
    logger.info("=" * 80)
    logger.info("[OCR_TEXT_BRUT] Extrait (500 premiers chars):")
    logger.info(f"  {text_preview}...")
    logger.info(f"[OCR_TEXT_BRUT] Longueur totale: {len(text)} caractères")
    logger.info("=" * 80)
    
    text_upper = text.upper()
    
    # [FIX] Nettoyer espaces multiples causés par certains PDF (PyPDF2)
    # Exemple : "F a c t u r e" devient "FACTURE"
    text_normalized = re.sub(r'\s+', ' ', text_upper)  # Normaliser espaces
    
    # [FIX CRITIQUE] Supprimer TOUS les espaces pour matching robuste
    # Permet de matcher "F A C T U R E" avec "FACTURE"
    text_no_spaces = text_normalized.replace(' ', '')
    
    # Score par type
    scores = {
        'FACTURE': 0,
        'BON_LIVRAISON': 0,
        'DEVIS': 0,
        'BON_COMMANDE': 0,
        'TICKET': 0
    }
    
    # === FACTURE ===
    # [FIX] Patterns renforcés avec pondération
    facture_keywords_strong = [
        'FACTURE N°',
        'INVOICE N°',
        'NUMÉRO DE FACTURE',
        'INVOICE NUMBER'
    ]
    
    facture_keywords_medium = [
        'FACTURE',
        'INVOICE',
        'FACT N°',
        'FACT.',
        'DATE D\'ÉCHÉANCE',
        'DUE DATE'
    ]
    
    facture_keywords_weak = [
        'TOTAL TTC',
        'MONTANT TTC',
        'NET À PAYER',
        'TVA',
        'HT'
    ]
    
    # Patterns forts = +3 points
    for kw in facture_keywords_strong:
        kw_no_space = kw.replace(' ', '')
        if kw_no_space in text_no_spaces:
            scores['FACTURE'] += 3
            logger.debug(f"  ✓ FACTURE strong: '{kw}' matched")
    
    # Patterns moyens = +2 points
    for kw in facture_keywords_medium:
        kw_no_space = kw.replace(' ', '')
        if kw_no_space in text_no_spaces:
            scores['FACTURE'] += 2
            logger.debug(f"  ✓ FACTURE medium: '{kw}' matched")
    
    # Patterns faibles = +1 point
    for kw in facture_keywords_weak:
        kw_no_space = kw.replace(' ', '')
        if kw_no_space in text_no_spaces:
            scores['FACTURE'] += 1
            logger.debug(f"  ✓ FACTURE weak: '{kw}' matched")
    
    # Exclure si c'est un BL
    if 'BON' in text_no_spaces and 'LIVRAISON' in text_no_spaces:
        scores['FACTURE'] = max(0, scores['FACTURE'] - 3)
    
    # === BON DE LIVRAISON ===
    bl_keywords = [
        'BON DE LIVRAISON',
        'DELIVERY NOTE',
        'BL N°',
        'BON LIVRAISON',
        'LIVRAISON N°'
    ]
    
    for kw in bl_keywords:
        kw_no_space = kw.replace(' ', '')
        if kw_no_space in text_no_spaces:
            scores['BON_LIVRAISON'] += 2
    
    # === DEVIS ===
    devis_keywords = [
        'DEVIS',
        'QUOTATION',
        'ESTIMATION',
        'QUOTE',
        'DEVIS N°'
    ]
    
    for kw in devis_keywords:
        kw_no_space = kw.replace(' ', '')
        if kw_no_space in text_no_spaces:
            scores['DEVIS'] += 2
    
    # === BON DE COMMANDE ===
    bc_keywords = [
        'BON DE COMMANDE',
        'PURCHASE ORDER',
        'BC N°',
        'COMMANDE N°',
        'ORDER N°'
    ]
    
    for kw in bc_keywords:
        kw_no_space = kw.replace(' ', '')
        if kw_no_space in text_no_spaces:
            scores['BON_COMMANDE'] += 2
    
    # === TICKET DE CAISSE ===
    # [FIX] Patterns affinés pour éviter faux positifs avec FACTURE
    # Retrait : CB, CARTE BANCAIRE, TOTAL A PAYER (présents dans factures)
    ticket_keywords = [
        'TICKET DE CAISSE',  # Pattern spécifique
        'TICKET N°',
        'N° CAISSE',
        'NUMERO DE CAISSE',
        'CODE CAISSE',
        'MERCI DE VOTRE VISITE',
        'A BIENTOT'
    ]
    
    for kw in ticket_keywords:
        kw_no_space = kw.replace(' ', '')
        if kw_no_space in text_no_spaces:
            scores['TICKET'] += 2  # Score augmenté car patterns plus précis
    
    # Patterns spécifiques tickets
    if re.search(r'\d+ARTICLE', text_no_spaces):  # "5ARTICLES" sans espace
        scores['TICKET'] += 2
    
    # Détection grands distributeurs (ticket)
    distributeurs = ['CARREFOUR', 'LECLERC', 'AUCHAN', 'INTERMARCHE', 'LIDL', 'CASINO']
    for distrib in distributeurs:
        if distrib in text_no_spaces:
            scores['TICKET'] += 3  # Score renforcé pour grande distribution
            break
    
    # [FIX] PRIORITÉ FACTURE : Si "FACTURE" détecté, pénaliser TICKET
    if 'FACTURE' in text_no_spaces or 'INVOICE' in text_no_spaces:
        if scores['FACTURE'] > 0:
            scores['TICKET'] = max(0, scores['TICKET'] - 3)  # Réduction score ticket
    
    # === SÉLECTION DU TYPE ===
    max_score = max(scores.values())
    
    # [FIX] LOGGING EXHAUSTIF - Tous les scores
    logger.info("=" * 60)
    logger.info("[TYPE_DETECTION] Scores de classification:")
    for doc_type, score in sorted(scores.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {doc_type:20} = {score:3} points")
    logger.info("=" * 60)
    
    if max_score == 0:
        logger.warning(f"[TYPE_DETECTION] Aucun mot-clé matché → AUTRE")
        return 'AUTRE'
    
    # Prendre le type avec le meilleur score
    detected_types = [doc_type for doc_type, score in scores.items() if score == max_score]
    
    # Si égalité, ordre de priorité
    priority_order = ['FACTURE', 'BON_LIVRAISON', 'DEVIS', 'BON_COMMANDE', 'TICKET']
    
    if len(detected_types) > 1:
        logger.warning(f"[TYPE_DETECTION] Égalité de scores ({max_score}) entre: {detected_types}")
        logger.warning(f"[TYPE_DETECTION] Application ordre de priorité: {priority_order}")
    
    for doc_type in priority_order:
        if doc_type in detected_types:
            logger.info(f"[TYPE_DETECTION] ✅ TYPE FINAL = {doc_type} (score: {max_score})")
            return doc_type
    
    logger.warning(f"[TYPE_DETECTION] Fallback → AUTRE")
    return 'AUTRE'


def get_document_type_confidence(text: str, detected_type: str) -> float:
    """
    Calcule un score de confiance pour le type détecté
    
    Args:
        text: Texte du document
        detected_type: Type détecté
    
    Returns:
        Score de confiance (0.0 à 1.0)
    """
    if detected_type == 'AUTRE':
        return 0.3
    
    # Recompter les mots-clés pour le type détecté
    text_upper = text.upper()
    
    keyword_map = {
        'FACTURE': ['FACTURE', 'INVOICE', 'TOTAL TTC', 'TVA'],
        'BON_LIVRAISON': ['BON DE LIVRAISON', 'DELIVERY NOTE', 'BL'],
        'DEVIS': ['DEVIS', 'QUOTATION', 'ESTIMATION'],
        'BON_COMMANDE': ['BON DE COMMANDE', 'PURCHASE ORDER'],
        'TICKET': ['TICKET', 'CAISSE', 'ARTICLE(S)']
    }
    
    keywords = keyword_map.get(detected_type, [])
    matches = sum(1 for kw in keywords if kw in text_upper)
    
    # Score basé sur nombre de matches
    if matches >= 3:
        return 0.95
    elif matches == 2:
        return 0.85
    elif matches == 1:
        return 0.70
    else:
        return 0.50


if __name__ == "__main__":
    # Tests
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    
    test_cases = [
        ("FACTURE N° 12345\nDate : 01/01/2026\nTotal HT : 1000€\nTVA 20% : 200€\nTotal TTC : 1200€", "FACTURE"),
        ("BON DE LIVRAISON N° BL-001\nDate : 01/01/2026\nArticles livrés", "BON_LIVRAISON"),
        ("DEVIS N° DEV-123\nValidité : 30 jours", "DEVIS"),
        ("Carrefour\nTICKET\n29 ARTICLES\nTOTAL À PAYER", "TICKET"),
        ("Document sans mots-clés spécifiques", "AUTRE")
    ]
    
    print("=== TEST DOCUMENT TYPE DETECTION ===\n")
    
    for text, expected in test_cases:
        detected = detect_document_type(text)
        confidence = get_document_type_confidence(text, detected)
        status = "✓" if detected == expected else "✗"
        print(f"{status} Expected: {expected:15} | Detected: {detected:15} | Confidence: {confidence:.2f}")
        print(f"   Text: {text[:50]}...")
        print()
