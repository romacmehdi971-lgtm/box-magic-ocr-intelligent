/**
 * 04_PARSERS.gs
 * BOX MAGIC OCR — Parsers centralisés
 * 
 * Responsabilité unique : Extraction déterministe de données depuis texte OCR
 * 
 * Règles IAPF :
 * - VIDE > BRUIT (aucune invention)
 * - Extraction factuelle uniquement
 * - Déterminisme total (même entrée → même sortie)
 * 
 * Modules :
 * - Extraction numéro facture
 * - Parsing montants FR (HT/TVA/TTC)
 * - Extraction date
 * - Validation format
 * - Sélection texte le plus long (anti-troncature)
 * 
 * @version 2.0.0
 * @date 2026-02-14
 */

// ============================================================
// PARSER — SÉLECTION TEXTE LE PLUS LONG
// ============================================================

/**
 * Pick the longest non-empty text among candidates (strings).
 * Used to avoid losing OCR content when multiple fields exist.
 * 
 * @param {Array<string>} candidates - Liste de candidats texte
 * @return {string} Texte le plus long (ou chaîne vide)
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

// ============================================================
// PARSER — NUMÉRO FACTURE / DOCUMENT
// ============================================================

/**
 * Extract invoice/document number from OCR text (best-effort, deterministic).
 * 
 * Patterns reconnus (FR) :
 * - N° Facture
 * - Numéro pièce
 * - N° Dossier
 * - Facture <numero>
 * 
 * @param {string} txt - Texte OCR brut
 * @return {string} Numéro facture (ou chaîne vide si non trouvé)
 */
