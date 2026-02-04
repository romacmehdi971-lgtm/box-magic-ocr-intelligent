/**
 * OCR__CLOUDRUN_INTEGRATION11_V2.gs
 * Cloud Run = source de vérité OCR
 *
 * ✅ V2 : TICKET CB ENRICHMENT
 * ✅ Mapping enrichi pour TICKET : mode_paiement, statut_paiement, carte_last4, montant_encaisse, date_encaissement
 * ✅ Correction spéciale TICKET : si "client" contient un SIREN/SIRET, on le bascule en fournisseur_siret
 * ✅ NE PAS ÉCRASER les champs existants
 */

function pipelineOCR(fileId) {
  logAction("OCR", "pipelineOCR_debut", { file_id: String(fileId || "") }, "", "INFO");

  const engine = String(BM_CFG.get("OCR_ENGINE") || "").trim().toUpperCase();
  const force = String(BM_CFG.get("OCR_FORCE_CLOUDRUN_TEST") || "").trim().toUpperCase() === "OUI";
  const url = String(BM_CFG.get("OCR_CLOUDRUN_URL") || "").trim() || "https://box-magic-ocr-intelligent-522732657254.us-central1.run.app/ocr";

  if (engine !== "CLOUDRUN" && !force) {
    logAction("OCR", "OCR_ENGINE_NOT_CLOUDRUN", { engine: engine, force: force }, "", "INFO");
    return { engine: "LEGACY", confiance: 0, texte: "", fields: {} };
  }

  const fileBytes = _BM_getFileBytes_(fileId);
  if (!fileBytes) {
    logAction("OCR", "OCR_CLOUDRUN_GETFILE_FAIL", { file_id: String(fileId), err: "no_bytes" }, "", "ERREUR");
    return { engine: "CLOUDRUN_STRICT", confiance: 0, texte: "", fields: {} };
  }

  const filename = String(_BM_safeFileNameFromDrive_(fileId) || "document.pdf");
  const sourceEntreprise = String(BM_CFG.get("SOURCE_ENTREPRISE") || "auto-detect");

  logAction("OCR", "OCR_CLOUDRUN_TRY", {
    url: url,
    file_id: String(fileId),
    filename: filename,
    source_entreprise: sourceEntreprise
  }, "", "INFO");

  try {
    const boundary = "----BMFormBoundary" + Utilities.getUuid().replace(/-/g, "");
    const crlf = "\r\n";

    const head =
      "--" + boundary + crlf +
      'Content-Disposition: form-data; name="file"; filename="' + filename + '"' + crlf +
      "Content-Type: application/pdf" + crlf + crlf;

    const tail =
      crlf + "--" + boundary + crlf +
      'Content-Disposition: form-data; name="source_entreprise"' + crlf + crlf +
      sourceEntreprise + crlf +
      "--" + boundary + "--" + crlf;

    const payloadBytes = Utilities.newBlob(head).getBytes()
      .concat(fileBytes)
      .concat(Utilities.newBlob(tail).getBytes());

    const resp = UrlFetchApp.fetch(url, {
      method: "post",
      contentType: "multipart/form-data; boundary=" + boundary,
      payload: payloadBytes,
      muteHttpExceptions: true,
      followRedirects: true
    });

    const status = resp.getResponseCode();
    const rawTxt = resp.getContentText() || "";

    logAction("OCR", "OCR_CLOUDRUN_RAW_RESPONSE", {
      file_id: String(fileId),
      status: status,
      raw_sample: rawTxt.substring(0, 1200)
    }, "", "INFO");

    if (status < 200 || status >= 300) {
      logAction("OCR", "OCR_CLOUDRUN_HTTP_FAIL", { status: status, raw: rawTxt.substring(0, 800) }, "", "ERREUR");
      return { engine: "CLOUDRUN_STRICT", confiance: 0, texte: "", fields: {} };
    }

    const json = JSON.parse(rawTxt || "{}");

    const fieldsRaw = (json && json.fields && typeof json.fields === "object") ? json.fields : {};
    const fields = _BM_normalizeFieldValues_(fieldsRaw);

    const out = {
      engine: "CLOUDRUN",
      confiance: Number(json.confidence || 0) || 0,
      texte: String(json.text || ""),
      fields: fields,
      raw: json,
      rule_created: json.rule_created || null,
      level: Number(json.level || 0) || 0,
      document_type: String(json.document_type || ""),
      entreprise_source: String(json.entreprise_source || "")
    };

    // ✅ Mapping direct
    out.mapped = _BM_mapCloudRunToPipeline_(out);

    // ✅ Compat OCR2 : on injecte mapped dans fields (sans écraser ce qui existe déjà)
    out.fields = _BM_mergeMappedIntoFields_(out.fields, out.mapped);

    logAction("OCR", "OCR_CLOUDRUN_OK", {
      file_id: String(fileId),
      confidence: out.confiance,
      fields_keys: Object.keys(out.fields || {}).join(","),
      mapped_keys: Object.keys(out.mapped || {}).join(","),
      level: out.level,
      doc_type: out.document_type
    }, "", "INFO");

    return out;

  } catch (e) {
    logAction("OCR", "OCR_CLOUDRUN_EXCEPTION", { file_id: String(fileId), err: String(e) }, "", "ERREUR");
    return { engine: "CLOUDRUN_STRICT", confiance: 0, texte: "", fields: {} };
  }
}

