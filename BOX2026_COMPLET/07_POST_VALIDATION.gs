/**
 * 07_POST_VALIDATION.gs
 * BOX MAGIC OCR — Post-validation + Écritures
 * 
 * Responsabilité : Validation finale, renommage, classement, CRM
 * 
 * Règle IAPF : POST_VALIDATION_ONLY
 * Aucune action destructive sans validation humaine explicite
 * 
 * @version 2.0.0
 * @date 2026-02-14
 */

// ============================================================
// POST-VALIDATION — VALIDATION FINALE DOCUMENT
// ============================================================

function BM_POSTVAL_validateDocument(fichier, donnees) {
  const errors = [];
  const warnings = [];
  
  try {
    // 1. Champs obligatoires
    if (!donnees.type) {
      errors.push('TYPE_MISSING');
    }
    
    if (!donnees.numero_facture && String(donnees.type || '').toUpperCase() === 'FACTURE') {
      warnings.push('NUMERO_FACTURE_MISSING');
    }
    
    // 2. Montants cohérents
    if (donnees.montants) {
      const ht = Number(donnees.montants.ht || 0);
      const tva = Number(donnees.montants.tva || 0);
      const ttc = Number(donnees.montants.ttc || 0);
      
      if (ht > 0 && tva > 0 && ttc > 0) {
        const expected = ht + tva;
        const diff = Math.abs(ttc - expected);
        
        if (diff > 0.10) { // Tolérance 10 centimes
          warnings.push('AMOUNTS_INCOHERENT: ' + diff.toFixed(2) + '€ diff');
        }
      }
    }
    
    // 3. Date valide
    if (donnees.date_document) {
      const pattern = /^\d{4}-\d{2}-\d{2}$/;
      if (!pattern.test(donnees.date_document)) {
        errors.push('DATE_FORMAT_INVALID: ' + donnees.date_document);
      }
    }
    
    // 4. Nom final générable
    const nomFinal = BM_POSTVAL_generateNomFinal(donnees);
    if (!nomFinal) {
      warnings.push('NOM_FINAL_NOT_GENERABLE');
    }
    
    return {
      valid: (errors.length === 0),
      errors: errors,
      warnings: warnings,
      nom_final: nomFinal
    };
    
  } catch (e) {
    return {
      valid: false,
      errors: ['VALIDATION_ERROR: ' + String(e)],
      warnings: [],
      nom_final: ''
    };
  }
}

// ============================================================
// POST-VALIDATION — GÉNÉRATION NOM FINAL
// ============================================================

function BM_POSTVAL_generateNomFinal(donnees) {
  try {
    // Format canonique : YYYY-MM-DD_FOURNISSEUR_TTC_<montant>EUR_FACTURE_<numero>.pdf
    
    // 1. Date
    let dateStr = '';
    if (donnees.date_document) {
      const m = String(donnees.date_document).match(/^(\d{4}-\d{2}-\d{2})/);
      if (m) dateStr = m[1];
    }
    if (!dateStr) {
      const now = new Date();
      dateStr = now.getFullYear() + '-' + 
                String(now.getMonth() + 1).padStart(2, '0') + '-' + 
                String(now.getDate()).padStart(2, '0');
    }
    
    // 2. Fournisseur
    let fournisseur = String(donnees.societe || 'UNKNOWN').trim().toUpperCase();
    fournisseur = fournisseur.replace(/[^A-Z0-9]/g, '_');
    if (fournisseur.length > 30) fournisseur = fournisseur.substring(0, 30);
    
    // 3. Montant TTC
    let montantStr = '';
    if (donnees.montants && donnees.montants.ttc) {
      const ttc = Number(donnees.montants.ttc);
      if (isFinite(ttc) && ttc > 0) {
        montantStr = ttc.toFixed(2).replace('.', '-');
      }
    }
    if (!montantStr) montantStr = '0-00';
    
    // 4. Type
    let type = String(donnees.type || 'AUTRE').trim().toUpperCase();
    type = type.replace(/[^A-Z]/g, '_');
    
    // 5. Numéro
    let numero = '';
    if (donnees.numero_facture) {
      numero = String(donnees.numero_facture).trim().replace(/[^A-Z0-9\-]/gi, '');
      if (numero.length > 20) numero = numero.substring(0, 20);
    }
    
    // Construction
    let nomFinal = dateStr + '_' + fournisseur + '_TTC_' + montantStr + 'EUR_' + type;
    if (numero) {
      nomFinal += '_' + numero;
    }
    nomFinal += '.pdf';
    
    return nomFinal;
    
  } catch (e) {
    logAction('POSTVAL', 'GENERATE_NAME_ERROR', {err: String(e)}, '', 'WARN');
    return '';
  }
}

