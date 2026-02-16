/**
 * 03_OCR_ENGINE.gs
 * BOX MAGIC OCR — Moteur OCR centralisé (3 niveaux)
 * 
 * Responsabilité unique : Appel et orchestration des moteurs OCR
 * 
 * Architecture IAPF validée (CR1/CR2/CR3) :
 * - OCR Level 1 (FAST) : Texte natif PDF uniquement
 * - OCR Level 2 (CONTEXTUAL) : Cloud Run standard (Google Cloud Vision)
 * - OCR Level 3 (MEMORY) : Cloud Run + IA Memory (apprentissage)
 * 
 * Règles IAPF :
 * - OCR = MIROIR DU DOCUMENT (aucune invention)
 * - VIDE > BRUIT (aucune complétion)
 * - Cloud Run = READ-ONLY (source de vérité)
 * 
 * @version 2.0.0
 * @date 2026-02-14
 */

// ============================================================
// OCR LEVEL 1 — FAST (Texte natif PDF)
// ============================================================

/**
 * OCR Level 1 : Extraction texte natif PDF (rapide).
 * 
 * - Pas d'appel Cloud Run
 * - Utilise getTextFromItem() natif Apps Script
 * - Rapide (< 1s)
 * - Fiabilité : bonne pour PDF texte, nulle pour scans
 * 
 * @param {File} fichier - Fichier Drive
 * @return {Object} {level: 1, texte: string, confiance: number, engine: "NATIVE"}
 */
function BM_OCR_ENGINE_Level1_Fast(fichier) {
  try {
    logAction('OCR1', 'OCR1_FAST_START', { file_id: fichier.getId() }, '', 'INFO');
    
    var texte = '';
    
    try {
      // Extraction texte natif PDF
      var blob = fichier.getBlob();
      texte = blob.getDataAsString() || '';
      
      // Fallback : Apps Script Drive API
      if (!texte || texte.length < 50) {
        texte = fichier.getAs('text/plain').getDataAsString() || '';
      }
    } catch (eExtract) {
      logAction('OCR1', 'OCR1_FAST_EXTRACT_FAIL', {
        file_id: fichier.getId(),
        err: String(eExtract)
      }, '', 'WARN');
    }
    
    var confiance = (texte && texte.length > 100) ? 0.9 : 0.3;
    
    logAction('OCR1', 'OCR1_FAST_END', {
      file_id: fichier.getId(),
      texte_length: texte.length,
      confiance: confiance
    }, '', 'INFO');
    
    return {
      level: 1,
      texte: texte,
      confiance: confiance,
      engine: 'NATIVE',
      fields: {},
      mapped: {},
      raw: {}
    };
    
  } catch (e) {
    logAction('OCR1', 'OCR1_FAST_ERROR', {
      file_id: fichier.getId(),
      err: String(e)
    }, '', 'ERREUR');
    
    return {
      level: 1,
      texte: '',
      confiance: 0,
      engine: 'NATIVE',
      fields: {},
      mapped: {},
      raw: {},
      error: String(e)
    };
  }
}

// ============================================================
// OCR LEVEL 2 — CONTEXTUAL (Cloud Run standard)
// ============================================================

/**
 * OCR Level 2 : Cloud Run standard (Google Cloud Vision).
 * 
 * - Appel Cloud Run via OCR__CLOUDRUN_INTEGRATION11.gs
 * - Google Cloud Vision API (DOCUMENT_TEXT_DETECTION)
 * - Extraction structurée (type, société, client, montants)
 * - Confiance tracking
 * 
 * @param {string} fileId - ID fichier Drive
 * @param {File} fichier - Fichier Drive (optionnel)
 * @return {Object} {level: 2, texte: string, confiance: number, engine: "CLOUDRUN", fields: {}, mapped: {}}
 */
