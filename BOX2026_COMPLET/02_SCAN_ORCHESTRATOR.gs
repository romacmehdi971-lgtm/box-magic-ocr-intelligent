/**
 * 02_SCAN_ORCHESTRATOR.gs
 * BOX MAGIC OCR — Orchestrateur principal
 * 
 * Responsabilité : Workflow complet de traitement document
 * 
 * REMPLACE : 02_SCAN_WORKER.gs
 * 
 * Architecture modulaire :
 * - 01_SCAN_ROUTING_GUARD → Guards
 * - 03_OCR_ENGINE → OCR
 * - 04_PARSERS → Extraction
 * - 05_PIPELINE_MAPPER → Mapping
 * - 06_OCR_INJECTION → Index
 * - 07_POST_VALIDATION → Validation finale
 * - R06_IA_MEMORY_SUPPLIERS → IA Memory
 * 
 * @version 2.0.0
 * @date 2026-02-14
 */

// ============================================================
// ORCHESTRATEUR — POINT D'ENTRÉE PRINCIPAL
// ============================================================

function traiterNouveauDocument(fichier) {
  try {
    const fileId = fichier.getId();
    const nom = fichier.getName();
    
    logAction('ORCHESTRATOR', 'START', {
      file_id: fileId,
      nom: nom
    }, '', 'INFO');
    
    // ========================================
    // PHASE 1 : ROUTING GUARD
    // ========================================
    const guard = BM_ROUTING_shouldProcess(fichier);
    
    if (!guard.should_process) {
      logAction('ORCHESTRATOR', 'SKIP', {
        file_id: fileId,
        reason: guard.reason,
        details: guard.details
      }, '', 'INFO');
      return;
    }
    
    // ========================================
    // PHASE 2 : NORMALISATION (optionnelle)
    // ========================================
    let normalizedId = fileId;
    
    try {
      if (typeof BM_PIPELINE_normalizeForOcr_ === 'function') {
        const norm = BM_PIPELINE_normalizeForOcr_(fileId, nom);
        if (norm && norm.fileIdForOcr) {
          normalizedId = norm.fileIdForOcr;
          logAction('ORCHESTRATOR', 'NORMALIZE_SUCCESS', {
            file_id: fileId,
            normalized_id: normalizedId
          }, '', 'INFO');
        }
      }
    } catch (eNorm) {
      logAction('ORCHESTRATOR', 'NORMALIZE_WARN', {
        file_id: fileId,
        err: String(eNorm)
      }, '', 'WARN');
    }
    
    // ========================================
    // PHASE 3 : OCR (via 03_OCR_ENGINE)
    // ========================================
    const ocr = BM_OCR_ENGINE_Auto(fichier, normalizedId, {});
    
    if (ocr.error) {
      logAction('ORCHESTRATOR', 'OCR_FAIL', {
        file_id: fileId,
        err: ocr.error
      }, '', 'ERREUR');
      // Continuer quand même avec payload vide
    }
    
    // ========================================
    // PHASE 4 : MAPPING (via 05_PIPELINE_MAPPER)
    // ========================================
    let donnees = BM_PIPELINE_mapOcrToPayload(ocr, fichier);
    
    // ========================================
    // PHASE 5 : IA_SUPPLIERS (R06 - PROTÉGÉ)
    // ========================================
    try {
      if (typeof R06_SUPPLIER_MEMORY__APPLY_IF_AVAILABLE_ === 'function') {
        const r06 = R06_SUPPLIER_MEMORY__APPLY_IF_AVAILABLE_(donnees, fileId) || {};
        
        logAction('ORCHESTRATOR', 'R06_APPLIED', {
          file_id: fileId,
          ok: !!r06.ok,
          applied: !!r06.applied,
          reason: r06.reason || '',
          siret14: r06.siret14 || ''
        }, '', 'INFO');
      }
    } catch (eR06) {
      logAction('ORCHESTRATOR', 'R06_ERROR', {
        file_id: fileId,
        err: String(eR06)
      }, '', 'WARN');
    }
    
    // ========================================
    // PHASE 6 : PROPOSITION CLASSEMENT
    // ========================================
    const proposition = proposerClassement(donnees);
    
    logAction('ORCHESTRATOR', 'CLASSEMENT_PROPOSED', {
      file_id: fileId,
      chemin: proposition.chemin || '',
      auto: !!proposition.auto
    }, '', 'INFO');
    
    // ========================================
    // PHASE 7 : INJECTION INDEX (via 06_OCR_INJECTION)
    // ========================================
    const injection = BM_INJECTION_writeToIndex(fichier, donnees, proposition);
    
    if (!injection.ok) {
      logAction('ORCHESTRATOR', 'INJECTION_FAIL', {
        file_id: fileId,
        err: injection.error || 'Unknown error'
      }, '', 'ERREUR');
    }
    
    // ========================================
    // PHASE 8 : CRM (si applicable - PROTÉGÉ)
    // ========================================
    try {
      // Client (création ou enrichissement)
      if (typeof BM_CRM_CLIENT_upsertFromDonnees_ === 'function') {
        BM_CRM_CLIENT_upsertFromDonnees_(donnees);
      }
      
      // Facture (append si type FACTURE)
      if (String(donnees.type || '').toUpperCase() === 'FACTURE') {
        if (typeof BM_CRM_FACTURE_appendFromDonnees_ === 'function') {
          BM_CRM_FACTURE_appendFromDonnees_(donnees);
        }
      }
    } catch (eCrm) {
      logAction('ORCHESTRATOR', 'CRM_WARN', {
        file_id: fileId,
        err: String(eCrm)
      }, '', 'WARN');
    }
    
    // ========================================
    // FIN ORCHESTRATION
    // ========================================
    logAction('ORCHESTRATOR', 'END', {
      file_id: fileId,
      type: donnees.type || 'autre',
      confiance: Number(donnees.confiance || 0)
    }, '', 'INFO');
    
  } catch (e) {
    logAction('ORCHESTRATOR', 'ERROR', {
      file_id: fichier.getId(),
      stack: String(e && e.stack ? e.stack : e)
    }, '', 'ERREUR');
  }
}

