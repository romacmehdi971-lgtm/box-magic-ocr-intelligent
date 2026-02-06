#!/usr/bin/env python3
"""
TEST COMPLET OCR v1.5.0 - Extraction sur les 3 PDFs principaux
"""
import sys
import os
import json
import re

# Ajouter le répertoire webapp au PYTHONPATH
sys.path.insert(0, '/home/user/webapp')

try:
    import pdfplumber
except ImportError:
    print("Installation de pdfplumber...")
    os.system("pip3 install -q pdfplumber")
    import pdfplumber

def extract_text_from_pdf(pdf_path):
    """Extrait le texte brut d'un PDF"""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                text += page.extract_text() or ""
            return text
    except Exception as e:
        return f"ERREUR: {e}"

def clean_ocr_text(text):
    """Nettoyage ULTRA-ROBUSTE du texte OCR (v1.5.0)"""
    # 1. Retirer NULL bytes
    text = text.replace('\u0000', '').replace('\x00', '')
    
    # 2. NETTOYAGE LIGNE PAR LIGNE
    lines = []
    for line in text.split('\n'):
        # Protéger les montants : ajouter des marqueurs temporaires
        line = re.sub(r'(\d+[,\.]\d{2})', r'<MONTANT>\1', line)
        
        # Si la ligne contient beaucoup d'espaces isolés, les retirer
        if re.search(r'\b[A-Za-z]\s+[A-Za-z]\s+[A-Za-z]', line):
            # Retirer espaces entre LETTRES isolées : "F a c t u r e" → "Facture"
            line = re.sub(r'(?<=[A-Za-z])\s+(?=[A-Za-z])', '', line)
        
        # Retirer espaces entre CHIFFRES isolés dans les montants
        if '<MONTANT>' in line:
            montants = re.findall(r'<MONTANT>([^<]+?)(?:<|$|\s)', line)
            for montant in montants:
                montant_clean = re.sub(r'\s+', '', montant)
                line = line.replace(f'<MONTANT>{montant}', f' {montant_clean}')
        
        # Retirer les marqueurs restants
        line = line.replace('<MONTANT>', ' ')
        
        lines.append(line)
    text = '\n'.join(lines)
    
    # 3. Normaliser espaces multiples
    text = re.sub(r' {2,}', ' ', text)
    
    # 4. Nettoyer sauts de ligne multiples
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()

def extract_invoice_number(text):
    """Extrait le numéro de facture"""
    patterns = [
        (r'N[°oúu]m[eé]ro\s*(?:de\s*)?facture\s*:?\s*([A-Z0-9\-_]{3,25})(?:\b|$|\s)', 'facture_label_fr'),
        (r'Invoice\s+Number\s*:?\s*([A-Z0-9\-_]{3,25})(?:\b|$|\s)', 'invoice_number'),
        (r'FACTURE\s*N[°oú]?\s*:?\s*([A-Z0-9\-_]{3,25})(?:\b|$|\s)', 'facture_prefix'),
    ]
    
    for pattern, pattern_name in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            numero = match.group(1).strip()
            numero = re.sub(r'[\s\-_]+', '', numero)
            
            # Validation stricte
            has_digit = bool(re.search(r'\d', numero))
            valid_length = 3 <= len(numero) <= 25
            not_only_letters = not numero.isalpha()
            
            if has_digit and valid_length and not_only_letters:
                return {
                    'value': numero,
                    'confidence': 0.95 if 'label' in pattern_name else 0.90,
                    'pattern': pattern_name
                }
    return None