function BM_OCR_ENGINE_Level2_Contextual(fileId, fichier) {
  try {
    logAction('OCR2', 'OCR2_CONTEXTUAL_START', { file_id: fileId }, '', 'INFO');
    
    // Appel Cloud Run (délégation vers OCR__CLOUDRUN_INTEGRATION11.gs)
    var ocr = null;
    
    try {
      if (typeof pipelineOCR === 'function') {
        ocr = pipelineOCR(fileId);
      } else {
        logAction('OCR2', 'OCR2_PIPELINE_MISSING', { file_id: fileId }, '', 'ERREUR');
        return {
          level: 2,
          texte: '',
          confiance: 0,
          engine: 'CLOUDRUN',
          fields: {},
          mapped: {},
          raw: {},
          error: 'pipelineOCR function not found'
        };
      }
    } catch (eOcr) {
      logAction('OCR2', 'OCR2_CLOUDRUN_CALL_FAIL', {
        file_id: fileId,
        err: String(eOcr)
      }, '', 'ERREUR');
      
      return {
        level: 2,
        texte: '',
        confiance: 0,
        engine: 'CLOUDRUN',
        fields: {},
        mapped: {},
        raw: {},
        error: String(eOcr)
      };
    }
    
    // Extraction texte (anti-troncature : prendre le plus long)
    var texte = '';
    
    if (ocr) {
      var cand1 = String((ocr && ocr.texte) ? ocr.texte : '');
      var cand2 = String((ocr && ocr.fields && ocr.fields.texte_ocr_brut) ? ocr.fields.texte_ocr_brut : '');
      var cand3 = String((ocr && ocr.raw && ocr.raw.ocr_text_raw) ? ocr.raw.ocr_text_raw : '');
      
      texte = BM_PARSERS_pickLongestText([cand1, cand2, cand3]);
      texte = BM_PARSERS_sanitizeOcrText(texte);
    }
    
    var confiance = Number((ocr && ocr.confiance) ? ocr.confiance : 0) || 0;
    var engine = String((ocr && ocr.engine) ? ocr.engine : 'CLOUDRUN').trim().toUpperCase();
    var fields = (ocr && ocr.fields && typeof ocr.fields === 'object') ? ocr.fields : {};
    var mapped = (ocr && ocr.mapped && typeof ocr.mapped === 'object') ? ocr.mapped : {};
    var raw = (ocr && ocr.raw && typeof ocr.raw === 'object') ? ocr.raw : {};
    
    logAction('OCR2', 'OCR2_CONTEXTUAL_END', {
      file_id: fileId,
      texte_length: texte.length,
      confiance: confiance,
      engine: engine
    }, '', 'INFO');
    
    return {
      level: 2,
      texte: texte,
      confiance: confiance,
      engine: engine,
      fields: fields,
      mapped: mapped,
      raw: raw
    };
    
  } catch (e) {
    logAction('OCR2', 'OCR2_CONTEXTUAL_ERROR', {
      file_id: fileId,
      err: String(e)
    }, '', 'ERREUR');
    
    return {
      level: 2,
      texte: '',
      confiance: 0,
      engine: 'CLOUDRUN',
      fields: {},
      mapped: {},
      raw: {},
      error: String(e)
    };
  }
}

// ============================================================
// OCR LEVEL 3 — MEMORY (Cloud Run + IA Memory)
// ============================================================

/**
 * OCR Level 3 : Cloud Run + IA Memory (apprentissage).
 * 
 * - Appel Cloud Run (Level 2)
 * - Application règles IA_SUPPLIERS (R06)
 * - Apprentissage progressif (template signature)
 * - Seuil confiance 99-100% pour auto-validation
 * 
 * Règle IAPF : POST_VALIDATION_ONLY
 * - Auto-learn désactivé (source unique = validation humaine)
 * - Lecture IA_SUPPLIERS uniquement
 * 
 * @param {string} fileId - ID fichier Drive
 * @param {File} fichier - Fichier Drive (optionnel)
 * @param {Object} donnees - Payload document (modifié par référence)
 * @return {Object} {level: 3, texte: string, confiance: number, engine: "CLOUDRUN+MEMORY", fields: {}, mapped: {}, rule_created: {}}
 */
