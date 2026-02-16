/**
 * 05_PIPELINE_MAPPER.gs
 * BOX MAGIC OCR — Mapping OCR → Payload normalisé
 * 
 * Responsabilité : Transformer résultat OCR en payload structuré
 * 
 * @version 2.0.0
 * @date 2026-02-14
 */

// ============================================================
// PIPELINE — MAPPING OCR → PAYLOAD
// ============================================================

function BM_PIPELINE_mapOcrToPayload(ocr, fichier) {
  try {
    const donnees = {};
    
    logAction('PIPELINE', 'MAP_START', {
      file_id: fichier.getId(),
      ocr_level: ocr.level || 0
    }, '', 'INFO');
    
    // 1. Mapping base depuis OCR.mapped
    if (ocr.mapped && typeof ocr.mapped === 'object') {
      Object.assign(donnees, ocr.mapped);
    }
    
    // 2. Extraction via parsers depuis texte OCR
    if (ocr.texte) {
      BM_PIPELINE_extractFromText(donnees, ocr.texte);
    }
    
    // 3. Enrichissement depuis OCR.fields
    if (ocr.fields && typeof ocr.fields === 'object') {
      BM_PIPELINE_enrichFromFields(donnees, ocr.fields);
    }
    
    // 4. Normalisation champs
    BM_PIPELINE_normalizeFields(donnees);
    
    // 5. Validation cohérence
    const validation = BM_PIPELINE_validatePayload(donnees);
    donnees._validation = validation;
    
    logAction('PIPELINE', 'MAP_END', {
      file_id: fichier.getId(),
      fields_count: Object.keys(donnees).length,
      validation_ok: validation.valid
    }, '', 'INFO');
    
    return donnees;
    
  } catch (e) {
    logAction('PIPELINE', 'MAP_ERROR', {
      file_id: fichier.getId(),
      err: String(e)
    }, '', 'ERREUR');
    return {};
  }
}

// ============================================================
// PIPELINE — EXTRACTION DEPUIS TEXTE OCR
// ============================================================

function BM_PIPELINE_extractFromText(donnees, texte) {
  try {
    // Extraction numéro facture (si vide)
    if (!donnees.numero_facture) {
      const numFacture = BM_PARSERS_extractInvoiceNumber(texte);
      if (numFacture) donnees.numero_facture = numFacture;
    }
    
    // Extraction montants (si vides)
    if (!donnees.montants || typeof donnees.montants !== 'object') {
      donnees.montants = {};
    }
    
    const amounts = BM_PARSERS_extractAmounts(texte);
    
    if (amounts.ht && !donnees.montants.ht) {
      donnees.montants.ht = amounts.ht;
    }
    
    if (amounts.tva_montant && !donnees.montants.tva) {
      donnees.montants.tva = amounts.tva_montant;
    }
    
    if (amounts.ttc && !donnees.montants.ttc) {
      donnees.montants.ttc = amounts.ttc;
    }
    
    if (amounts.tva_taux && !donnees.tva_taux) {
      donnees.tva_taux = amounts.tva_taux;
    }
    
    // Extraction date (si vide)
    if (!donnees.date_document) {
      const dateDoc = BM_PARSERS_extractDate(texte);
      if (dateDoc) donnees.date_document = dateDoc;
    }
    
  } catch (e) {
    logAction('PIPELINE', 'EXTRACT_TEXT_ERROR', {err: String(e)}, '', 'WARN');
  }
}

// ============================================================
// PIPELINE — ENRICHISSEMENT DEPUIS FIELDS OCR
// ============================================================

function BM_PIPELINE_enrichFromFields(donnees, fields) {
  try {
    // Helper : set si champ vide
    function setIfMissing(key, value) {
      if (!donnees[key] && value !== null && value !== undefined && String(value).trim() !== '') {
        donnees[key] = value;
      }
    }
    
    // Type document
    setIfMissing('type', fields.type || fields.document_type);
    
    // Numéro facture
    setIfMissing('numero_facture', fields.numero_facture || fields.numero_doc);
    
    // Société émettrice
    setIfMissing('societe', fields.societe || fields.societe_emettrice || fields.entreprise_source);
    
    // Client (reject "Unknown")
    const clientValue = fields.client_nom || fields.client;
    if (clientValue && String(clientValue).toUpperCase() !== 'UNKNOWN') {
      setIfMissing('client', clientValue);
    }
    
    // Date document (normalisation si yyyy-dd-mm)
    const dateValue = fields.date_doc || fields.date_emission || fields.date_document || fields.date_facture;
    if (dateValue) {
      const normalized = BM_PIPELINE_normalizeDateSwapYMD(dateValue);
      setIfMissing('date_document', normalized);
    }
    
    // Montants
    if (!donnees.montants) donnees.montants = {};
    
    function setAmountIfMissing(key, value) {
      if (value !== null && value !== undefined) {
        const s = String(value).trim();
        if (s && s !== '0' && s !== '') {
          const normalized = s.replace(/\s/g, '').replace(',', '.');
          const n = Number(normalized);
          if (isFinite(n) && n > 0) {
            if (!donnees.montants[key] || Number(donnees.montants[key]) === 0) {
              donnees.montants[key] = n;
            }
          }
        }
      }
    }
    
    setAmountIfMissing('ttc', fields.ttc || fields.total_ttc);
    setAmountIfMissing('ht', fields.ht || fields.montant_ht);
    setAmountIfMissing('tva', fields.tva_montant || fields.montant_tva);
    
    // Taux TVA
    const tauxValue = fields.tva_taux || fields.tva_rate;
    if (tauxValue) {
      setIfMissing('tva_taux', String(tauxValue).trim());
    }
    
    // Champs étendus
    setIfMissing('date_prestation', fields.date_prestation);
    setIfMissing('lieu_livraison', fields.lieu_livraison);
    setIfMissing('prestation_type', fields.prestation_type);
    setIfMissing('prestation_detail', fields.prestation_detail);
    setIfMissing('prestation_inclus', fields.prestation_inclus);
    
    if (fields.nb_personnes !== undefined && fields.nb_personnes !== null) {
      const nbPers = Number(fields.nb_personnes);
      if (isFinite(nbPers) && nbPers > 0) {
        setIfMissing('nb_personnes', nbPers);
      }
    }
    
    // Client détaillé
    setIfMissing('client_nom', fields.client_nom);
    setIfMissing('client_adresse', fields.client_adresse);
    setIfMissing('client_code_postal', fields.client_code_postal);
    setIfMissing('client_ville', fields.client_ville);
    
  } catch (e) {
    logAction('PIPELINE', 'ENRICH_FIELDS_ERROR', {err: String(e)}, '', 'WARN');
  }
}

