/**
 * BM_Parsers.gs
 * Module centralisé de parsing pour Box Magic OCR
 * Date: 2026-02-14
 * Version: 1.0.0
 * 
 * Contient:
 * - Parsers de montants français (HT/TVA/TTC)
 * - Parsers de numéros de factures
 * - Parsers de dates (normalisation YYYY-MM-DD)
 * - Extracteurs d'emails et noms fournisseurs
 * - Utilitaires de sélection texte (longest, isEmpty)
 * 
 * ⚠️ ATTENTION: Ce fichier centralise les fonctions précédemment dispersées
 * dans 02_SCAN_WORKER.gs. Ne pas modifier sans tester l'ensemble du pipeline OCR.
 */

/**
 * Pick the longest non-empty text among candidates (strings).
 * Used to avoid losing OCR content when multiple fields exist.
 * 
 * @param {Array<string>} candidates - Array of text candidates
 * @return {string} The longest non-empty text, or empty string
 */
function BM_PARSERS_pickLongestText(candidates) {
  try {
    if (!candidates || !candidates.length) return '';
    var best = '';
    for (var i = 0; i < candidates.length; i++) {
      var t = candidates[i];
      if (t === null || t === undefined) continue;
      if (typeof t !== 'string') t = String(t);
      t = t.trim();
      if (!t) continue;
      if (t.length > best.length) best = t;
    }
    return best;
  } catch (e) {
    return '';
  }
}

/**
 * Extract invoice/document number from OCR text (best-effort, deterministic).
 * 
 * Patterns recognized:
 * - N° Facture, No Facture, N Facture
 * - N° Pièce, N° Document, N° Ticket, N° Dossier
 * - Facture #, Facture -, Facture :
 * 
 * @param {string} txt - OCR text to parse
 * @return {string} Extracted invoice number, or empty string
 */
function BM_PARSERS_extractInvoiceNumber(txt) {
  try {
    if (!txt) return '';
    txt = String(txt);
    // Common French markers
    var patterns = [
      /\b(?:N\s*[°oº]|No|N°)\s*(?:Facture|Pi[eè]ce|Document|Ticket|Dossier)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9\-/]{4,})\b/i,
      /\b(?:Facture)\s*[:#-]?\s*([A-Z0-9][A-Z0-9\-/]{4,})\b/i,
      /\b(?:N\s*Dossier)\s*[:#-]?\s*([0-9]{4,})\b/i
    ];
    for (var i = 0; i < patterns.length; i++) {
      var m = txt.match(patterns[i]);
      if (m && m[1]) return String(m[1]).trim();
    }
    return '';
  } catch (e) {
    return '';
  }
}

/**
 * Parse a French amount string to a normalized decimal string with dot.
 * 
 * Examples:
 * - "593,72" -> "593.72"
 * - "1.234,56" -> "1234.56"
 * - "1,234.56" -> "1234.56"
 * - "1234" -> "1234"
 * 
 * @param {string|number} s - Amount to parse (French format)
 * @return {string} Normalized decimal string with dot, or empty string
 */
function BM_PARSERS_parseAmountFR(s) {
  try {
    if (s === null || s === undefined) return '';
    s = String(s);
    // Keep digits, comma, dot, minus
    s = s.replace(/[^0-9,\.\-]/g, '');
    // If both comma and dot exist, assume dot is thousands separator and comma is decimal
    if (s.indexOf(',') >= 0 && s.indexOf('.') >= 0) {
      s = s.replace(/\./g, '').replace(',', '.');
    } else if (s.indexOf(',') >= 0) {
      s = s.replace(',', '.');
    }
    // Normalize multiple dots
    var parts = s.split('.');
    if (parts.length > 2) {
      var dec = parts.pop();
      s = parts.join('') + '.' + dec;
    }
    return s;
  } catch (e) {
    return '';
  }
}

/**
 * Extract HT/TVA/TTC and TVA taux from OCR text (best-effort).
 * 
 * Returns object with:
 * - ht: string (montant HT)
 * - tva_montant: string (montant TVA)
 * - ttc: string (montant TTC)
 * - tva_taux: string (taux TVA, e.g. "20")
 * 
 * @param {string} txt - OCR text to parse
 * @return {Object} Object with ht, tva_montant, ttc, tva_taux (all strings)
 */