function BM_OCR_ENGINE_Level3_Memory(fileId, fichier, donnees) {
  try {
    logAction('OCR3', 'OCR3_MEMORY_START', { file_id: fileId }, '', 'INFO');
    
    // Étape 1 : OCR Level 2 (Cloud Run)
    var ocr = BM_OCR_ENGINE_Level2_Contextual(fileId, fichier);
    
    if (ocr.error) {
      logAction('OCR3', 'OCR3_CLOUDRUN_FAIL', {
        file_id: fileId,
        err: ocr.error
      }, '', 'ERREUR');
      
      return {
        level: 3,
        texte: ocr.texte || '',
        confiance: 0,
        engine: 'CLOUDRUN+MEMORY',
        fields: ocr.fields || {},
        mapped: ocr.mapped || {},
        raw: ocr.raw || {},
        error: ocr.error
      };
    }
    
    // Étape 2 : IA_SUPPLIERS (R06) — Application règles fournisseurs
    var r06 = {};
    
    try {
      if (typeof R06_SUPPLIER_MEMORY__APPLY_IF_AVAILABLE_ === 'function') {
        r06 = R06_SUPPLIER_MEMORY__APPLY_IF_AVAILABLE_(donnees, fileId) || {};
        
        logAction('OCR3', 'OCR3_IA_SUPPLIERS_APPLY', {
          file_id: fileId,
          ok: !!r06.ok,
          applied: !!r06.applied,
          reason: r06.reason || '',
          siret14: r06.siret14 || r06.siret || '',
          fields_written: r06.fields_written || []
        }, '', 'INFO');
      } else {
        logAction('OCR3', 'OCR3_IA_SUPPLIERS_MISSING', {
          file_id: fileId
        }, '', 'WARN');
      }
    } catch (eR06) {
      logAction('OCR3', 'OCR3_IA_SUPPLIERS_ERROR', {
        file_id: fileId,
        err: String(eR06)
      }, '', 'ERREUR');
    }
    
    // Étape 3 : Règle OCR (template signature) — LECTURE UNIQUEMENT
    var rule_created = (ocr && ocr.rule_created) ? ocr.rule_created : null;
    var templateSig = rule_created ? String(rule_created.template_signature || '').trim() : '';
    var hashDoc = rule_created ? String(rule_created.hash_document || '').trim() : '';
    
    if (rule_created && (templateSig || hashDoc)) {
      var alreadyKnown = false;
      
      try {
        if (typeof BM_IAMEMORY_hasTemplateSignature_ === 'function') {
          alreadyKnown = BM_IAMEMORY_hasTemplateSignature_(templateSig);
        }
      } catch (eCheck) {
        logAction('OCR3', 'OCR3_TEMPLATE_CHECK_WARN', {
          file_id: fileId,
          template_signature: templateSig,
          err: String(eCheck)
        }, '', 'WARN');
      }
      
      logAction('OCR3', 'OCR3_TEMPLATE_DECISION', {
        file_id: fileId,
        learn: false,
        already_known: alreadyKnown,
        reason: alreadyKnown ? 'TEMPLATE_FOUND_IN_MEMORY' : 'AUTO_LEARN_DISABLED_BY_GOVERNANCE',
        template_signature: templateSig,
        hash_document: hashDoc
      }, '', 'INFO');
    } else {
      logAction('OCR3', 'OCR3_NO_TEMPLATE', {
        file_id: fileId
      }, '', 'INFO');
    }
    
    logAction('OCR3', 'OCR3_MEMORY_END', {
      file_id: fileId,
      texte_length: ocr.texte.length,
      confiance: ocr.confiance,
      r06_applied: !!r06.applied
    }, '', 'INFO');
    
    return {
      level: 3,
      texte: ocr.texte,
      confiance: ocr.confiance,
      engine: 'CLOUDRUN+MEMORY',
      fields: ocr.fields,
      mapped: ocr.mapped,
      raw: ocr.raw,
      rule_created: rule_created,
      r06_result: r06
    };
    
  } catch (e) {
    logAction('OCR3', 'OCR3_MEMORY_ERROR', {
      file_id: fileId,
      err: String(e)
    }, '', 'ERREUR');
    
    return {
      level: 3,
      texte: '',
      confiance: 0,
      engine: 'CLOUDRUN+MEMORY',
      fields: {},
      mapped: {},
      raw: {},
      error: String(e)
    };
  }
}