// ============================================================
// PIPELINE — NORMALISATION DATE (SWAP Y-M-D si nécessaire)
// ============================================================

function BM_PIPELINE_normalizeDateSwapYMD(s) {
  try {
    const v = String(s || '').trim();
    if (!v) return '';
    
    // Format yyyy-mm-dd (ou yyyy-dd-mm à corriger)
    const m = v.match(/^(\d{4})[\/-](\d{2})[\/-](\d{2})$/);
    if (!m) return v;
    
    const Y = m[1];
    const A = Number(m[2]);
    const B = Number(m[3]);
    
    // Si "mois" > 12 mais "jour" <= 12 => swap (ex: 2025-14-06 -> 2025-06-14)
    if (A > 12 && B >= 1 && B <= 12) {
      return Y + '-' + String(B).padStart(2, '0') + '-' + String(A).padStart(2, '0');
    }
    
    return Y + '-' + String(A).padStart(2, '0') + '-' + String(B).padStart(2, '0');
    
  } catch (e) {
    return String(s || '');
  }
}

// ============================================================
// PIPELINE — NORMALISATION CHAMPS
// ============================================================

function BM_PIPELINE_normalizeFields(donnees) {
  try {
    // Type en majuscules
    if (donnees.type) {
      donnees.type = String(donnees.type).trim().toUpperCase();
    }
    
    // Numéro facture normalisé
    if (donnees.numero_facture) {
      donnees.numero_facture = BM_PARSERS_normalizeInvoiceNumber(donnees.numero_facture);
    }
    
    // Montants: garantir structure
    if (!donnees.montants || typeof donnees.montants !== 'object') {
      donnees.montants = {};
    }
    
    // Valider montants
    ['ht', 'tva', 'ttc'].forEach(function(key) {
      if (donnees.montants[key] !== undefined && donnees.montants[key] !== null) {
        const val = donnees.montants[key];
        if (!BM_PARSERS_validateAmount(val)) {
          delete donnees.montants[key];
        }
      }
    });
    
  } catch (e) {
    logAction('PIPELINE', 'NORMALIZE_ERROR', {err: String(e)}, '', 'WARN');
  }
}

// ============================================================
// PIPELINE — VALIDATION COHÉRENCE PAYLOAD
// ============================================================

function BM_PIPELINE_validatePayload(donnees) {
  const errors = [];
  const warnings = [];
  
  try {
    // Champs obligatoires
    if (!donnees.type || String(donnees.type).trim() === '') {
      errors.push('TYPE_MISSING');
    }
    
    // Cohérence montants (HT + TVA = TTC)
    if (donnees.montants && donnees.montants.ht && donnees.montants.tva && donnees.montants.ttc) {
      const ht = Number(donnees.montants.ht);
      const tva = Number(donnees.montants.tva);
      const ttc = Number(donnees.montants.ttc);
      
      const expected = ht + tva;
      const diff = Math.abs(ttc - expected);
      
      // Tolérance 0.01 (arrondi)
      if (diff > 0.01) {
        warnings.push('AMOUNTS_INCOHERENT: HT+TVA=' + expected.toFixed(2) + ' vs TTC=' + ttc.toFixed(2));
      }
    }
    
    // Date valide
    if (donnees.date_document) {
      const datePattern = /^\d{4}-\d{2}-\d{2}$/;
      if (!datePattern.test(donnees.date_document)) {
        warnings.push('DATE_FORMAT_INVALID: ' + donnees.date_document);
      }
    }
    
    return {
      valid: (errors.length === 0),
      errors: errors,
      warnings: warnings
    };
    
  } catch (e) {
    return {
      valid: false,
      errors: ['VALIDATION_ERROR: ' + String(e)],
      warnings: []
    };
  }
}

// ============================================================
// FIN 05_PIPELINE_MAPPER.gs
// ============================================================
