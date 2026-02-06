#!/usr/bin/env python3
"""
Test script to extract OCR text from PDF and diagnose extraction issues
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from connectors.document_loader import DocumentLoader

# Configuration
config = {
    'ocr_engine': 'tesseract'
}

# PDF path
pdf_path = "/home/user/uploaded_files/Scanné 3 févr. 2026 à 22_03_27 (2).pdf"

print("="*80)
print("PDF OCR TEXT EXTRACTION DIAGNOSTIC")
print("="*80)
print(f"PDF: {pdf_path}")
print()

# Load document
loader = DocumentLoader(config)

try:
    document = loader.load(pdf_path)
    
    print(f"✅ Document loaded successfully")
    print(f"Method: {document.metadata.get('method')}")
    print(f"OCR Mode: {document.metadata.get('ocr_mode')}")
    print(f"PDF Text Detected: {document.metadata.get('pdf_text_detected')}")
    print()
    
    text = document.get_text()
    print(f"📝 Extracted text length: {len(text)} characters")
    print()
    print("="*80)
    print("FULL EXTRACTED TEXT:")
    print("="*80)
    print(text)
    print("="*80)
    print()
    
    # Simple pattern detection
    print("🔍 PATTERN DETECTION:")
    print()
    
    import re
    
    # Numéro facture
    numero_patterns = [
        r'N[°o]\s*[:\s]*([A-Z0-9-]+)',
        r'FACTURE\s*N[°o]?\s*:?\s*([A-Z0-9-]+)',
        r'Invoice\s*#?\s*:?\s*([A-Z0-9-]+)',
        r'NUMERO\s*:?\s*([A-Z0-9-]+)'
    ]
    
    print("Numéro facture:")
    for pattern in numero_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            print(f"  ✅ Pattern '{pattern}' found: {matches}")
    
    # Dates
    date_patterns = [
        r'(\d{2})[/-](\d{2})[/-](\d{4})',
        r'(\d{4})[/-](\d{2})[/-](\d{2})',
        r'(\d{1,2})\s+(janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre)\s+(\d{4})'
    ]
    
    print("\nDates:")
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            print(f"  ✅ Pattern '{pattern}' found: {matches}")
    
    # Montants
    amount_patterns = [
        r'(\d+(?:[,\s]\d{3})*)[.,](\d{2})\s*€',
        r'€\s*(\d+(?:[,\s]\d{3})*)[.,](\d{2})',
        r'(\d+(?:[,\s]\d{3})*)[.,](\d{2})\s*EUR'
    ]
    
    print("\nMontants:")
    for pattern in amount_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            print(f"  ✅ Pattern '{pattern}' found: {matches}")
    
    # Context-based extraction
    print("\n💡 CONTEXT ANALYSIS:")
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower()
        if any(kw in line_lower for kw in ['total', 'montant', 'ttc', 'ht', 'tva', 'facture', 'invoice', 'date', 'client']):
            print(f"  Line {i}: {line.strip()}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