def extract_amounts(text):
    """Extrait les montants HT, TVA, TTC"""
    amounts = {}
    
    amount_pattern = r'([\d\s]+)[,.]([\d]{2})'
    
    # TTC
    ttc_patterns = [
        r'(?:Total\s*TTC|TOTAL\s*TTC|Total|TOTAL|Montant\s*d[ûu]|Amount\s*due|Net\s*[àa]\s*payer)\s*:?\s*' + amount_pattern,
        r'(?:TTC|TOTAL)\s*:?\s*' + amount_pattern,
        r'MONTANT\s*=?\s*' + amount_pattern,
    ]
    
    for pattern in ttc_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and 'total_ttc' not in amounts:
            montant_str = match.group(1).replace(' ', '') + '.' + match.group(2)
            try:
                amounts['total_ttc'] = {
                    'value': float(montant_str),
                    'confidence': 0.95,
                    'pattern': 'ttc_pattern'
                }
                break
            except:
                pass
    
    # HT
    ht_patterns = [
        r'(?:Total\s*HT|TOTAL\s*HT|Total\s*hors\s*taxe[s]?|Subtotal|Sous-total)\s*:?\s*' + amount_pattern,
    ]
    
    for pattern in ht_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and 'total_ht' not in amounts:
            montant_str = match.group(1).replace(' ', '') + '.' + match.group(2)
            try:
                amounts['total_ht'] = {
                    'value': float(montant_str),
                    'confidence': 0.90,
                    'pattern': 'ht_pattern'
                }
                break
            except:
                pass
    
    # TVA
    tva_patterns = [
        r'(?:Montant\s*TVA|TVA|VAT\s*Amount)\s*:?\s*' + amount_pattern,
    ]
    
    for pattern in tva_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match and 'montant_tva' not in amounts:
            montant_str = match.group(1).replace(' ', '') + '.' + match.group(2)
            try:
                amounts['montant_tva'] = {
                    'value': float(montant_str),
                    'confidence': 0.85,
                    'pattern': 'tva_pattern'
                }
                break
            except:
                pass
    
    return amounts

def extract_date(text):
    """Extrait la date d'émission"""
    patterns = [
        r"(?:Date\s*d[''']?émission|Date\s*de\s*facture|Invoice\s*date|Date)\s*:?\s*(\d{1,2})\s*[/-]\s*(\d{1,2})\s*[/-]\s*(\d{4})",
        r"(?:Date\s*d[''']?émission|Date\s*de\s*facture|Invoice\s*date|Date)\s*:?\s*(\d{1,2})\s+(janvier|février|f[ée]vrier|mars|avril|mai|juin|juillet|ao[ûu]t|septembre|octobre|novembre|d[ée]cembre)\s+(\d{4})",
    ]
    
    mois_map = {
        'janvier': '01', 'février': '02', 'fevrier': '02', 'mars': '03',
        'avril': '04', 'mai': '05', 'juin': '06',
        'juillet': '07', 'août': '08', 'aout': '08', 'septembre': '09',
        'octobre': '10', 'novembre': '11', 'décembre': '12', 'decembre': '12'
    }
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if groups[1].isdigit():
                # Format numérique
                date_str = f"{groups[2]}-{groups[1].zfill(2)}-{groups[0].zfill(2)}"
            else:
                # Format avec mois
                mois = mois_map.get(groups[1].lower(), '01')
                date_str = f"{groups[2]}-{mois}-{groups[0].zfill(2)}"
            
            return {
                'value': date_str,
                'confidence': 0.95,
                'pattern': 'date_context'
            }
    
    return None