// ============================================================
// ORCHESTRATEUR — PROPOSITION CLASSEMENT
// ============================================================

function proposerClassement(donnees) {
  try {
    const soc = String(donnees.societe || '').trim();
    const typ = String(donnees.type || '').trim().toUpperCase();
    
    // Année: priorité date_document, sinon année courante
    const y = (function() {
      const d = String(donnees.date_document || '').trim();
      let m = d.match(/\b(\d{2})\/(\d{2})\/(\d{4})\b/);
      if (m) return Number(m[3]);
      m = d.match(/\b(\d{4})-(\d{2})-(\d{2})\b/);
      if (m) return Number(m[1]);
      return new Date().getFullYear();
    })();
    
    // Règle canonique (sans sous-dossier client)
    if (soc === "MARTIN'S TRAITEUR" && typ === 'FACTURE') {
      const chemin = 'HOLDING / 03_CLIENTS / MARTINS_TRAITEUR / 01_COMPTABILITE / 02_FACTURES_CLIENTS / ' + y;
      
      logAction('R07', 'PATH_PROPOSED_FROM_RULE', {
        societe: soc,
        type: typ,
        annee: y,
        chemin_final: chemin
      }, '', 'INFO');
      
      return {
        chemin: chemin,
        auto: true,
        from_rule: true,
        annee: y
      };
    }
    
    // Fallback: comportement existant
    return {
      chemin: String(donnees.chemin || ''),
      auto: false
    };
    
  } catch (e) {
    logAction('ORCHESTRATOR', 'CLASSEMENT_ERROR', {err: String(e)}, '', 'WARN');
    return {
      chemin: '',
      auto: false
    };
  }
}

// ============================================================
// ORCHESTRATEUR — HELPERS (COMPATIBILITÉ LEGACY)
// ============================================================

/**
 * enregistrerDansIndex - Alias pour compatibilité legacy
 * Délègue vers 06_OCR_INJECTION
 */
function enregistrerDansIndex(fichier, donnees, proposition) {
  return BM_INJECTION_writeToIndex(fichier, donnees, proposition);
}

// ============================================================
// FIN 02_SCAN_ORCHESTRATOR.gs
// ============================================================