function BM_PARSERS_extractAmounts(txt) {
  var out = { ht: '', tva_montant: '', ttc: '', tva_taux: '' };
  try {
    if (!txt) return out;
    txt = String(txt);
    
    // Rate (e.g. 8.5%, 20%)
    var mRate = txt.match(/\b(\d{1,2}(?:[\.,]\d{1,2})?)\s*%\b/);
    if (mRate && mRate[1]) out.tva_taux = BM_PARSERS_parseAmountFR(mRate[1]);

    // TTC
    var mTTC = txt.match(/\b(?:TOTAL\s*TTC|MONTANT\s*TTC|NET\s*A\s*PAYER|A\s*PAYER)\b[^0-9]{0,20}([0-9][0-9 \.,]{1,15})\s*(?:€|EUR)?/i);
    if (mTTC && mTTC[1]) out.ttc = BM_PARSERS_parseAmountFR(mTTC[1]);

    // HT
    var mHT = txt.match(/\b(?:TOTAL\s*HT|MONTANT\s*HT)\b[^0-9]{0,20}([0-9][0-9 \.,]{1,15})\s*(?:€|EUR)?/i);
    if (mHT && mHT[1]) out.ht = BM_PARSERS_parseAmountFR(mHT[1]);

    // TVA amount
    var mTVA = txt.match(/\b(?:TVA\s*(?:MONTANT)?|MONTANT\s*TVA)\b[^0-9]{0,20}([0-9][0-9 \.,]{1,15})\s*(?:€|EUR)?/i);
    if (mTVA && mTVA[1]) out.tva_montant = BM_PARSERS_parseAmountFR(mTVA[1]);

    return out;
  } catch (e) {
    return out;
  }
}

/**
 * Normalize date in YYYY-MM-DD format, with auto-swap if needed.
 * 
 * If month > 12 but day <= 12, automatically swap (e.g. 2025-14-06 -> 2025-06-14)
 * 
 * @param {string} s - Date string to normalize
 * @return {string} Normalized date YYYY-MM-DD, or original string if no match
 */
function BM_PARSERS_normDateSwapYMD(s) {
  try {
    var v = String(s || '').trim();
    if (!v) return '';
    var m = v.match(/^(\d{4})[\/-](\d{2})[\/-](\d{2})$/);
    if (!m) return v;
    var Y = m[1], A = Number(m[2]), B = Number(m[3]);
    // si "mois" > 12 mais "jour" <= 12 => swap (ex: 2025-14-06 -> 2025-06-14)
    if (A > 12 && B >= 1 && B <= 12) {
      return Y + '-' + String(B).padStart(2, '0') + '-' + String(A).padStart(2, '0');
    }
    return Y + '-' + String(A).padStart(2, '0') + '-' + String(B).padStart(2, '0');
  } catch (e) {
    return String(s || '');
  }
}

/**
 * Extract email address from text using regex.
 * 
 * @param {string} s - Text to search
 * @return {string} Extracted email, or empty string
 */
function BM_PARSERS_extractEmail(s) {
  try {
    var v = String(s || '');
    var mm = v.match(/[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}/i);
    return mm ? String(mm[0]).trim() : '';
  } catch (e) {
    return '';
  }
}

/**
 * Extract supplier name from email local part.
 * 
 * Transforms "john.doe123@example.com" -> "JOHN DOE"
 * Mini-correction: "VER IN" -> "VERIN"
 * 
 * @param {string} email - Email address
 * @return {string} Extracted supplier name (uppercase), or empty string
 */
function BM_PARSERS_supplierNameFromEmail(email) {
  try {
    var e = String(email || '').trim();
    if (!e) return '';
    var local = (e.split('@')[0] || '').trim();
    var name = local
      .replace(/[0-9]+/g, ' ')
      .replace(/[._\-]+/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toUpperCase();
    // mini-correction connue: "VER IN" -> "VERIN"
    name = name.replace(/\bVER\s+IN\b/g, 'VERIN');
    return name.length >= 4 ? name : '';
  } catch (e) {
    return '';
  }
}

/**
 * Test if value is empty (null, undefined, or empty string after trim).
 * 
 * @param {*} v - Value to test
 * @return {boolean} True if empty, false otherwise
 */
function BM_PARSERS_isEmpty(v) {
  return (v === null || v === undefined || String(v).trim() === '');
}