// ============================================================
// OCR ENGINE ROUTER — Sélection automatique du niveau
// ============================================================

/**
 * Sélection automatique du niveau OCR en fonction du fichier.
 * 
 * Logique :
 * - PDF texte natif → Level 1 (Fast)
 * - PDF scan / Image → Level 2 (Contextual)
 * - Document récurrent (fournisseur connu) → Level 3 (Memory)
 * 
 * @param {File} fichier - Fichier Drive
 * @param {string} fileId - ID fichier Drive
 * @param {Object} donnees - Payload document
 * @return {Object} Résultat OCR avec level détecté
 */
function BM_OCR_ENGINE_Auto(fichier, fileId, donnees) {
  try {
    logAction('OCR', 'OCR_AUTO_START', { file_id: fileId }, '', 'INFO');
    
    var mimeType = fichier.getMimeType();
    var fileName = fichier.getName();
    
    // Détection type fichier
    var isPdf = (mimeType === 'application/pdf');
    var isImage = (mimeType.indexOf('image/') === 0);
    
    // Par défaut : Level 2 (Cloud Run standard)
    var selectedLevel = 2;
    
    // Si PDF texte natif détectable → Level 1
    try {
      if (isPdf) {
        var level1 = BM_OCR_ENGINE_Level1_Fast(fichier);
        
        // Si texte natif valide (>100 chars), utiliser Level 1
        if (level1.texte && level1.texte.length > 100 && level1.confiance >= 0.8) {
          logAction('OCR', 'OCR_AUTO_DECISION', {
            file_id: fileId,
            selected_level: 1,
            reason: 'NATIVE_TEXT_VALID'
          }, '', 'INFO');
          
          return level1;
        }
      }
    } catch (eLevel1) {
      logAction('OCR', 'OCR_AUTO_LEVEL1_FAIL', {
        file_id: fileId,
        err: String(eLevel1)
      }, '', 'WARN');
    }
    
    // Sinon : Level 2 (Cloud Run) par défaut
    logAction('OCR', 'OCR_AUTO_DECISION', {
      file_id: fileId,
      selected_level: 2,
      reason: 'DEFAULT_CLOUDRUN'
    }, '', 'INFO');
    
    return BM_OCR_ENGINE_Level2_Contextual(fileId, fichier);
    
  } catch (e) {
    logAction('OCR', 'OCR_AUTO_ERROR', {
      file_id: fileId,
      err: String(e)
    }, '', 'ERREUR');
    
    return {
      level: 0,
      texte: '',
      confiance: 0,
      engine: 'AUTO',
      fields: {},
      mapped: {},
      raw: {},
      error: String(e)
    };
  }
}

// ============================================================
// EXPORTS (pour compatibilité avec ancien code)
// ============================================================

/**
 * pipelineOCR — Point d'entrée principal (ancien nom conservé).
 * 
 * @param {string} fileId - ID fichier Drive
 * @return {Object} Résultat OCR
 */
function pipelineOCR(fileId) {
  try {
    var fichier = DriveApp.getFileById(fileId);
    var donnees = {};
    
    // Auto-sélection niveau OCR
    var result = BM_OCR_ENGINE_Auto(fichier, fileId, donnees);
    
    return result;
  } catch (e) {
    logAction('OCR', 'PIPELINE_OCR_ERROR', {
      file_id: fileId,
      err: String(e)
    }, '', 'ERREUR');
    
    return {
      level: 0,
      texte: '',
      confiance: 0,
      engine: 'PIPELINE',
      fields: {},
      mapped: {},
      raw: {},
      error: String(e)
    };
  }
}

// ============================================================
// FIN 03_OCR_ENGINE.gs
// ============================================================