// ============================================================
// POST-VALIDATION — RENOMMAGE FICHIER (AVEC VALIDATION)
// ============================================================

function BM_POSTVAL_renameFile(fichier, nomFinal, validationRequired) {
  try {
    if (validationRequired !== true) {
      logAction('POSTVAL', 'RENAME_BLOCKED', {
        file_id: fichier.getId(),
        reason: 'POST_VALIDATION_ONLY',
        details: 'Renommage requis validation humaine explicite'
      }, '', 'INFO');
      return {ok: false, reason: 'POST_VALIDATION_ONLY'};
    }
    
    if (!nomFinal || String(nomFinal).trim() === '') {
      logAction('POSTVAL', 'RENAME_INVALID_NAME', {
        file_id: fichier.getId()
      }, '', 'ERREUR');
      return {ok: false, reason: 'INVALID_NAME'};
    }
    
    fichier.setName(nomFinal);
    
    logAction('POSTVAL', 'RENAME_SUCCESS', {
      file_id: fichier.getId(),
      old_name: fichier.getName(),
      new_name: nomFinal
    }, '', 'INFO');
    
    return {ok: true, new_name: nomFinal};
    
  } catch (e) {
    logAction('POSTVAL', 'RENAME_ERROR', {
      file_id: fichier.getId(),
      err: String(e)
    }, '', 'ERREUR');
    return {ok: false, reason: String(e)};
  }
}

// ============================================================
// POST-VALIDATION — DÉPLACEMENT FICHIER (AVEC VALIDATION)
// ============================================================

function BM_POSTVAL_moveToFolder(fichier, cheminFinal, validationRequired) {
  try {
    if (validationRequired !== true) {
      logAction('POSTVAL', 'MOVE_BLOCKED', {
        file_id: fichier.getId(),
        reason: 'POST_VALIDATION_ONLY',
        details: 'Déplacement requis validation humaine explicite'
      }, '', 'INFO');
      return {ok: false, reason: 'POST_VALIDATION_ONLY'};
    }
    
    if (!cheminFinal || String(cheminFinal).trim() === '') {
      logAction('POSTVAL', 'MOVE_INVALID_PATH', {
        file_id: fichier.getId()
      }, '', 'ERREUR');
      return {ok: false, reason: 'INVALID_PATH'};
    }
    
    // Parse chemin (ex: "HOLDING / 03_CLIENTS / ...")
    const parts = String(cheminFinal).split('/').map(function(p) {
      return p.trim();
    }).filter(function(p) {
      return p.length > 0;
    });
    
    if (parts.length === 0) {
      return {ok: false, reason: 'EMPTY_PATH'};
    }
    
    // Trouver/créer dossiers
    let currentFolder = DriveApp.getRootFolder();
    
    for (let i = 0; i < parts.length; i++) {
      const folderName = parts[i];
      const it = currentFolder.getFoldersByName(folderName);
      
      if (it.hasNext()) {
        currentFolder = it.next();
      } else {
        currentFolder = currentFolder.createFolder(folderName);
      }
    }
    
    // Déplacer fichier
    const parents = fichier.getParents();
    while (parents.hasNext()) {
      const parent = parents.next();
      parent.removeFile(fichier);
    }
    
    currentFolder.addFile(fichier);
    
    logAction('POSTVAL', 'MOVE_SUCCESS', {
      file_id: fichier.getId(),
      chemin_final: cheminFinal,
      folder_id: currentFolder.getId()
    }, '', 'INFO');
    
    return {ok: true, folder_id: currentFolder.getId()};
    
  } catch (e) {
    logAction('POSTVAL', 'MOVE_ERROR', {
      file_id: fichier.getId(),
      err: String(e)
    }, '', 'ERREUR');
    return {ok: false, reason: String(e)};
  }
}

// ============================================================
// POST-VALIDATION — ÉCRITURE CRM (DÉLÉGATION)
// ============================================================

function BM_POSTVAL_writeCRM(donnees, validationRequired) {
  try {
    if (validationRequired !== true) {
      logAction('POSTVAL', 'CRM_BLOCKED', {
        reason: 'POST_VALIDATION_ONLY',
        details: 'Écriture CRM requis validation humaine explicite'
      }, '', 'INFO');
      return {ok: false, reason: 'POST_VALIDATION_ONLY'};
    }
    
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
    
    logAction('POSTVAL', 'CRM_WRITE_SUCCESS', {
      type: donnees.type || ''
    }, '', 'INFO');
    
    return {ok: true};
    
  } catch (e) {
    logAction('POSTVAL', 'CRM_WRITE_ERROR', {err: String(e)}, '', 'ERREUR');
    return {ok: false, reason: String(e)};
  }
}

// ============================================================
// FIN 07_POST_VALIDATION.gs
// ============================================================