function _BM_normalizeFieldValues_(fieldsRaw) {
  const out = {};
  Object.keys(fieldsRaw || {}).forEach(k => {
    const v = fieldsRaw[k];
    if (v && typeof v === "object" && "value" in v) out[k] = v.value;
    else out[k] = v;
  });
  return out;
}

/**
 * ✅ Mapping vers les clés attendues par OCR2 (type/societe/numero/date/ht/tva/ttc/taux…)
 * + correction tickets : client contient souvent un Siren -> on le bascule en fournisseur_siret
 * 🎯 V2 : TICKET CB enrichment fields
 */
function _BM_mapCloudRunToPipeline_(base) {
  const f = base.fields || {};
  const docType = String(base.document_type || "").trim();
  const entrepriseSource = String(base.entreprise_source || "").trim();

  let client = String(f.client || f.client_nom || "").trim();
  let fournisseurSiret = String(f.fournisseur_siret || f.siret || f.siren || "").trim();

  // ✅ Cas TICKET : si "client" ressemble à un Siren/Siret, ce n'est pas un client → c'est le fournisseur
  if (!fournisseurSiret && _BM_looksLikeSirenOrSiret_(client)) {
    fournisseurSiret = _BM_extractDigits_(client);
    client = entrepriseSource || "";
  }

  const mapped = {
    type: docType || "",
    document_type: docType || "",

    // fournisseur / societe (si CloudRun le donne)
    societe: String(f.fournisseur || f.societe || f.enseigne || f.magasin || "").trim(),
    fournisseur: String(f.fournisseur || f.societe || f.enseigne || f.magasin || "").trim(),

    entreprise_source: entrepriseSource,

    // client corrigé
    client: client,

    // identifiant fournisseur
    fournisseur_siret: fournisseurSiret,

    // facture / date
    numero_facture: String(f.numero_facture || f.numero_doc || f.numero_ticket || "").trim(),
    date_doc: String(f.date_doc || f.date_facture || f.date || "").trim(),
    date_prestation: String(f.date_prestation || "").trim(),

    // montants
    ht: _BM_pickAmount_(f, ["total_ht", "montant_ht", "ht", "subtotal", "net_amount"]),
    tva_montant: _BM_pickAmount_(f, ["tva_montant", "montant_tva", "vat_amount"]),
    ttc: _BM_pickAmount_(f, ["total_ttc", "montant_ttc", "ttc", "total", "gross_amount"]),

    tva_taux: String(f.tva_taux || f.tva_rate || f.vat_rate || "").trim(),
    
    // 🎯 TICKET CB ENRICHMENT
    mode_paiement: String(f.mode_paiement || f.payment_method || "").trim(),
    statut_paiement: String(f.statut_paiement || f.payment_status || "").trim(),
    carte_last4: String(f.carte_last4 || f.card_last4 || "").trim(),
    montant_encaisse: _BM_pickAmount_(f, ["montant_encaisse", "montant_encaissement", "amount_paid"]),
    date_encaissement: String(f.date_encaissement || f.payment_date || "").trim(),
    
    ticket_cb_detecte: Boolean(f.ticket_cb_detecte || f.cb || f.carte_bancaire || (f.mode_paiement === "CB") || false),

    ia_signature: String((base.raw && base.raw.document_id) || "")
  };

  // 🎯 LOGIQUE TICKET CB : si mode_paiement=CB et pas de date_encaissement → utiliser date_doc
  if (docType === "TICKET" && mapped.mode_paiement === "CB" && !mapped.date_encaissement && mapped.date_doc) {
    mapped.date_encaissement = mapped.date_doc;
  }

  // 🎯 LOGIQUE TICKET CB : si statut_paiement=PAYE et pas de montant_encaisse → utiliser ttc
  if (docType === "TICKET" && mapped.statut_paiement === "PAYE" && !mapped.montant_encaisse && mapped.ttc) {
    mapped.montant_encaisse = mapped.ttc;
  }

  // fallback : si fournisseur vide mais on a un siret → on garde la trace
  if (!mapped.fournisseur && mapped.fournisseur_siret) {
    mapped.fournisseur = "";
    mapped.societe = "";
  }

  return mapped;
}

