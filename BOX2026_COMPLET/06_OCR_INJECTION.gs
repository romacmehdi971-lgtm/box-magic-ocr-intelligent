/**
 * 06_OCR_INJECTION.gs
 * BOX MAGIC OCR — Injection INDEX_FACTURES
 * 
 * Responsabilité : Écriture payload validé dans INDEX_GLOBAL
 * 
 * @version 2.0.0
 * @date 2026-02-14
 */

// ============================================================
// INJECTION — ÉCRITURE INDEX_GLOBAL
// ============================================================

function BM_INJECTION_writeToIndex(fichier, donnees, proposition) {
  try {
    const fileId = fichier.getId();
    
    logAction('INJECTION', 'WRITE_START', {file_id: fileId}, '', 'INFO');
    
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName('INDEX_GLOBAL');
    
    if (!sh) {
      logAction('INJECTION', 'SHEET_NOT_FOUND', {expected: 'INDEX_GLOBAL'}, '', 'ERREUR');
      return {ok: false, error: 'INDEX_GLOBAL sheet not found'};
    }
    
    // Lire headers
    const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
    const headerIndex = {};
    headers.forEach(function(h, i) {
      headerIndex[String(h || '').trim()] = i;
    });
    
    logAction('INJECTION', 'HEADERS_READ', {
      file_id: fileId,
      headers_count: headers.length
    }, '', 'INFO');
    
    // Construire ligne
    const row = BM_INJECTION_buildRow(fichier, donnees, proposition, headers, headerIndex);
    
    // Append row
    sh.appendRow(row);
    
    logAction('INJECTION', 'WRITE_SUCCESS', {
      file_id: fileId,
      row_length: row.length
    }, '', 'INFO');
    
    return {ok: true};
    
  } catch (e) {
    logAction('INJECTION', 'WRITE_ERROR', {
      file_id: fichier.getId(),
      err: String(e)
    }, '', 'ERREUR');
    return {ok: false, error: String(e)};
  }
}

// ============================================================
// INJECTION — CONSTRUCTION LIGNE INDEX
// ============================================================

function BM_INJECTION_buildRow(fichier, donnees, proposition, headers, headerIndex) {
  const row = new Array(headers.length).fill('');
  
  // Helper : set colonne si existe
  function set(col, val) {
    if (headerIndex[col] !== undefined) {
      row[headerIndex[col]] = (val !== null && val !== undefined) ? val : '';
    }
  }
  
  // Champs système
  set('Timestamp', new Date());
  set('Fichier_ID', fichier.getId());
  set('Nom_Original', fichier.getName());
  set('Nom_Final', donnees.nom_final || '');
  set('Chemin_Final', donnees.chemin_final || '');
  
  // Hash MD5 (si disponible)
  try {
    const blob = fichier.getBlob();
    const bytes = blob.getBytes();
    const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, bytes);
    const hash = digest.map(function(byte) {
      const v = (byte < 0) ? byte + 256 : byte;
      return (v < 16 ? '0' : '') + v.toString(16);
    }).join('');
    set('Hash_MD5', hash);
  } catch (e) {
    // Ignorer erreur hash
  }
  
  // Champs document
  set('Type_Document', donnees.type || donnees.document_type || '');
  set('Numero_Facture', donnees.numero_facture || '');
  set('Date_Document', donnees.date_document || '');
  set('Date_Prestation', donnees.date_prestation || '');
  
  // Société / Client
  set('Societe', donnees.societe || '');
  set('Entreprise_Source', donnees.entreprise_source || '');
  set('Client', donnees.client || '');
  set('Client_Nom', donnees.client_nom || '');
  set('Client_Adresse', donnees.client_adresse || '');
  set('Client_Code_Postal', donnees.client_code_postal || '');
  set('Client_Ville', donnees.client_ville || '');
  
  // SIRET
  set('Fournisseur_SIRET', donnees.fournisseur_siret || '');
  set('Client_SIRET', donnees.client_siret || '');
  
  // Montants
  const montants = donnees.montants || {};
  set('Montant_HT', montants.ht || '');
  set('TVA_Montant', montants.tva || '');
  set('Montant_TTC', montants.ttc || '');
  set('TVA_Taux', donnees.tva_taux || '');
  
  // Prestation
  set('Lieu_Livraison', donnees.lieu_livraison || '');
  set('Nb_Personnes', donnees.nb_personnes || '');
  set('Prestation_Type', donnees.prestation_type || '');
  set('Prestation_Detail', donnees.prestation_detail || '');
  set('Prestation_Inclus', donnees.prestation_inclus || '');
  
  // Paiement
  set('Mode_Paiement', donnees.mode_paiement || '');
  set('Statut_Paiement', donnees.statut_paiement || '');
  set('Montant_Encaisse', donnees.montant_encaisse || '');
  
  // OCR
  set('OCR_Engine', donnees.ocr_engine || '');
  set('OCR_Level', donnees.level || '');
  set('Confiance', donnees.confiance || 0);
  
  // Classement
  set('Chemin_Propose', (proposition && proposition.chemin) ? proposition.chemin : '');
  set('Classement_Auto', (proposition && proposition.auto) ? true : false);
  set('Annee', (proposition && proposition.annee) ? proposition.annee : '');
  
  // Status
  set('Status', donnees.status || 'SCAN');
  set('Date_Validation', donnees.date_validation || '');
  
  return row;
}

// ============================================================
// INJECTION — LOG DÉTAILLÉ
// ============================================================

function BM_INJECTION_logInjection(fichier, donnees) {
  try {
    const fileId = fichier.getId();
    
    // Log JSONL (1 ligne key=value;...)
    const kv = function(k, v) {
      const s = (v === null || v === undefined) ? '' : String(v);
      return k + '=' + s.replace(/\s+/g, ' ').replace(/;/g, ',').trim();
    };
    
    const montants = donnees.montants || {};
    const ttc = (montants.ttc !== undefined && montants.ttc !== null && String(montants.ttc).trim() !== '') ? montants.ttc : '';
    const ht = (montants.ht !== undefined && montants.ht !== null && String(montants.ht).trim() !== '') ? montants.ht : '';
    const tva = (montants.tva !== undefined && montants.tva !== null && String(montants.tva).trim() !== '') ? montants.tva : '';
    
    const line = [
      kv('type', donnees.type || donnees.document_type || ''),
      kv('document_type', donnees.document_type || ''),
      kv('societe', donnees.societe || ''),
      kv('client', donnees.client || ''),
      kv('fournisseur_siret', donnees.fournisseur_siret || ''),
      kv('date_doc', donnees.date_document || donnees.date_doc || ''),
      kv('numero_facture', donnees.numero_facture || ''),
      kv('ttc', ttc),
      kv('ht', ht),
      kv('tva_montant', tva),
      kv('tva_taux', donnees.tva_taux || ''),
      kv('mode_paiement', donnees.mode_paiement || ''),
      kv('confidence', donnees.confiance || donnees.confidence || ''),
      kv('level', donnees.level || '')
    ].join(';');
    
    logAction('INJECTION', 'PAYLOAD_JSONL', {
      file_id: fileId,
      payload: line
    }, '', 'INFO');
    
  } catch (e) {
    // Ignorer erreur log
  }
}

// ============================================================
// FIN 06_OCR_INJECTION.gs
// ============================================================