def extract_siret(text):
    """Extrait le SIRET"""
    patterns = [
        r'SIRET\s*:?\s*(\d{3}\s*\d{3}\s*\d{3}\s*\d{5})',
        r'SIRET\s*:?\s*(\d{14})',
        r'\b(\d{14})\b',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            siret = re.sub(r'\s+', '', match.group(1))
            if len(siret) == 14:
                return {
                    'value': siret,
                    'confidence': 0.95 if 'SIRET' in pattern else 0.80,
                    'pattern': 'siret_pattern'
                }
    
    return None

def test_pdf(pdf_path, pdf_name):
    """Test complet d'extraction sur un PDF"""
    print(f"\n{'='*80}")
    print(f"📄 TEST: {pdf_name}")
    print(f"{'='*80}\n")
    
    # 1. Extraction texte brut
    print("1️⃣  EXTRACTION TEXTE BRUT...")
    text_raw = extract_text_from_pdf(pdf_path)
    print(f"   ✅ Longueur texte brut: {len(text_raw)} caractères")
    print(f"   📝 Aperçu (200 premiers chars):\n{text_raw[:200]}\n")
    
    # 2. Nettoyage
    print("2️⃣  NETTOYAGE OCR v1.5.0...")
    text_clean = clean_ocr_text(text_raw)
    print(f"   ✅ Longueur texte nettoyé: {len(text_clean)} caractères")
    print(f"   📝 Aperçu (200 premiers chars):\n{text_clean[:200]}\n")
    
    # 3. Extraction numéro facture
    print("3️⃣  EXTRACTION N° FACTURE...")
    numero = extract_invoice_number(text_clean)
    if numero:
        print(f"   ✅ N° Facture: {numero['value']}")
        print(f"   📊 Confiance: {numero['confidence']}")
        print(f"   🔍 Pattern: {numero['pattern']}")
    else:
        print(f"   ❌ N° Facture: NON TROUVÉ")
    print()
    
    # 4. Extraction dates
    print("4️⃣  EXTRACTION DATE...")
    date = extract_date(text_clean)
    if date:
        print(f"   ✅ Date: {date['value']}")
        print(f"   📊 Confiance: {date['confidence']}")
    else:
        print(f"   ❌ Date: NON TROUVÉE")
    print()
    
    # 5. Extraction montants
    print("5️⃣  EXTRACTION MONTANTS...")
    amounts = extract_amounts(text_clean)
    if amounts:
        for key, data in amounts.items():
            print(f"   ✅ {key.upper()}: {data['value']}")
            print(f"      📊 Confiance: {data['confidence']}")
    else:
        print(f"   ❌ Montants: NON TROUVÉS")
    print()
    
    # 6. Extraction SIRET
    print("6️⃣  EXTRACTION SIRET...")
    siret = extract_siret(text_clean)
    if siret:
        print(f"   ✅ SIRET: {siret['value']}")
        print(f"   📊 Confiance: {siret['confidence']}")
    else:
        print(f"   ❌ SIRET: NON TROUVÉ")
    print()
    
    # 7. Résumé
    print("📊 RÉSUMÉ:")
    print(f"   • N° Facture: {numero['value'] if numero else 'VIDE'}")
    print(f"   • Date: {date['value'] if date else 'VIDE'}")
    print(f"   • TTC: {amounts.get('total_ttc', {}).get('value', 'VIDE')}")
    print(f"   • HT: {amounts.get('total_ht', {}).get('value', 'VIDE')}")
    print(f"   • TVA: {amounts.get('montant_tva', {}).get('value', 'VIDE')}")
    print(f"   • SIRET: {siret['value'] if siret else 'VIDE'}")
    print()

def main():
    """Test des 3 PDFs principaux"""
    print("\n" + "="*80)
    print("🧪 TEST COMPLET OCR v1.5.0 - EXTRACTION SUR 3 PDFs")
    print("="*80)
    
    pdfs = [
        ("/home/user/uploaded_files/Invoice-N8WY0KFA-0003.pdf", "Invoice Genspark"),
        ("/home/user/uploaded_files/Scanné 3 févr. 2026 à 22_03_27 (1).pdf", "Weldom/BricoDia"),
        ("/home/user/uploaded_files/scan_20260130_192127.pdf", "Carrefour CB (scan)"),
    ]
    
    for pdf_path, pdf_name in pdfs:
        if os.path.exists(pdf_path):
            test_pdf(pdf_path, pdf_name)
        else:
            print(f"\n❌ FICHIER NON TROUVÉ: {pdf_path}\n")
    
    print("="*80)
    print("✅ TESTS TERMINÉS")
    print("="*80)

if __name__ == "__main__":
    main()