/**
 * ✅ Pour compat OCR2 : injecte mapped dans fields (ex: ttc, ht, date_doc, numero_facture…)
 */
function _BM_mergeMappedIntoFields_(fields, mapped) {
  const out = fields || {};
  const m = mapped || {};
  Object.keys(m).forEach(k => {
    if (!(k in out) || out[k] === "" || out[k] == null) out[k] = m[k];
  });

  // alias attendus OCR2 (si ton OCR2 cherche "ttc" / "ht" etc)
  if (!("ttc" in out) && "ttc" in m) out.ttc = m.ttc;
  if (!("ht" in out) && "ht" in m) out.ht = m.ht;
  if (!("tva_montant" in out) && "tva_montant" in m) out.tva_montant = m.tva_montant;
  if (!("tva_taux" in out) && "tva_taux" in m) out.tva_taux = m.tva_taux;
  
  // 🎯 TICKET CB aliases
  if (!("mode_paiement" in out) && "mode_paiement" in m) out.mode_paiement = m.mode_paiement;
  if (!("statut_paiement" in out) && "statut_paiement" in m) out.statut_paiement = m.statut_paiement;
  if (!("carte_last4" in out) && "carte_last4" in m) out.carte_last4 = m.carte_last4;
  if (!("montant_encaisse" in out) && "montant_encaisse" in m) out.montant_encaisse = m.montant_encaisse;
  if (!("date_encaissement" in out) && "date_encaissement" in m) out.date_encaissement = m.date_encaissement;

  return out;
}

function _BM_pickAmount_(f, keys) {
  for (var i = 0; i < (keys || []).length; i++) {
    var k = keys[i];
    if (k in f && f[k] !== "" && f[k] != null) return f[k];
  }
  return "";
}

function _BM_looksLikeSirenOrSiret_(s) {
  const digits = _BM_extractDigits_(s);
  // SIREN = 9 digits, SIRET = 14 digits
  return digits.length === 9 || digits.length === 14;
}

function _BM_extractDigits_(s) {
  return String(s || "").replace(/\D/g, "");
}

function _BM_getFileBytes_(fileId) {
  try {
    const f = DriveApp.getFileById(String(fileId));
    return f.getBlob().getBytes();
  } catch (e) {
    return null;
  }
}

function _BM_safeFileNameFromDrive_(fileId) {
  try {
    return DriveApp.getFileById(String(fileId)).getName();
  } catch (e) {
    return "document.pdf";
  }
}
