/**
 * 01_SCAN_ROUTING_GUARD.gs
 * BOX MAGIC OCR — Routing intelligent + Guards
 * 
 * Responsabilité : Décider si un fichier doit être traité
 * 
 * @version 2.0.0
 * @date 2026-02-14
 */

// ============================================================
// ROUTING — VÉRIFICATION SI FICHIER DOIT ÊTRE TRAITÉ
// ============================================================

function BM_ROUTING_shouldProcess(fichier) {
  try {
    const fileId = fichier.getId();
    const fileName = fichier.getName();
    const mimeType = fichier.getMimeType();
    
    // 1. Vérifier format valide
    const validFormats = [
      'application/pdf',
      'image/jpeg',
      'image/jpg',
      'image/png'
    ];
    
    if (validFormats.indexOf(mimeType) === -1) {
      return {
        should_process: false,
        reason: 'FORMAT_INVALID',
        details: 'Format non supporté: ' + mimeType
      };
    }
    
    // 2. Vérifier taille > 0
    const size = fichier.getSize();
    if (size === 0) {
      return {
        should_process: false,
        reason: 'FILE_EMPTY',
        details: 'Fichier vide (0 bytes)'
      };
    }
    
    // 3. Vérifier si déjà traité dans INDEX_GLOBAL
    const alreadyProcessed = BM_ROUTING_isAlreadyInIndex(fileId);
    if (alreadyProcessed) {
      return {
        should_process: false,
        reason: 'ALREADY_PROCESSED',
        details: 'Fichier déjà dans INDEX_GLOBAL'
      };
    }
    
    // 4. Vérifier doublon par hash
    const duplicate = BM_ROUTING_detectDuplicate(fichier);
    if (duplicate.is_duplicate) {
      return {
        should_process: false,
        reason: 'DUPLICATE_HASH',
        details: 'Doublon détecté: ' + duplicate.existing_id
      };
    }
    
    return {
      should_process: true,
      reason: 'OK',
      details: 'Fichier prêt à être traité'
    };
    
  } catch (e) {
    logAction('ROUTING', 'ERROR', {err: String(e)}, '', 'ERREUR');
    return {
      should_process: false,
      reason: 'ERROR',
      details: String(e)
    };
  }
}

// ============================================================
// ROUTING — VÉRIFICATION INDEX_GLOBAL
// ============================================================

function BM_ROUTING_isAlreadyInIndex(fileId) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName('INDEX_GLOBAL');
    if (!sh) return false;
    
    const lastRow = sh.getLastRow();
    if (lastRow < 2) return false;
    
    // Chercher colonne Fichier_ID
    const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
    let colIndex = -1;
    for (let i = 0; i < headers.length; i++) {
      if (String(headers[i]).trim() === 'Fichier_ID') {
        colIndex = i + 1;
        break;
      }
    }
    
    if (colIndex === -1) return false;
    
    // Chercher fileId dans la colonne
    const values = sh.getRange(2, colIndex, lastRow - 1, 1).getValues();
    for (let i = 0; i < values.length; i++) {
      if (String(values[i][0]).trim() === fileId) {
        return true;
      }
    }
    
    return false;
    
  } catch (e) {
    logAction('ROUTING', 'INDEX_CHECK_ERROR', {err: String(e)}, '', 'WARN');
    return false;
  }
}

// ============================================================
// ROUTING — DÉTECTION DOUBLON PAR HASH
// ============================================================

function BM_ROUTING_detectDuplicate(fichier) {
  try {
    const fileId = fichier.getId();
    
    // Calculer hash MD5
    const blob = fichier.getBlob();
    const bytes = blob.getBytes();
    const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, bytes);
    const hash = digest.map(function(byte) {
      const v = (byte < 0) ? byte + 256 : byte;
      return (v < 16 ? '0' : '') + v.toString(16);
    }).join('');
    
    // Chercher hash dans INDEX_GLOBAL
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName('INDEX_GLOBAL');
    if (!sh) {
      return {is_duplicate: false, existing_id: '', hash: hash};
    }
    
    const lastRow = sh.getLastRow();
    if (lastRow < 2) {
      return {is_duplicate: false, existing_id: '', hash: hash};
    }
    
    // Chercher colonne Hash_MD5
    const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
    let hashColIndex = -1;
    let idColIndex = -1;
    
    for (let i = 0; i < headers.length; i++) {
      const h = String(headers[i]).trim();
      if (h === 'Hash_MD5') hashColIndex = i + 1;
      if (h === 'Fichier_ID') idColIndex = i + 1;
    }
    
    if (hashColIndex === -1) {
      return {is_duplicate: false, existing_id: '', hash: hash};
    }
    
    // Chercher hash dans la colonne
    const hashValues = sh.getRange(2, hashColIndex, lastRow - 1, 1).getValues();
    const idValues = (idColIndex !== -1) ? sh.getRange(2, idColIndex, lastRow - 1, 1).getValues() : [];
    
    for (let i = 0; i < hashValues.length; i++) {
      const existingHash = String(hashValues[i][0]).trim();
      if (existingHash === hash) {
        const existingId = (idValues.length > i) ? String(idValues[i][0]).trim() : '';
        // Ne pas considérer comme doublon si c'est le même fichier
        if (existingId !== fileId) {
          return {
            is_duplicate: true,
            existing_id: existingId,
            hash: hash
          };
        }
      }
    }
    
    return {is_duplicate: false, existing_id: '', hash: hash};
    
  } catch (e) {
    logAction('ROUTING', 'DUPLICATE_CHECK_ERROR', {err: String(e)}, '', 'WARN');
    return {is_duplicate: false, existing_id: '', hash: ''};
  }
}

// ============================================================
// ROUTING — SÉLECTION NIVEAU OCR AUTOMATIQUE
// ============================================================

function BM_ROUTING_selectLevel(fichier) {
  try {
    const mimeType = fichier.getMimeType();
    const fileName = fichier.getName();
    
    // Si image → Level 2 (Cloud Run obligatoire)
    if (mimeType.indexOf('image/') === 0) {
      return {
        level: 2,
        reason: 'IMAGE_REQUIRES_CLOUDRUN',
        details: 'Image scannée détectée'
      };
    }
    
    // Si PDF → tenter Level 1 (texte natif)
    if (mimeType === 'application/pdf') {
      try {
        const blob = fichier.getBlob();
        const text = blob.getDataAsString();
        
        // Si texte natif valide (>100 chars)
        if (text && text.length > 100) {
          return {
            level: 1,
            reason: 'PDF_NATIVE_TEXT',
            details: 'Texte natif détecté (' + text.length + ' chars)'
          };
        }
      } catch (e) {
        // Échec extraction texte natif → Level 2
      }
      
      return {
        level: 2,
        reason: 'PDF_SCAN_OR_NO_TEXT',
        details: 'PDF scan ou texte non extractible'
      };
    }
    
    // Par défaut → Level 2
    return {
      level: 2,
      reason: 'DEFAULT_CLOUDRUN',
      details: 'Niveau par défaut'
    };
    
  } catch (e) {
    logAction('ROUTING', 'SELECT_LEVEL_ERROR', {err: String(e)}, '', 'WARN');
    return {
      level: 2,
      reason: 'ERROR_FALLBACK',
      details: String(e)
    };
  }
}

// ============================================================
// FIN 01_SCAN_ROUTING_GUARD.gs
// ============================================================