function BM_PARSERS_extractInvoiceNumber(txt) {
  try {
    if (!txt) return '';
    txt = String(txt);
    
    // Common French markers
    var patterns = [
      /\b(?:N\s*[°oº]|No|N°)\s*(?:Facture|Pi[eè]ce|Document|Ticket|Dossier)?\s*[:#-]?\s*([A-Z0-9][A-Z0-9\-/]{4,})\b/i,
      /\b(?:Facture)\s*[:#-]?\s*([A-Z0-9][A-Z0-9\-/]{4,})\b/i,
      /\b(?:N\s*Dossier)\s*[:#-]?\s*([0-9]{4,})\b/i,
      /\b(?:Num[eé]ro\s+pi[eè]ce)\s*[:#-]?\s*([0-9]{4,})\b/i
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

// ============================================================
// PARSER — MONTANTS FR (PARSING)
// ============================================================

/**
 * Parse a French amount string to a normalized decimal string with dot.
 * 
 * Exemples :
 * - '593,72' → '593.72'
 * - '1 234,56' → '1234.56'
 * - '1.234,56' → '1234.56'
 * 
 * @param {string} s - Montant format FR
 * @return {string} Montant normalisé avec point décimal
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

// ============================================================
// PARSER — EXTRACTION MONTANTS (HT/TVA/TTC/TAUX)
// ============================================================

/**
 * Extract HT/TVA/TTC and TVA taux from OCR text (best-effort).
 * 
 * Retourne un objet avec :
 * - ht: montant HT (string normalisé)
 * - tva_montant: montant TVA (string normalisé)
 * - ttc: montant TTC (string normalisé)
 * - tva_taux: taux TVA en % (string normalisé)
 * 
 * @param {string} txt - Texte OCR brut
 * @return {Object} {ht, tva_montant, ttc, tva_taux}
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

// ============================================================
// PARSER — EXTRACTION DATE
// ============================================================

/**
 * Extract date from OCR text (best-effort).
 * 
 * Formats reconnus :
 * - DD/MM/YYYY
 * - YYYY-MM-DD
 * - DD-MM-YYYY
 * 
 * @param {string} txt - Texte OCR brut
 * @return {string} Date normalisée YYYY-MM-DD (ou chaîne vide)
 */
function BM_PARSERS_extractDate(txt) {
  try {
    if (!txt) return '';
    txt = String(txt);
    
    // Format DD/MM/YYYY
    var m1 = txt.match(/\b(\d{2})\/(\d{2})\/(\d{4})\b/);
    if (m1) {
      var day = m1[1];
      var month = m1[2];
      var year = m1[3];
      return year + '-' + month + '-' + day;
    }
    
    // Format YYYY-MM-DD (déjà normalisé)
    var m2 = txt.match(/\b(\d{4})-(\d{2})-(\d{2})\b/);
    if (m2) return m2[0];
    
    // Format DD-MM-YYYY
    var m3 = txt.match(/\b(\d{2})-(\d{2})-(\d{4})\b/);
    if (m3) {
      var day2 = m3[1];
      var month2 = m3[2];
      var year2 = m3[3];
      return year2 + '-' + month2 + '-' + day2;
    }
    
    return '';
  } catch (e) {
    return '';
  }
}

// ============================================================
// PARSER — NORMALISATION NUMÉRO FACTURE
// ============================================================

/**
 * Normalize invoice number (cleanup).
 * 
 * - Trim whitespace
 * - Remove leading/trailing special chars
 * 
 * @param {string} num - Numéro brut
 * @return {string} Numéro normalisé
 */
function BM_PARSERS_normalizeInvoiceNumber(num) {
  try {
    if (!num) return '';
    var s = String(num).trim();
    // Remove leading/trailing : - # /
    s = s.replace(/^[:#\-\/]+/, '');
    s = s.replace(/[:#\-\/]+$/, '');
    return s;
  } catch (e) {
    return '';
  }
}

// ============================================================
// PARSER — VALIDATION MONTANT
// ============================================================

/**
 * Validate amount (must be a valid number).
 * 
 * @param {string|number} montant - Montant à valider
 * @return {boolean} true si montant valide, false sinon
 */
function BM_PARSERS_validateAmount(montant) {
  try {
    if (montant === null || montant === undefined) return false;
    var s = String(montant).trim();
    if (!s) return false;
    var n = Number(s);
    return (isFinite(n) && n >= 0);
  } catch (e) {
    return false;
  }
}

// ============================================================
// PARSER — DÉTECTION FOURNISSEUR (IA_SUPPLIERS)
// ============================================================

/**
 * Detect supplier from OCR text using IA_SUPPLIERS reference.
 * 
 * Note: Cette fonction délègue vers R06_IA_MEMORY_SUPPLIERS_APPLY.gs
 * Elle est définie ici pour centraliser l'interface des parsers.
 * 
 * @param {string} txt - Texte OCR brut
 * @param {Object} donnees - Payload document
 * @return {Object} {supplier_name, siret, confidence}
 */
function BM_PARSERS_detectSupplier(txt, donnees) {
  try {
    // Délégation vers R06 (protégé)
    if (typeof R06_SUPPLIER_MEMORY__APPLY_IF_AVAILABLE_ === 'function') {
      return R06_SUPPLIER_MEMORY__APPLY_IF_AVAILABLE_(donnees, '') || {};
    }
    return {};
  } catch (e) {
    return {};
  }
}

// ============================================================
// PARSER — EXTRACTION DONNÉES CANONIQUES (FILENAME FALLBACK)
// ============================================================

/**
 * Extract data from canonical filename (strict fallback only).
 * 
 * Format attendu :
 * YYYY-MM-DD_FOURNISSEUR_TTC_<montant>EUR_<TYPE>_<NUMERO>.pdf
 * 
 * Exemple :
 * 2026-01-13_PROMOCASH_TTC_593.72EUR_FACTURE_777807.pdf
 * 
 * Règles :
 * - Ne remplit QUE si champs vides
 * - Fallback STRICT (ne doit pas écraser données OCR)
 * 
 * @param {string} filename - Nom fichier
 * @return {Object|null} {date_doc, fournisseur, ttc, type, numero_facture} ou null
 */
function BM_PARSERS_extractFromCanonicalFilename(filename) {
  try {
    var name = String(filename || '').trim();
    name = name.replace(/\.pdf$/i, '');
    
    // Example: 2026-01-13_PROMOCASH_TTC_593.72EUR_FACTURE_777807
    var m = name.match(/^([0-9]{4}-[0-9]{2}-[0-9]{2})_([^_]+)_TTC_([0-9]+(?:\.[0-9]{2})?)EUR_(FACTURE|TICKET|RECU)(?:_([^_]+))?$/i);
    if (!m) return null;

    var date_doc = m[1];
    var fournisseur = m[2];
    var ttc_point = m[3];
    var type = String(m[4]).toUpperCase();
    var numero = (m[5] != null && String(m[5]).trim() !== '') ? String(m[5]).trim() : '';

    // Convert 593.72 -> 593,72 for sheet/business fields
    var ttc = String(ttc_point).replace('.', ',');
    
    return {
      date_doc: date_doc,
      fournisseur: fournisseur,
      ttc: ttc,
      type: type,
      numero_facture: numero
    };
  } catch (e) {
    return null;
  }
}

// ============================================================
// PARSER — EXTRACTION DÉTERMINISTE COMPLÈTE (PROMOCASH)
// ============================================================

/**
 * Extract deterministic invoice data from OCR text (full extraction).
 * 
 * Spécialisé pour :
 * - PROMOCASH (numéro pièce 6 chiffres)
 * - Montants HT/TVA/TTC avec patterns FR
 * 
 * Règle IAPF : VIDE > BRUIT
 * Ne remplit QUE si pattern fort détecté
 * 
 * @param {string} txt - Texte OCR brut
 * @return {Object|null} {numero_facture, ht, tva_montant, ttc} ou null
 */
function BM_PARSERS_extractDeterministicInvoiceData(txt) {
  try {
    var s = String(txt || '');
    if (!s) return null;

    // Normaliser espaces
    var flat = s.replace(/\u00A0/g, ' ');

    var out = {
      numero_facture: '',
      ht: '',
      tva_montant: '',
      ttc: ''
    };

    // Numéro de pièce / facture (PROMOCASH / caisse)
    // Exemple (scan) : "Numéro pièce" puis 6 chiffres
    var mNumPiece = flat.match(/(?:Num[eé]ro\s+pi[eè]ce|N°\s*pi[eè]ce)\s*[:\s]*([0-9]{6,})/i);
    if (mNumPiece && mNumPiece[1]) {
      out.numero_facture = String(mNumPiece[1]).trim();
    }

    // Montants (patterns FR)
    var amts = BM_PARSERS_extractAmounts(flat);
    if (amts.ht) out.ht = amts.ht;
    if (amts.tva_montant) out.tva_montant = amts.tva_montant;
    if (amts.ttc) out.ttc = amts.ttc;

    // Si au moins un champ renseigné, on retourne
    if (out.numero_facture || out.ht || out.tva_montant || out.ttc) {
      return out;
    }

    return null;
  } catch (e) {
    return null;
  }
}

// ============================================================
// PARSER — SANITIZE OCR TEXT (CLEANUP)
// ============================================================

/**
 * Sanitize OCR text (cleanup common OCR artifacts).
 * 
 * - Replace non-breaking spaces
 * - Normalize whitespace
 * - Remove control characters
 * 
 * @param {string} txt - Texte OCR brut
 * @return {string} Texte nettoyé
 */
function BM_PARSERS_sanitizeOcrText(txt) {
  try {
    if (!txt) return '';
    var s = String(txt);
    
    // Replace non-breaking spaces
    s = s.replace(/\u00A0/g, ' ');
    
    // Normalize whitespace
    s = s.replace(/\s+/g, ' ');
    
    // Remove control characters
    s = s.replace(/[\x00-\x1F\x7F]/g, '');
    
    return s.trim();
  } catch (e) {
    return '';
  }
}

// ============================================================
// EXPORTS (pour compatibilité avec ancien code)
// ============================================================

// Anciens noms (legacy)
function _BM_pickLongestText_(candidates) {
  return BM_PARSERS_pickLongestText(candidates);
}

function _BM_extractInvoiceNumber_(txt) {
  return BM_PARSERS_extractInvoiceNumber(txt);
}

function _BM_parseAmountFR_(s) {
  return BM_PARSERS_parseAmountFR(s);
}

function _BM_extractAmounts_(txt) {
  return BM_PARSERS_extractAmounts(txt);
}

function _BM_extractFromCanonicalFilename_(filename) {
  return BM_PARSERS_extractFromCanonicalFilename(filename);
}

function _BM_extractDeterministicInvoiceDataFromOcrText_(txt) {
  return BM_PARSERS_extractDeterministicInvoiceData(txt);
}

function _BM_sanitizeOcrText_(txt) {
  return BM_PARSERS_sanitizeOcrText(txt);
}

// ============================================================
// FIN 04_PARSERS.gs
// ============================================================
