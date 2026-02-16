/**
 * Pick the longest non-empty text among candidates (strings).
 * Used to avoid losing OCR content when multiple fields exist.
 */
function _BM_pickLongestText_(candidates) {
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

/** Extract invoice/document number from OCR text (best-effort, deterministic). */
function _BM_extractInvoiceNumber_(txt) {
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

/** Parse a French amount string to a normalized decimal string with dot (e.g. '593,72' -> '593.72'). */
function _BM_parseAmountFR_(s) {
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

/** Extract HT/TVA/TTC and TVA taux from OCR text (best-effort). Returns {ht,tva_montant,ttc,tva_taux}. */
function _BM_extractAmounts_(txt) {
  var out = { ht: '', tva_montant: '', ttc: '', tva_taux: '' };
  try {
    if (!txt) return out;
    txt = String(txt);
    // Rate (e.g. 8.5%, 20%)
    var mRate = txt.match(/\b(\d{1,2}(?:[\.,]\d{1,2})?)\s*%\b/);
    if (mRate && mRate[1]) out.tva_taux = _BM_parseAmountFR_(mRate[1]);

    // TTC
    var mTTC = txt.match(/\b(?:TOTAL\s*TTC|MONTANT\s*TTC|NET\s*A\s*PAYER|A\s*PAYER)\b[^0-9]{0,20}([0-9][0-9 \.,]{1,15})\s*(?:€|EUR)?/i);
    if (mTTC && mTTC[1]) out.ttc = _BM_parseAmountFR_(mTTC[1]);

    // HT
    var mHT = txt.match(/\b(?:TOTAL\s*HT|MONTANT\s*HT)\b[^0-9]{0,20}([0-9][0-9 \.,]{1,15})\s*(?:€|EUR)?/i);
    if (mHT && mHT[1]) out.ht = _BM_parseAmountFR_(mHT[1]);

    // TVA amount
    var mTVA = txt.match(/\b(?:TVA\s*(?:MONTANT)?|MONTANT\s*TVA)\b[^0-9]{0,20}([0-9][0-9 \.,]{1,15})\s*(?:€|EUR)?/i);
    if (mTVA && mTVA[1]) out.tva_montant = _BM_parseAmountFR_(mTVA[1]);

    return out;
  } catch (e) {
    return out;
  }
}

/**
 * 02_SCAN_WORKER.gs
 * Canon — WORKER SCAN (P14)
 * Migré depuis Classementlegacy.gs — ne pas éditer sans gouvernance.
 */

function traiterNouveauDocument(fichier) {
  try {
    const fileId = fichier.getId();
    const nom = fichier.getName();

    logAction('CLASSEMENT', 'traiterNouveauDocument_debut', { file_id: fileId, nom: nom }, '', 'INFO');

    // Normalisation (SAFE)
    let normalize = null;
    try {
      if (typeof BM_PIPELINE_normalizeForOcr_ === "function") {
        normalize = BM_PIPELINE_normalizeForOcr_(fileId, nom);
      }
    } catch (eNorm) {
      logAction('PIPELINE', 'PIPELINE_NORMALIZE_WARN', { file_id: fileId, err: String(eNorm) }, '', 'WARN');
      normalize = null;
    }

    const ocrFileId = (normalize && normalize.fileIdForOcr) ? String(normalize.fileIdForOcr) : fileId;

    // OCR Cloud Run
    const ocr = pipelineOCR(ocrFileId);

    // IMPORTANT: ocrText / ocrEngine doivent exister AVANT OCR1_ENRICH
      let ocrText = String((ocr && ocr.texte) ? ocr.texte : "");
      // ✅ Anti-troncature: on prend toujours la meilleure source (longueur max) parmi les candidats CloudRun
      const _cand1 = ocrText;
      const _cand2 = (ocr && ocr.fields && ocr.fields.texte_ocr_brut) ? String(ocr.fields.texte_ocr_brut) : "";
      const _cand3 = (ocr && ocr.raw && ocr.raw.ocr_text_raw) ? String(ocr.raw.ocr_text_raw) : "";
      const _best = _BM_pickLongestText_([_cand1, _cand2, _cand3]);
      if (_best !== ocrText) ocrText = _best;
      ocrText = _BM_sanitizeOcrText_(ocrText);
      logAction("OCR", "OCR_TEXT_PICK", {
        file_id: String(fileId),
        len_texte: _cand1.length,
        len_fields_texte_ocr_brut: _cand2.length,
        len_raw_ocr_text_raw: _cand3.length,
        len_used: ocrText.length
      }, ".", "INFO");
      const ocrEngine = String((ocr && ocr.engine) ? ocr.engine : "").trim().toUpperCase();

     // IMPORTANT: donnees doit exister AVANT OCR1_ENRICH (sinon ReferenceError)
// ✅ Priorité Cloud Run : on pré-remplit donnees avec le mapping Cloud Run (fill-base)
let donnees = {};
try {
  if (ocr && ocr.mapped && typeof ocr.mapped === "object") {
    donnees = Object.assign({}, ocr.mapped);
  }
} catch (_) {}
// Extraction legacy (optionnel) — ne doit PAS écraser les champs déjà posés par OCR1/OCR2
try {
  if (typeof extraireStructure === "function") {
    const legacy = extraireStructure(ocrText, fileId) || {};
    if (legacy && typeof legacy === "object") {
      // Merge non destructif
      donnees = Object.assign({}, legacy, donnees);
      if (legacy.montants && typeof legacy.montants === "object") {
        donnees.montants = Object.assign({}, legacy.montants, (donnees.montants || {}));
      }
    }
  }
} catch (eExtract) {
  logAction('OCR', 'OCR_LEGACY_EXTRACTION_FAIL', { file_id: fileId, err: String(eExtract) }, '', 'WARN');
}

    // =========================
    // OCR1 — RECONNAISSANCE MÉTIER (ENRICHI) — TENTATIVE SÛRE
    // =========================
    const __ocr1_t0 = Date.now();
    try {
      const f = (ocr && ocr.fields && typeof ocr.fields === "object") ? ocr.fields : {};
      const level = (ocr && (ocr.level !== undefined && ocr.level !== null)) ? ocr.level : null;

      logAction("OCR1", "OCR1_ENRICH_START", {
        file_id: fileId,
        nom: String(fichier.getName ? fichier.getName() : ""),
        engine: String((ocr && ocr.engine) ? ocr.engine : "UNKNOWN"),
        level: level,
        has_text: Boolean(ocrText && ocrText.length),
        text_len: (ocrText && ocrText.length) ? ocrText.length : 0
      }, "", "INFO");

      const enrich = OCR1_ENRICH_extractCandidates_(ocrText, f, fichier);
      const signals = enrich.signals || {};
      const candidates = enrich.candidates || {};
      const deferKeys = enrich.deferKeys || [];

// JSONL — OCR1 candidates (1 ligne) + taille + hash
try {
  const __cStr = JSON.stringify(candidates || {});
  let __cMd5 = "";
  try {
    const __d = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, __cStr || "", Utilities.Charset.UTF_8);
    __cMd5 = __d.map(b => { const x = ((b < 0 ? b + 256 : b).toString(16)); return x.length === 1 ? "0" + x : x; }).join("");
  } catch (_) {}
  logAction("OCR1", "OCR1_CANDIDATES_JSONL", {
    file_id: fileId,
    len: (__cStr && __cStr.length) ? __cStr.length : 0,
    md5: __cMd5,
    jsonl: String(__cStr || "").substring(0, 800)
  }, "", "INFO");
} catch (_) {}

      logAction("OCR1", "OCR1_ENRICH_SIGNALS_FOUND", {
        file_id: fileId,
        type_guess: String(signals.type_guess || ""),
        client_guess: String(signals.client_guess || ""),
        societe_guess: String(signals.societe_guess || ""),
        numero_doc_guess: String(signals.numero_doc_guess || ""),
        patterns_found: String(signals.patterns_found || "")
      }, "", "INFO");

      logAction("OCR1", "OCR1_ENRICH_FIELDS_CANDIDATES", {
        file_id: fileId,
        candidates_json: JSON.stringify(candidates)
      }, "", "INFO");

      if (deferKeys.length) {
        logAction("OCR1", "OCR1_ENRICH_DEFER_TO_OCR2", {
          file_id: fileId,
          keys: deferKeys.join(",")
        }, "", "INFO");
      }

      // Remplissage STRICTEMENT sûr : uniquement si (score>=0.8) + format OK + valeur unique
      const filled = [];

      const applyIfSafe = (key, targetPath) => {
        const c = candidates[key];
        if (!c || c.value === undefined || c.value === null) return;
        const score = Number(c.score || 0);
        if (score < 0.8) return;

        const val = c.value;

        // Appliquer uniquement si champ vide côté donnees (non destructif)
        if (targetPath === "donnees.type") {
          if (!donnees.type) { donnees.type = String(val); filled.push("type_doc"); }
          return;
        }
        if (targetPath === "donnees.client") {
          if (!donnees.client) { donnees.client = String(val); filled.push("client"); }
          return;
        }
        if (targetPath === "donnees.societe") {
          if (!donnees.societe) { donnees.societe = String(val); filled.push("societe_emettrice"); }
          return;
        }
        if (targetPath === "donnees.numero_facture") {
          if (!donnees.numero_facture) { donnees.numero_facture = String(val); filled.push("numero_doc"); }
          return;
        }
        if (targetPath === "donnees.date_document") {
          if (!donnees.date_document) { donnees.date_document = String(val); filled.push("date_facture"); }
          return;
        }
        if (targetPath === "donnees.date_prestation") {
          if (!donnees.date_prestation) { donnees.date_prestation = String(val); filled.push("date_prestation"); }
          return;
        }
        if (targetPath === "donnees.lieu_livraison") {
          if (!donnees.lieu_livraison) { donnees.lieu_livraison = String(val); filled.push("lieu_prestation"); }
          return;
        }
        if (targetPath === "donnees.nb_personnes") {
          if (donnees.nb_personnes === undefined || donnees.nb_personnes === null || String(donnees.nb_personnes).trim() === "") {
            donnees.nb_personnes = val;
            filled.push("nb_personnes");
          }
          return;
        }
        if (targetPath === "donnees.tva_taux") {
          if (!donnees.tva_taux) { donnees.tva_taux = String(val); filled.push("tva_taux"); }
          return;
        }
        if (targetPath === "donnees.montants.ht") {
          if (!donnees.montants || typeof donnees.montants !== "object") donnees.montants = {};
          if (!donnees.montants.ht || Number(donnees.montants.ht) === 0) { donnees.montants.ht = val; filled.push("montant_ht"); }
          return;
        }
      };

      applyIfSafe("type_doc", "donnees.type");
      applyIfSafe("client", "donnees.client");
      applyIfSafe("societe_emettrice", "donnees.societe");
      applyIfSafe("numero_doc", "donnees.numero_facture");
      applyIfSafe("date_facture", "donnees.date_document");
      applyIfSafe("date_prestation", "donnees.date_prestation");
      applyIfSafe("lieu_prestation", "donnees.lieu_livraison");
      applyIfSafe("nb_personnes", "donnees.nb_personnes");
      applyIfSafe("tva_taux", "donnees.tva_taux");
      applyIfSafe("montant_ht", "donnees.montants.ht");

      logAction("OCR1", "OCR1_ENRICH_END", {
        file_id: fileId,
        duration_ms: Date.now() - __ocr1_t0,
        filled_keys: filled.join(",")
      }, "", "INFO");

    } catch (eOcr1Enrich) {
      logAction("OCR1", "OCR1_ENRICH_ERROR", { file_id: fileId, err: String(eOcr1Enrich) }, "", "ERREUR");
    }

// ocrText / ocrEngine déjà initialisés plus haut (OCR1_ENRICH) — éviter redeclare

    
     // OCR2 — EXTRACTION PROFONDE (LOGS + INJECTION SAFE)
    // =========================
    try {
      logAction("OCR2", "OCR2_START", { file_id: fileId }, "", "INFO");

      const f = (ocr && ocr.fields && typeof ocr.fields === "object") ? ocr.fields : null;
      // JSONL — OCR2 inject (1 ligne) + taille + hash
try {
  const __fStr = JSON.stringify(f || {});
  let __fMd5 = "";
  try {
    const __d = Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, __fStr || "", Utilities.Charset.UTF_8);
    __fMd5 = __d.map(b => { const x = ((b < 0 ? b + 256 : b).toString(16)); return x.length === 1 ? "0" + x : x; }).join("");
  } catch (_) {}
  logAction("OCR2", "OCR2_INJECT_JSONL", {
    file_id: fileId,
    len: (__fStr && __fStr.length) ? __fStr.length : 0,
    md5: __fMd5,
    jsonl: String(__fStr || "").substring(0, 800)
  }, "", "INFO");
} catch (_) {}

      if (f) {
        // Logs FOUND / MISSING (audit)
        try {
          const expectedKeys = [
            "type", "document_type",
            "societe", "entreprise_source",
            "client", "client_nom",
            "numero_facture",
            "date_doc", "date_prestation",
            "ht", "tva_montant", "ttc",
            "tva_taux", "tva_rate",
            "nb_personnes",
            "prestation_type", "prestation_detail", "prestation_inclus",
            "lieu_livraison"
          ];

          const found = Object.keys(f).filter(k => f[k] !== null && f[k] !== undefined && String(f[k]).trim() !== "");
          const missing = expectedKeys.filter(k => !(k in f) || f[k] === null || f[k] === undefined || String(f[k]).trim() === "");

          logAction("OCR2", "OCR2_FIELDS_FOUND", {
            file_id: fileId,
            found_count: found.length,
            missing_count: missing.length,
            found_keys: found.join(","),
            missing_keys: missing.join(",")
          }, "", "INFO");
        } catch (eAudit) {
          logAction("OCR2", "OCR2_AUDIT_WARN", { file_id: fileId, err: String(eAudit) }, "", "WARN");
        }

        // Injection SAFE dans donnees (sans casser legacy)
        if (!donnees.montants || typeof donnees.montants !== "object") donnees.montants = {};

        // Champs principaux (NORMALISATION + compat CloudRun)
        function __normDateSwapYMD__(s) {
          const v = String(s || "").trim();
          if (!v) return "";
          const m = v.match(/^(\d{4})[\/-](\d{2})[\/-](\d{2})$/);
          if (!m) return v;
          const Y = m[1], A = Number(m[2]), B = Number(m[3]);
          // si "mois" > 12 mais "jour" <= 12 => swap (ex: 2025-14-06 -> 2025-06-14)
          if (A > 12 && B >= 1 && B <= 12) return `${Y}-${String(B).padStart(2, "0")}-${String(A).padStart(2, "0")}`;
          return `${Y}-${String(A).padStart(2, "0")}-${String(B).padStart(2, "0")}`;
        }

        function __extractEmail__(s) {
          const v = String(s || "");
          const mm = v.match(/[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}/i);
          return mm ? String(mm[0]).trim() : "";
        }

        function __supplierNameFromEmail__(email) {
          const e = String(email || "").trim();
          if (!e) return "";
          const local = (e.split("@")[0] || "").trim();
          let name = local
            .replace(/[0-9]+/g, " ")
            .replace(/[._\-]+/g, " ")
            .replace(/\s+/g, " ")
            .trim()
            .toUpperCase();
          // mini-correction connue: "VER IN" -> "VERIN"
          name = name.replace(/\bVER\s+IN\b/g, "VERIN");
          return name.length >= 4 ? name : "";
        }

        function __isEmpty__(v) {
  return (v === null || v === undefined || String(v).trim() === "");
}
function __isUnknown__(v) {
  const s = String(v || "").trim().toUpperCase();
  return (s === "UNKNOWN" || s === "N/A" || s === "NA");
}
function __setIfMissing__(obj, key, val, opts) {
  const o = opts || {};
  if (!obj) return;
  if (!__isEmpty__(obj[key])) return;
  if (__isEmpty__(val)) return;
  if (o.rejectUnknown && __isUnknown__(val)) return;
  obj[key] = val;
}

__setIfMissing__(donnees, "type", String(f.type || f.document_type || ""), { rejectUnknown: false });
__setIfMissing__(donnees, "numero_facture", String(f.numero_facture || f.numero_doc || ""), { rejectUnknown: false });
__setIfMissing__(donnees, "societe", String(f.societe || f.societe_emettrice || f.entreprise_source || ""), { rejectUnknown: false });

// ✅ “Unknown” ne doit jamais polluer
__setIfMissing__(donnees, "client", String(f.client_nom || f.client || ""), { rejectUnknown: true });

        // Date : CloudRun renvoie souvent date_emission, parfois au format yyyy-dd-mm (ex: 2025-14-06)
        const __dateSrc = (f.date_doc || f.date_emission || f.date_document || f.date_facture || "");
        if (!donnees.date_document) {
          const __d = __normDateSwapYMD__(__dateSrc);
          if (__d) donnees.date_document = __d;
        }

        // VIDE > BRUIT : on ne force jamais 0 si non prouvé
        function __numOrEmpty__(v) {
          const s = String(v == null ? "" : v).trim();
          if (!s) return "";
          const norm = s.replace(/\s/g, "").replace(",", ".");
          const n = Number(norm);
          return (isFinite(n) ? n : "");
        }

        // Montants : CloudRun renvoie souvent total_ttc / montant_ht / montant_tva
        const __ttcRaw = (f.ttc != null && String(f.ttc).trim() !== "")
          ? f.ttc
          : ((f.total_ttc != null && String(f.total_ttc).trim() !== "") ? f.total_ttc : "");

        const __htRaw  = (f.ht != null && String(f.ht).trim() !== "")
          ? f.ht
          : ((f.montant_ht != null && String(f.montant_ht).trim() !== "") ? f.montant_ht : "");

        const __tvaRaw = (f.tva_montant != null && String(f.tva_montant).trim() !== "")
          ? f.tva_montant
          : ((f.montant_tva != null && String(f.montant_tva).trim() !== "") ? f.montant_tva : "");

        const __ttc = __numOrEmpty__(__ttcRaw);
        const __ht  = __numOrEmpty__(__htRaw);
        const __tva = __numOrEmpty__(__tvaRaw);

        if (__ht !== "")  donnees.montants.ht  = __ht;
        if (__tva !== "") donnees.montants.tva = __tva;
        if (__ttc !== "") donnees.montants.ttc = __ttc;

        // TVA taux (VIDE si non prouvé)
        const __taux = String(f.tva_taux || f.tva_rate || "").trim();
        if (__taux) donnees.tva_taux = __taux;

	        // ============================================================
	        // STABILISATION A — EXTRACTION DÉTERMINISTE (APPS SCRIPT)
	        // But : si Cloud Run ne renseigne pas (encore) numero_facture + HT/TVA/TTC,
	        //       on extrait à partir du texte OCR (anti-bruit, seulement si VIDE).
	        // ============================================================
	        if (ocrText) {
	          const __det = _BM_extractDeterministicInvoiceDataFromOcrText_(ocrText);
	          if (__det) {
	            if (!donnees.numero_facture && __det.numero_facture) {
	              donnees.numero_facture = __det.numero_facture;
	            }
	            if (!donnees.ht && __det.ht) {
	              donnees.ht = __det.ht;
	              donnees.montants.ht = __det.ht;
	            }
	            if (!donnees.tva_montant && __det.tva_montant) {
	              donnees.tva_montant = __det.tva_montant;
	              donnees.montants.tva = __det.tva_montant;
	            }
	            if (!donnees.ttc && __det.ttc) {
	              donnees.ttc = __det.ttc;
	              donnees.montants.ttc = __det.ttc;
	            }
	          }
	        }

        // ==============================================
        // P0 Fallback (strict): canonical filename -> missing fields only
        // Only used when the uploaded file already follows the canonical naming standard.
        if (fichier && typeof fichier.getName === "function") {
          var __canon = _BM_extractFromCanonicalFilename_(fichier.getName());
          if (__canon) {
            if (!fields.numero_facture && __canon.numero_facture) fields.numero_facture = __canon.numero_facture;
            if (!fields.ttc && __canon.ttc) fields.ttc = __canon.ttc;
            if (!fields.date_doc && __canon.date_doc) fields.date_doc = __canon.date_doc;
            // Never override supplier/client fields already populated (IA_SUPPLIERS / CRM)
            if (!fields.type && __canon.type) fields.type = __canon.type;
          }
        }



        // ============================================================
        // PHASE 2-BIS — SNIPER TICKET ENFORCEMENT (ANTI-BRUIT) — TICKET ONLY
        // Objectif :
        // - Client TICKET = entreprise_source (autoritaire)
        // - Fournisseur TICKET = enseigne (si détectable) ou VIDE (fail-safe)
        // - Montant CB prioritaire si contradiction TTC
        // Impact : AUCUN hors TICKET
        // ============================================================
        const __typeUpper = String(donnees.type || "").toUpperCase();
        if (__typeUpper === "TICKET") {
          // RÈGLE 1 — Client = entreprise_source (écrase toute valeur OCR)
          const __entrepriseSource = String(f.entreprise_source || donnees.entreprise_source || "MARTIN’S TRAITEUR" || "");
          donnees.entreprise_source = __entrepriseSource;

          // NO-OVERWRITE (Cloud Run prioritaire) :
          // - on ne remplace JAMAIS un client non vide
          // - "Unknown" ne doit pas polluer : on autorise le fill si Unknown/UNKNOWN
          const __clientCur = String(donnees.client || "").trim();
          const __clientIsUnknown = (__clientCur.toLowerCase() === "unknown");
          if (!__clientCur || __clientIsUnknown) {
            donnees.client = __entrepriseSource;
          }

          // RÈGLE 2 — Fournisseur = enseigne détectée (sinon fail-safe VIDE, mais jamais = client)
          const __mapSirenToBrand = {
            "399515113": "CARREFOUR",
            "851729384": "TOTALENERGIES"
          };

          const __hay = [
            f.fournisseur, f.societe, f.societe_emettrice, f.enseigne, f.merchant, f.nom_enseigne,
            f.client, donnees.societe, donnees.client_nom
          ].filter(Boolean).join(" ").toUpperCase();

          let __brand = "";

          // 2A) Détection directe par mots-clés
          if (__hay.indexOf("CARREFOUR") >= 0) __brand = "CARREFOUR";
          else if (__hay.indexOf("TOTALENERG") >= 0 || __hay.indexOf("TOTAL ENERG") >= 0) __brand = "TOTALENERGIES";

          // 2B) Fallback SIRET/SIREN (champs OCR) → mapping enseigne connue
          const __siretRaw = String(f.fournisseur_siret || donnees.fournisseur_siret || "");
          const __digits = __siretRaw.replace(/\D/g, "");
          const __siren = (__digits.length >= 9) ? __digits.slice(0, 9) : "";

          if (!__brand && __siren && __mapSirenToBrand[__siren]) {
            __brand = __mapSirenToBrand[__siren];
          }

          // 2C) Détection “SIREN xxx xxx xxx” dans les strings OCR (ex: "~ Siren 399 515 113")
          if (!__brand) {
            const __mSiren = __hay.match(/SIREN\D*([0-9][0-9 \.]*)/);
            if (__mSiren && __mSiren[1]) {
              const __s = String(__mSiren[1]).replace(/\D/g, "").slice(0, 9);
              if (__s && __mapSirenToBrand[__s]) __brand = __mapSirenToBrand[__s];
            }
          }

          // Appliquer fournisseur (societe) : jamais = client
          const __clientUp = String(__entrepriseSource || "").toUpperCase();
          if (__brand && __brand.toUpperCase() !== __clientUp) {
            donnees.societe = __brand;
          } else {
            // fail-safe : pas de faux fournisseur = Martin’s
            const __socUp = String(donnees.societe || "").toUpperCase();
            if (__socUp && __socUp.indexOf("MARTIN") >= 0) {
              donnees.societe = "";
            }
          }

          // Conserver siret si présent
          if (__digits) donnees.fournisseur_siret = __digits;

          // RÈGLE 3 — Montant CB prioritaire si contradiction TTC
          const __cbSignal =
            Boolean(f.ticket_cb_detecte) ||
            /(\bCB\b|\bCARTE\b|\bVISA\b|\bMASTERCARD\b)/i.test(String(f.mode_paiement || "") + " " + __hay);

          let __montantCB = Number(f.montant_encaisse || 0) || 0;

          // Fallback : extraire montant depuis une string type "Payé CB ... 181,34"
          if (!__montantCB) {
            const __mAmt = String(f.client || "").match(/(\d{1,4}[,\.]\d{2})/);
            if (__mAmt && __mAmt[1]) {
              __montantCB = Number(String(__mAmt[1]).replace(",", ".")) || 0;
            }
          }

          if (__cbSignal && __montantCB > 0) {
            donnees.mode_paiement = "CB";
            donnees.statut_paiement = "PAYE";
            donnees.montant_encaisse = __montantCB;

            if (!donnees.montants) donnees.montants = {};
            const __ttcNow = Number(donnees.montants.ttc || 0) || 0;
            if (__montantCB > __ttcNow) {
              donnees.montants.ttc = __montantCB;
            }
          }
        }

        // Cas fournisseur BL : TVA = 0 (et HT = TTC si HT absent)
        if (__typeUpper === "BON_LIVRAISON" || __typeUpper === "BON LIVRAISON" || __typeUpper === "BL") {
          donnees.tva_taux = "0";
          donnees.montants.tva = 0;
          if (!donnees.montants.ht || Number(donnees.montants.ht) === 0) {
            donnees.montants.ht = __ttc;
          }

          // Sniper : si "societe" = MARTIN’S (erreur CloudRun) et que le champ client contient un email,
          // on reconstruit le fournisseur depuis l'email et on force client=Martin’s
          const __email = __extractEmail__(donnees.client_nom || donnees.client || "");
          const __socUp = String(donnees.societe || "").toUpperCase();
          if (__email && __socUp.indexOf("MARTIN") >= 0) {
            const __supplier = __supplierNameFromEmail__(__email);
            if (__supplier) {
              donnees.societe = __supplier;          // émetteur = fournisseur

              // NO-OVERWRITE (Cloud Run prioritaire) :
              const __clientCur2 = String(donnees.client || "").trim();
              const __clientIsUnknown2 = (__clientCur2.toLowerCase() === "unknown");
              if (!__clientCur2 || __clientIsUnknown2) {
                donnees.client = "MARTIN’S TRAITEUR";
              }
            }
          }
        }

        
// Champs étendus (nouveau : utilisés par IndexWriter v2 + audit)
        donnees.date_prestation = donnees.date_prestation || String(f.date_prestation || "");
        donnees.lieu_livraison = donnees.lieu_livraison || String(f.lieu_livraison || "");
        donnees.prestation_type = donnees.prestation_type || String(f.prestation_type || "");
        donnees.prestation_detail = donnees.prestation_detail || String(f.prestation_detail || "");
        donnees.prestation_inclus = donnees.prestation_inclus || String(f.prestation_inclus || "");
        donnees.nb_personnes = (donnees.nb_personnes !== undefined && donnees.nb_personnes !== null && String(donnees.nb_personnes).trim() !== "")
          ? donnees.nb_personnes
          : (Number(f.nb_personnes || 0) || "");

        // Client détaillé (si dispo)
        donnees.client_nom = donnees.client_nom || String(f.client_nom || "");
        donnees.client_adresse = donnees.client_adresse || String(f.client_adresse || "");
        donnees.client_code_postal = donnees.client_code_postal || String(f.client_code_postal || "");
        donnees.client_ville = donnees.client_ville || String(f.client_ville || "");

// Fallback OCR (si CloudRun n'a pas renvoyé cp/ville)
        if ((!donnees.client_code_postal || !donnees.client_ville) && ocrText && !(donnees.fournisseur_siret && (String(donnees.type||'').toUpperCase()==='FACTURE' || String(donnees.document_type||'').toUpperCase()==='FACTURE'))) {
          const pv = OCR_parseClientPostalVille_(ocrText, donnees.client_nom);
          if (pv) {
            if (!donnees.client_code_postal && pv.code_postal) donnees.client_code_postal = pv.code_postal;
            if (!donnees.client_ville && pv.ville) donnees.client_ville = pv.ville;
            if (!donnees.client_adresse && pv.adresse) donnees.client_adresse = pv.adresse;

            logAction("OCR2", "OCR2_CLIENT_POSTAL_VILLE_EXTRACTED", {
              file_id: fileId,
              client_nom: String(donnees.client_nom || ""),
              client_code_postal: String(donnees.client_code_postal || ""),
              client_ville: String(donnees.client_ville || ""),
              client_adresse: String(donnees.client_adresse || "")
            }, "", "INFO");
          } else {
            logAction("OCR2", "OCR2_CLIENT_POSTAL_VILLE_NOT_FOUND", { file_id: fileId }, "", "INFO");
          }
        }
        // Fallback CP/Ville depuis le texte OCR (si CloudRun ne renvoie pas ces champs)
        if ((!donnees.client_code_postal || !donnees.client_ville) && ocrText && !(donnees.fournisseur_siret && (String(donnees.type||'').toUpperCase()==='FACTURE' || String(donnees.document_type||'').toUpperCase()==='FACTURE'))) {
        const pc = OCR_parsePostalCity_(ocrText);
        if (!donnees.client_code_postal && pc.cp) donnees.client_code_postal = pc.cp;
        if (!donnees.client_ville && pc.ville) donnees.client_ville = pc.ville;
       }

        // Marquage OCR
        donnees.ocr_engine = ocrEngine || "UNKNOWN";
        donnees.confiance = Number(ocr.confiance || 0) || 0;

        
      // ✅ Extraction déterministe (conservative) à partir du texte OCR complet (montants + numéro)
      // - Ne remplit que si vide (VIDE > BRUIT)
      // - Objectif: débloquer Nom_Final/Chemin_Final (INSUFFICIENT_DATA) sans toucher Cloud Run
      if (!donnees.numero_facture) {
        const _num = _BM_extractInvoiceNumber_(ocrText);
        if (_num) donnees.numero_facture = _num;
      }
      if (!donnees.ttc || !donnees.ht || !donnees.tva_montant) {
        const _amts = _BM_extractAmounts_(ocrText);
        if (!donnees.ttc && _amts.ttc) donnees.ttc = _amts.ttc;
        if (!donnees.ht && _amts.ht) donnees.ht = _amts.ht;
        if (!donnees.tva_montant && _amts.tva) donnees.tva_montant = _amts.tva;
      }
      logAction("OCR2", "OCR2_DETERMINISTIC_EXTRACT", {
        file_id: String(fileId),
        len_used: ocrText.length,
        numero_facture: String(donnees.numero_facture || ""),
        ht: String(donnees.ht || ""),
        tva_montant: String(donnees.tva_montant || ""),
        ttc: String(donnees.ttc || "")
      }, ".", "INFO");
logAction("OCR2", "OCR2_INJECTION_DONE", {
          file_id: fileId,
          type: donnees.type || "",
          numero_facture: donnees.numero_facture || "",
          societe: donnees.societe || "",
          client: donnees.client || "",
          ttc: (donnees.montants && donnees.montants.ttc !== undefined && donnees.montants.ttc !== null && String(donnees.montants.ttc).trim() !== "")
            ? donnees.montants.ttc
            : "",
          tva_taux: donnees.tva_taux || "",
          nb_personnes: (donnees.nb_personnes !== undefined && donnees.nb_personnes !== null) ? donnees.nb_personnes : ""
        }, "", "INFO");

        // Log legacy conservé (compatibilité)
        logAction("OCR", "OCR_FIELDS_INJECTED_INTO_DONNEES", {
          file_id: fileId,
          type: donnees.type || "",
          numero_facture: donnees.numero_facture || "",
          societe: donnees.societe || "",
          client: donnees.client || "",
          ttc: (donnees.montants && donnees.montants.ttc !== undefined && donnees.montants.ttc !== null && String(donnees.montants.ttc).trim() !== "")
  ? donnees.montants.ttc
  : "",
          has_ocr_text: Boolean(ocrText && ocrText.length)
        }, "", "INFO");

      } else {
        logAction("OCR2", "OCR2_NO_FIELDS_TO_INJECT", { file_id: fileId }, "", "INFO");
        logAction("OCR", "OCR_NO_FIELDS_TO_INJECT", { file_id: fileId }, "", "INFO");
      }

      logAction("OCR2", "OCR2_END", { file_id: fileId }, "", "INFO");
    } catch (eInject) {
      logAction("OCR2", "OCR2_ERROR", { file_id: fileId, err: String(eInject) }, "", "ERREUR");
      logAction("OCR", "OCR_FIELDS_INJECT_ERROR", { file_id: fileId, err: String(eInject) }, "", "ERREUR");
    }

    // CloudRun = source de vérité → pas d’override IA Memory ici
    logAction("OCR", "OCR_OVERRIDE_DISABLED_FOR_CLOUDRUN", {
      engine_cfg: String(BM_CFG.get("OCR_ENGINE") || ""),
      engine_run: String(ocrEngine || ""),
      reason: "CloudRun_is_source_of_truth"
    }, '', "INFO");

 // OCR3 — IA / APPRENTISSAGE & RÈGLES (LOGS + GARDE-FOU)
    // =========================
    try {
      logAction("OCR3", "OCR3_START", { file_id: fileId }, "", "INFO");

      const rule = (ocr && ocr.rule_created) ? ocr.rule_created : null;
      const templateSig = rule ? String(rule.template_signature || "").trim() : "";
      const hashDoc = rule ? String(rule.hash_document || "").trim() : "";

      // Si CloudRun ne propose pas de règle -> OCR3 = NO
      if (!rule || (!templateSig && !hashDoc)) {
        logAction("OCR3", "OCR3_DECISION", {
          file_id: fileId,
          learn: false,
          reason: "NO_RULE_PROVIDED_BY_ENGINE"
        }, "", "INFO");
        logAction("OCR3", "OCR3_END", { file_id: fileId }, "", "INFO");
      } else {
        // Check si déjà appris (hash prioritaire, puis template_signature)
        let alreadyKnownByTemplate = false;
        let alreadyKnownByHash = false;

        try {
          alreadyKnownByHash = BM_IAMEMORY_hasHashDocument_(hashDoc);
          alreadyKnownByTemplate = BM_IAMEMORY_hasTemplateSignature_(templateSig);
        } catch (eCheck) {
          logAction("OCR3", "OCR3_RULE_CHECK_WARN", {
            file_id: fileId,
            template_signature: templateSig,
            hash_document: hashDoc,
            err: String(eCheck)
          }, "", "WARN");

          // SAFE: en cas de doute, on n’empêche pas l’apprentissage
          alreadyKnownByHash = false;
          alreadyKnownByTemplate = false;
        }

        if (alreadyKnownByHash || alreadyKnownByTemplate) {
          logAction("OCR3", "OCR3_DECISION", {
            file_id: fileId,
            learn: false,
            reason: alreadyKnownByHash ? "HASH_FOUND_IN_IAMEMORY" : "TEMPLATE_FOUND_IN_IAMEMORY",
            template_signature: templateSig,
            hash_document: hashDoc
          }, "", "INFO");
          logAction("OCR3", "OCR3_END", { file_id: fileId }, "", "INFO");
        } else {
          logAction("OCR3", "OCR3_DECISION", {
            file_id: fileId,
            learn: true,
            reason: "NEW_LAYOUT",
            template_signature: templateSig
          }, "", "INFO");

          // ✅ IA_MEMORY: AUTO-LEARN DÉSACTIVÉ (source unique = VALIDATION HUMAINE)
          // Raison : éviter double écriture IA_MEMORY (auto + human)
          logAction("IA_MEMORY", "AUTO_LEARN_SKIPPED", {
            file_id: fileId,
            reason: "HUMAN_VALIDATION_IS_SINGLE_SOURCE_OF_TRUTH",
            template_signature: templateSig,
            hash_document: hashDoc
          }, "", "INFO");

          // Log legacy conservé (compatibilité)
          logAction("OCR", "IA_MEMORY_RULE_APPENDED", {
            file_id: fileId,
            template_signature: templateSig,
            hash_document: hashDoc
          }, "", "INFO");

          logAction("OCR3", "OCR3_END", { file_id: fileId }, "", "INFO");
        }
      }
    } catch (eMem) {
      logAction("OCR3", "OCR3_ERROR", { file_id: fileId, err: String(eMem) }, "", "ERREUR");
      logAction("OCR", "IA_MEMORY_WRITE_FAIL", { file_id: fileId, err: String(eMem) }, "", "ERREUR");
    }
    // R06 — IA_SUPPLIERS (APPLY sur scan) : remplit uniquement l'identité fournisseur (VIDE > BRUIT)
    try {
      const r06 = R06_SUPPLIER_MEMORY__APPLY_IF_AVAILABLE_(donnees, fileId) || {};
      try {
        logAction("R06_IA_MEMORY", "SUPPLIER_MEMORY_APPLY_RESULT", {
          file_id: fileId,
          ok: !!r06.ok,
          applied: !!r06.applied,
          reason: r06.reason || "",
          siret14: r06.siret14 || r06.siret || "",
          siren9: r06.siren9 || "",
          fields_written: r06.fields_written || []
        }, "", "INFO");
      } catch (_) {}
    } catch (eApply) {
      try {
        logAction("R06_IA_MEMORY", "SUPPLIER_MEMORY_APPLY_FAIL", { file_id: fileId, err: String(eApply) }, "", "ERREUR");
      } catch (_) {}
    }

    // Proposition classement (placeholder)
    const proposition = proposerClassement(donnees);

    // JSONL — payload final (1 ligne key=value;...) juste avant écriture INDEX_GLOBAL
try {
  const __kv = (k, v) => {
    const s = (v === null || v === undefined) ? "" : String(v);
    return k + "=" + s.replace(/\s+/g, " ").replace(/;/g, ",").trim();
  };

  const __ttc = (donnees.montants && donnees.montants.ttc !== undefined && donnees.montants.ttc !== null && String(donnees.montants.ttc).trim() !== "") ? donnees.montants.ttc : "";
  const __ht  = (donnees.montants && donnees.montants.ht  !== undefined && donnees.montants.ht  !== null && String(donnees.montants.ht ).trim() !== "") ? donnees.montants.ht  : "";
  const __tva = (donnees.montants && donnees.montants.tva !== undefined && donnees.montants.tva !== null && String(donnees.montants.tva).trim() !== "") ? donnees.montants.tva : "";

  const __line = [
    __kv("type", donnees.type || donnees.document_type || ""),
    __kv("document_type", donnees.document_type || ""),
    __kv("societe", donnees.societe || ""),
    __kv("client", donnees.client || ""),
    __kv("fournisseur_siret", donnees.fournisseur_siret || ""),
    __kv("date_doc", donnees.date_document || donnees.date_doc || ""),
    __kv("numero_facture", donnees.numero_facture || ""),
    __kv("ttc", __ttc),
    __kv("ht", __ht),
    __kv("tva_montant", __tva),
    __kv("tva_taux", donnees.tva_taux || ""),
    __kv("mode_paiement", donnees.mode_paiement || ""),
    __kv("ticket_cb_detecte", (donnees.ticket_cb_detecte === true ? "TRUE" : "")),
    __kv("confidence", donnees.confiance || donnees.confidence || ""),
    __kv("level", donnees.level || "")
  ].join(";");

  logAction(
    "OCR",
    "OCR_FINAL_PAYLOAD_JSONL",
    {
      file_id: fileId,
      payload_final: {
        donnees: donnees,
        proposition: proposition
      }
    },
    "",
    "INFO"
  );
} catch (_) {}

    // Index Global
    enregistrerDansIndex(fichier, donnees, proposition);

    // CRM — ROUTAGE CANONIQUE (SANS SUPPRESSION)
// 1. CRM_CLIENT = base client (1 ligne / client)
// 2. CRM_FACTURE = écritures facture

// Client (création ou enrichissement si absent)
if (typeof BM_CRM_CLIENT_upsertFromDonnees_ === "function") {
  BM_CRM_CLIENT_upsertFromDonnees_(donnees);
} else {
  logAction("CRM", "CRM_CLIENT_HANDLER_MISSING", {
    phase: "SCAN",
    reason: "POST_VALIDATION_ONLY — création/enrichissement client exécuté après validation humaine"
  }, "", "INFO");
}

// Facture (append uniquement si document FACTURE)
if (String(donnees.type || "").toUpperCase() === "FACTURE") {
  if (typeof BM_CRM_FACTURE_appendFromDonnees_ === "function") {
    BM_CRM_FACTURE_appendFromDonnees_(donnees);
  } else {
    logAction("CRM", "CRM_FACTURE_HANDLER_MISSING", {
      phase: "SCAN",
      reason: "POST_VALIDATION_ONLY — écriture facture exécutée après validation humaine"
    }, "", "INFO");
  }
}


    logAction('CLASSEMENT', 'traiterNouveauDocument_fin', {
      file_id: fileId,
      type: donnees.type || 'autre',
      auto: false,
      confiance: Number(donnees.confiance || 0)
    }, '', 'INFO');

  } catch (e) {
    logAction('CLASSEMENT', 'traiterNouveauDocument_error', { stack: String(e && e.stack ? e.stack : e) }, '', 'ERREUR');
  }
}


function proposerClassement(donnees) {
  // OPTION A — règle métier de chemin (indépendante OCR3)
  const soc = String(donnees?.societe || "").trim();
  const typ = String(donnees?.type || "").trim().toUpperCase();

  // Année: priorité à date_document (dd/mm/yyyy ou yyyy-mm-dd), sinon année courante
  const y = (function () {
    const d = String(donnees?.date_document || "").trim();
    let m = d.match(/\b(\d{2})\/(\d{2})\/(\d{4})\b/);
    if (m) return Number(m[3]);
    m = d.match(/\b(\d{4})-(\d{2})-(\d{2})\b/);
    if (m) return Number(m[1]);
    return new Date().getFullYear();
  })();

  // Règle canonique demandée (sans sous-dossier client)
  if (soc === "MARTIN’S TRAITEUR" && typ === "FACTURE") {
    const chemin = "HOLDING / 03_CLIENTS / MARTINS_TRAITEUR / 01_COMPTABILITE / 02_FACTURES_CLIENTS / " + y;

    try {
      logAction("R07", "PATH_PROPOSED_FROM_RULE", {
        societe: soc,
        type: typ,
        annee: y,
        chemin_final: chemin
      }, "", "INFO");
    } catch (e) {}

    return { chemin: chemin, auto: true, from_rule: true, annee: y };
  }

  // fallback: comportement existant
  return { chemin: String(donnees?.chemin || ""), auto: false };
}


function enregistrerDansIndex(fichier, donnees, proposition) {
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName("INDEX_GLOBAL");
    if (!sh) {
      logAction("INDEX", "INDEX_SHEET_NOT_FOUND", { expected: "INDEX_GLOBAL" }, "", "ERREUR");
      return;
    }

    // Lire en-tête
    const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0];
    const headerIndex = {};
    headers.forEach((h, i) => headerIndex[String(h || "").trim()] = i);

    logAction("INDEX", "INDEX_MAP_BUILD_START", {
      file_id: fichier.getId(),
      headers_count: headers.length
    }, "", "INFO");

    // Construire ligne vide alignée
    const row = new Array(headers.length).fill("");

    // Helper safe
    const set = (col, val) => {
      if (headerIndex[col] !== undefined) row[headerIndex[col]] = val;
    };

    // Champs système
    set("Timestamp", new Date());
    set("Fichier_ID", fichier.getId());
    set("Nom_Original", fichier.getName());
    // R07 — écrire la décision métier (Nom_Final / Chemin_Final)
    const nomFinal = String(donnees?.nom_final || donnees?.Nom_Final || "").trim();
    const cheminFinal = String(proposition?.chemin || "").trim();

    set("Nom_Final", nomFinal);
    set("Chemin_Final", cheminFinal);

    // ============================================================
    // WORK — P_SUPPLIERS_INDEX_AUTOFILL — FACTURE FOURNISSEUR ONLY
    // Objectif : compléter INDEX_GLOBAL (paiement + fournisseur) sans bruit
    // ============================================================

    // Helpers anti-bruit (fail-safe)
    const _isNoiseValue = (v) => {
      const s = String(v || "").trim();
      if (!s) return true;
      if (s.length < 2) return true;
      if (/@|https?:\/\/|www\./i.test(s)) return true; // email/url
      if (/\b\d{14}\b/.test(s)) return true;           // SIRET seul
      if (/\b\d{3}\s?\d{3}\s?\d{3}\b/i.test(s)) return true; // SIREN seul
      if (/\b\d+[.,]\d{2}\b/.test(s) && s.replace(/[^\d]/g, "").length <= 6) return true; // montant isolé
      if (s.split(/\s+/).length >= 8) return true;     // phrase longue
      return false;
    };

    const _cleanSiret14 = (v) => {
      const digits = String(v || "").replace(/\D/g, "");
      return digits.length === 14 ? digits : "";
    };

    const _toBool = (v) => {
      if (v === true || v === "TRUE") return true;
      if (v === false || v === "FALSE") return false;
      const s = String(v || "").toLowerCase().trim();
      if (["1", "yes", "oui", "vrai", "true"].includes(s)) return true;
      if (["0", "no", "non", "faux", "false"].includes(s)) return false;
      return false;
    };

    // --- Document (fallback keys, sans casser l’existant)
    const typeDoc = String(donnees?.type || donnees?.document_type || "").trim();
    const numFact = String(donnees?.numero_facture || donnees?.reference || "").trim();

    // Societe = fournisseur (si dispo) mais jamais bruit
    const societeCandidate = String(donnees?.societe || donnees?.fournisseur || "").trim();
    const societeSafe = _isNoiseValue(societeCandidate) ? "" : societeCandidate;

    // Client : conserver ce que le pipeline a déjà stabilisé (souvent Martin’s Traiteur)
    const clientVal = String(donnees?.client || "").trim();

    // Date_Doc : prefer date_doc (OCR mapping), fallback date_document
    const dateDocVal = String(donnees?.date_doc || donnees?.date_document || donnees?.date_emission || "").trim();

    set("Type", typeDoc);
    set("N° Facture", numFact);
    set("Societe", societeSafe);
    set("Client", clientVal);
    set("Date_Doc", dateDocVal);
// ============================================================
// WORK — P_TICKET_PRO_ENRICH_INDEX — CARREFOUR — TICKET ONLY
// Objectif : enrichissement déterministe FACTURE CAISSE (safe)
// NOTE : ocrText n’existe PAS dans enregistrerDansIndex() → on utilise uniquement "donnees".
// ============================================================

if (String(typeDoc).toUpperCase() === "TICKET") {

  // --- Fournisseur (priorité aux champs déjà injectés)
  const fournisseurGuess = String(donnees?.societe || donnees?.fournisseur || societeSafe || "").toUpperCase().trim();
  if (!societeSafe && fournisseurGuess) {
    // fail-safe : on n’écrit que si c’est court et non bruit
    if (fournisseurGuess.length >= 3 && fournisseurGuess.length <= 40) {
      set("Societe", fournisseurGuess);
    }
  }

  // --- SIRET (14 digits) via donnees (CloudRun / OCR2)
  const siretRaw = String(donnees?.fournisseur_siret || donnees?.fournisseurSiret || donnees?.siret || "").trim();
  const siret14 = siretRaw.replace(/\D/g, "");
  if (siret14.length === 14) {
    set("Fournisseur_SIRET", siret14);
  }

  // --- Paiement CB (via donnees)
  const modePaiement = String(donnees?.mode_paiement || "").toUpperCase().trim();
  const cbDetecte =
    (donnees?.ticket_cb_detecte === true) ||
    (String(donnees?.ticket_cb_detecte || "").toUpperCase().trim() === "TRUE") ||
    (modePaiement === "CB") ||
    /CB|CARTE/.test(modePaiement);

  if (cbDetecte) {
    set("Mode_Paiement", "CB");
    set("Statut_Paiement", "PAYE");
    set("Ticket_CB_Detecte", "TRUE");
  }

  // --- Montant encaissé : priorité montant explicite, sinon TTC si CB
  const montantEncaisse =
    Number(donnees?.montant_encaisse || donnees?.montantEncaisse || 0) ||
    Number(donnees?.ttc || donnees?.total_ttc || 0) ||
    0;

  if (cbDetecte && montantEncaisse > 0) {
    set("Montant_Encaisse", montantEncaisse);
  }

  // --- Date encaissement : uniquement si déjà fourni (sinon VIDE)
  const dateEnc = String(donnees?.date_encaissement || donnees?.dateEncaissement || "").trim();
  if (dateEnc) {
    set("Date_Encaissement", dateEnc);
  }
}

    // --- Montants : prefer structure existante, sinon root (OCR mapping)
// FAIL-SAFE : on n’écrit pas 0 si inconnu (VIDE > BRUIT)
    const htVal  = (donnees?.montants && donnees.montants.ht !== undefined) ? donnees.montants.ht : (donnees?.ht ?? "");
    const tvaVal = (donnees?.montants && donnees.montants.tva !== undefined) ? donnees.montants.tva : (donnees?.tva_montant ?? donnees?.montant_tva ?? "");
    const ttcVal = (donnees?.montants && donnees.montants.ttc !== undefined) ? donnees.montants.ttc : (donnees?.ttc ?? donnees?.total_ttc ?? "");

    if (Number(htVal)  > 0) set("HT", Number(htVal));
    if (Number(tvaVal) > 0) set("TVA Montant", Number(tvaVal));
    if (Number(ttcVal) > 0) set("TTC", Number(ttcVal));

    // --- FACTURE FOURNISSEUR / dépense fournisseur : mapping paiement + SIRET
    // Condition stricte : ne touche pas BL ; et n’injecte rien si incertain
    const __hasPaymentSignals =
      !!String(donnees?.mode_paiement || "").trim() ||
      !!String(donnees?.statut_paiement || "").trim() ||
      ((donnees?.montant_encaisse != null) && (Number(donnees.montant_encaisse) > 0));

    const isSupplierExpense =
      (typeDoc === "FACTURE" || typeDoc === "FACTURE_FOURNISSEUR") ||
      (typeDoc === "TICKET" && (
        societeSafe ||
        _cleanSiret14(donnees?.fournisseur_siret || donnees?.Fournisseur_SIRET) ||
        __hasPaymentSignals
      ));

    if (isSupplierExpense) {
      // SIRET : OCR si présent
      let siret14 = _cleanSiret14(donnees?.fournisseur_siret || donnees?.Fournisseur_SIRET);

      // Enrich deterministe CARREFOUR : Siren 399 515 113 -> SIRET 39951511300021
      // (seulement si on a déjà CARREFOUR comme société et pas de SIRET 14)
      if (!siret14 && String(societeSafe || "").toUpperCase().includes("CARREFOUR")) {
        const clientRaw = String(donnees?.client || "").toUpperCase();
        const siren9 = clientRaw.replace(/\D/g, "").match(/\d{9}/);
        if (siren9 && siren9[0] === "399515113") {
          siret14 = "39951511300021";
        }
      }

      const ticketCB = _toBool(donnees?.ticket_cb_detecte || donnees?.Ticket_CB_Detecte);
      const modePaiement = String(donnees?.mode_paiement || "").trim();
      const statutPaiement = String(donnees?.statut_paiement || "").trim();

      // Ticket CB : si CB détecté côté OCR → Mode_Paiement=CB
      const modeFinal = (modePaiement === "CB" || ticketCB) ? "CB" : (modePaiement || "");

      // Cohérence : si Mode_Paiement=CB, alors Ticket_CB_Detecte=TRUE
      const ticketCBFinal = (ticketCB || modeFinal === "CB");

      // Statut : PAYE uniquement si signal “payé” ou CB (sinon vide)
      const statutFinal =
        (String(statutPaiement).toUpperCase() === "PAYE" || ticketCBFinal) ? "PAYE" :
        (String(statutPaiement).toUpperCase() === "A_PAYER") ? "A_PAYER" :
        "";

      // Date/Montant encaissement : uniquement si fourni (sinon vide)
      const dateEnc = String(donnees?.date_encaissement || "").trim();
      const montantEnc = String(donnees?.montant_encaisse || donnees?.montant_encaissement || "").trim();

      if (siret14) set("Fournisseur_SIRET", siret14);

      // FAIL-SAFE : ne jamais écrire "FALSE" (VIDE > BRUIT)
      if (ticketCBFinal) set("Ticket_CB_Detecte", "TRUE");

      if (modeFinal) set("Mode_Paiement", modeFinal);
      if (statutFinal) set("Statut_Paiement", statutFinal);

      if (dateEnc) set("Date_Encaissement", dateEnc);
      if (montantEnc) set("Montant_Encaisse", montantEnc);
    }

    // OCR
    set("Statut_OCR", donnees.ocr_engine || "");
    set("Confiance", Number(donnees.confiance || 0));

    // Prestation / client étendu
    set("Client_nom", donnees.client_nom || "");
    set("Client_adresse", donnees.client_adresse || "");
    set("Client_code_postal", donnees.client_code_postal || "");
    set("Client_ville", donnees.client_ville || "");
    set("Date_prestation", donnees.date_prestation || "");
    set("Lieu_livraison", donnees.lieu_livraison || "");
    set("Prestation_type", donnees.prestation_type || "");
    set("Prestation_detail", donnees.prestation_detail || "");
    set("Prestation_inclus", donnees.prestation_inclus || "");

    // TVA / personnes (VIDE > BRUIT)
    let tvaTaux = donnees.tva_taux || "";
    if (typeof tvaTaux === "string") {
      const raw = tvaTaux.trim();
      if (raw) {
        const n = Number(raw.replace(",", ".").replace("%", ""));
        if (!isNaN(n)) {
          if (String(raw) !== String(n)) {
            logAction("INDEX", "INDEX_VALUE_NORMALIZATION_WARNING", {
              field: "TVA_taux",
              raw: raw,
              normalized: n
            }, "", "WARN");
          }
          tvaTaux = n;
        } else {
          tvaTaux = raw;
        }
      } else {
        tvaTaux = "";
      }
    }
    set("TVA_taux", tvaTaux);
    set("Nb_personnes", donnees.nb_personnes || "");

    // Validation humaine / ID
    set("Valide_Par", "");
    set("Date_Validation", "");
// R07 — Client_ID canonique : récupérer depuis CRM_CLIENTS si possible
// IMPORTANT: Sur TICKET / FACTURE_FOURNISSEUR, Client_ID n'est pas bloquant (éviter bruit)
const docTypeR07 = String(
  donnees?.type_doc || donnees?.type || donnees?.document_type || ""
).trim().toUpperCase();

if (docTypeR07 === "TICKET" || docTypeR07 === "FACTURE_FOURNISSEUR") {
  set("Client_ID", "");
  try {
    logAction("R07", "CLIENT_ID_SKIPPED", {
      reason: "DOC_TYPE_NOT_CUSTOMER_FLOW",
      doc_type: docTypeR07,
      client: String(donnees?.client || donnees?.client_nom || ""),
      file_id: fichier.getId()
    }, "", "INFO");
  } catch (e) {}
} else {
  let clientId = String(donnees?.client_id || donnees?.Client_ID || "").trim();
  if (!clientId) clientId = BM_RESOLVE_CLIENT_ID_FROM_CRM_(donnees?.client || donnees?.client_nom || "");

  if (clientId) {
    set("Client_ID", clientId);
    try {
      logAction("R07", "CLIENT_ID_PROPAGATED", {
        client: String(donnees?.client || donnees?.client_nom || ""),
        client_id: clientId,
        file_id: fichier.getId()
      }, "", "INFO");
    } catch (e) {}
  } else {
    set("Client_ID", "");
    try {
      logAction("R07", "CLIENT_ID_MISSING", {
        client: String(donnees?.client || donnees?.client_nom || ""),
        file_id: fichier.getId()
      }, "", "INFO");
    } catch (e) {}
  }
}



    // Vérification finale
    logAction("INDEX", "INDEX_ROW_LENGTH_CHECK", {
      row_len: row.length,
      headers_len: headers.length,
      ok: row.length === headers.length
    }, "", row.length === headers.length ? "INFO" : "ERREUR");

    if (row.length !== headers.length) {
      throw new Error("Index row length mismatch");
    }

    // DIAG JSONL — PAYLOAD FINAL JUSTE AVANT ÉCRITURE INDEX_GLOBAL
    DIAG_jsonl(
      "OCR_FINAL_PAYLOAD_JSONL",
      {
        file_id: fichier.getId(),
        donnees: donnees,
        proposition: proposition,
        row: row
      }
    );

    sh.appendRow(row);

    logAction("INDEX", "INDEX_APPEND_OK", {
      file_id: fichier.getId(),
      sheet: "INDEX_GLOBAL"
    }, "", "INFO");

    // ---------------------------
    // R-05 POST-OCR (décision métier)
    // - Génère Nom_Final / Chemin_Final
    // - Remonte dans CRM + COMPTABILITE
    // - Aucun contournement : séparation ingestion vs décision
    // ---------------------------
    try {
      if (typeof R05_POST_OCR_applyToFileId === "function") {
        R05_POST_OCR_applyToFileId(fichier.getId());
      } else {
        logAction("R05", "R05_NOT_LOADED", {
          file_id: fichier.getId(),
          phase: "SCAN",
          reason: "POST_VALIDATION_ONLY — CRM/COMPTA/MOVE exécutés via R05_POST_VALIDATION après validation humaine"
        }, "", "INFO");
      }
    } catch (eR05) {
      logAction("R05", "R05_POST_OCR_ERROR", { file_id: fichier.getId(), err: String(eR05) }, "", "ERREUR");
    }

  } catch (e) {
    logAction("INDEX", "INDEX_APPEND_ERROR", { err: String(e) }, "", "ERREUR");
  }
}


function OCR1_ENRICH_extractCandidates_(ocrText, fields, fichier) {
  const text = String(ocrText || "");
  const f = (fields && typeof fields === "object") ? fields : {};

  const candidates = {};
  const deferKeys = [];
  const patterns = [];

  // Helpers
  const norm = (s) => String(s || "").replace(/\s+/g, " ").trim();
  const asNumber = (s) => {
    const x = String(s || "").replace(/\s/g, "").replace(",", ".").replace("€", "");
    const n = Number(x);
    return isNaN(n) ? null : n;
  };
  const findUnique = (re, groupIndex = 1) => {
    const m = [];
    let match;
    const r = new RegExp(re.source, re.flags.includes("g") ? re.flags : re.flags + "g");
    while ((match = r.exec(text)) !== null) {
      const v = norm(match[groupIndex] || "");
      if (v) m.push(v);
      if (m.length > 10) break;
    }
    const uniq = Array.from(new Set(m));
    if (uniq.length === 1) return uniq[0];
    return null;
  };
  const findUniquePercent = () => {
    const re = /(\d{1,2}(?:[.,]\d{1,2})?)\s*%/g;
    const vals = [];
    let match;
    while ((match = re.exec(text)) !== null) {
      const raw = match[1];
      const n = Number(String(raw).replace(",", "."));
      if (!isNaN(n)) vals.push(n);
      if (vals.length > 20) break;
    }
    const uniq = Array.from(new Set(vals));
    return uniq.length === 1 ? uniq[0] : null;
  };

  // === type_doc (FACTURE / BDC / DEVIS) ===
  let typeGuess = norm(f.type || f.document_type || "");
  if (!typeGuess) {
    if (/bon\s+de\s+commande/i.test(text) || /\bBDC\b/i.test(text) || /\bBC\b/i.test(text)) typeGuess = "BDC";
    else if (/\bdevis\b/i.test(text)) typeGuess = "DEVIS";
    else if (/\bfacture\b/i.test(text) || /\bFC\b/i.test(text)) typeGuess = "FACTURE";
  }
  if (typeGuess) {
    patterns.push("type_doc");
    candidates.type_doc = { value: typeGuess.toUpperCase(), score: 0.9, source: (f.type || f.document_type) ? "fields" : "regex" };
  } else {
    deferKeys.push("type_doc");
  }

  // === client (À l’attention de / Attn) ===
  let client = norm(f.client_nom || f.client || "");
  if (!client) {
    const c1 = findUnique(/A\s+l[’']attention\s+de\s+([A-Z0-9 \-']{3,})/ig, 1);
    const c2 = findUnique(/\bAttn\s*[:\-]?\s*([A-Z0-9 \-']{3,})/ig, 1);
    client = c1 || c2 || "";
    if (client) patterns.push("client_attention");
  } else {
    patterns.push("client_fields");
  }
  if (client) {
    candidates.client = { value: client, score: (f.client_nom || f.client) ? 0.9 : 0.8, source: (f.client_nom || f.client) ? "fields" : "regex" };
  } else {
    deferKeys.push("client");
  }

  // === societe_emettrice ===
  let soc = norm(f.societe || f.entreprise_source || "");
  if (!soc && /MARTIN[’'S]*\s+TRAITEUR/i.test(text)) {
    soc = "MARTIN’S TRAITEUR";
    patterns.push("societe_keyword");
  } else if (soc) {
    patterns.push("societe_fields");
  }
  if (soc) {
    candidates.societe_emettrice = { value: soc, score: soc ? 0.9 : 0, source: (f.societe || f.entreprise_source) ? "fields" : "regex" };
  } else {
    deferKeys.push("societe_emettrice");
  }

  // === numero_doc (FC 2025-143 etc) ===
  let num = norm(f.numero_facture || "");
  if (!num) {
    const n1 = findUnique(/\bFC\s*[\d]{4}\s*[-\/]\s*[\d]{1,5}\b/ig, 0);
    const n2 = findUnique(/\bFC0+\d{2,6}\b/ig, 0);
    const n3 = findUnique(/\bBDC\s*[\d]{4}\s*[-\/]\s*[\d]{1,6}\b/ig, 0);
    num = n1 || n2 || n3 || "";
    if (num) patterns.push("numero_doc_regex");
  } else {
    patterns.push("numero_doc_fields");
  }
  if (num) {
    candidates.numero_doc = { value: num, score: (f.numero_facture) ? 0.9 : 0.8, source: (f.numero_facture) ? "fields" : "regex" };
  } else {
    deferKeys.push("numero_doc");
  }

  // === date_facture / date_prestation ===
  const dateDoc = norm(f.date_doc || "");
  const datePrest = norm(f.date_prestation || "");
  const d1 = dateDoc || findUnique(/\b(\d{2}\/\d{2}\/\d{4})\b/ig, 1);
  if (d1) {
    candidates.date_facture = { value: d1, score: dateDoc ? 0.9 : 0.8, source: dateDoc ? "fields" : "regex" };
    patterns.push("date_doc");
  } else deferKeys.push("date_facture");

  if (datePrest) {
    candidates.date_prestation = { value: datePrest, score: 0.9, source: "fields" };
    patterns.push("date_prestation_fields");
  } else {
    // tentative : si une seule date et règle métier “souvent identique”, on ne FORCE PAS → defer (sécurité)
    deferKeys.push("date_prestation");
  }

  // === lieu_prestation ===
  const lieu = norm(f.lieu_livraison || "");
  if (lieu) {
    candidates.lieu_prestation = { value: lieu, score: 0.9, source: "fields" };
    patterns.push("lieu_fields");
  } else {
    const l1 = findUnique(/\bLieu\s*[:\-]\s*([A-Z0-9À-ÿ \-']{4,})/ig, 1);
    if (l1) {
      candidates.lieu_prestation = { value: l1, score: 0.8, source: "regex" };
      patterns.push("lieu_regex");
    } else deferKeys.push("lieu_prestation");
  }

  // === nb_personnes (160 pers / 160 personnes) ===
  const nbFromFields = (f.nb_personnes !== undefined && f.nb_personnes !== null && String(f.nb_personnes).trim() !== "") ? Number(f.nb_personnes) : null;
  if (nbFromFields && !isNaN(nbFromFields)) {
    candidates.nb_personnes = { value: nbFromFields, score: 0.9, source: "fields" };
    patterns.push("nb_personnes_fields");
  } else {
    const m = findUnique(/\b(\d{1,4})\s*(?:pers(?:onnes)?|pax)\b/ig, 1);
    if (m) {
      const n = Number(m);
      if (!isNaN(n)) {
        candidates.nb_personnes = { value: n, score: 0.8, source: "regex" };
        patterns.push("nb_personnes_regex");
      } else deferKeys.push("nb_personnes");
    } else deferKeys.push("nb_personnes");
  }

  // === tva_taux (unique %) ===
  const tvaField = norm(f.tva_taux || f.tva_rate || "");
  if (tvaField) {
    const n = asNumber(tvaField);
    candidates.tva_taux = { value: (n !== null ? n : tvaField), score: 0.9, source: "fields" };
    patterns.push("tva_fields");
  } else {
    const p = findUniquePercent();
    if (p !== null) {
      candidates.tva_taux = { value: p, score: 0.8, source: "regex_unique_percent" };
      patterns.push("tva_unique_percent");
    } else deferKeys.push("tva_taux");
  }

  // === montant_ht (si “HT” clairement libellé + unique) ===
  const htField = (f.ht !== undefined && f.ht !== null && String(f.ht).trim() !== "") ? Number(f.ht) : null;
  if (htField && !isNaN(htField)) {
    candidates.montant_ht = { value: htField, score: 0.9, source: "fields" };
    patterns.push("ht_fields");
  } else {
    const htTxt = findUnique(/\bHT\b[^0-9]{0,12}([0-9][0-9\s]*[.,]?\d{0,2})/ig, 1);
    if (htTxt) {
      const n = asNumber(htTxt);
      if (n !== null) {
        candidates.montant_ht = { value: n, score: 0.8, source: "regex" };
        patterns.push("ht_regex");
      } else deferKeys.push("montant_ht");
    } else deferKeys.push("montant_ht");
  }

  const signals = {
    type_guess: candidates.type_doc ? candidates.type_doc.value : "",
    client_guess: candidates.client ? candidates.client.value : "",
    societe_guess: candidates.societe_emettrice ? candidates.societe_emettrice.value : "",
    numero_doc_guess: candidates.numero_doc ? candidates.numero_doc.value : "",
    patterns_found: patterns.join(",")
  };

  return { signals, candidates, deferKeys };
}


function OCR_parsePostalCity_(ocrText) {
  const text = String(ocrText || "").replace(/\s+/g, " ").trim();
  if (!text) return { cp: "", ville: "" };

  // Cherche un pattern "971xx VILLE" ou "xxxxx VILLE"
  const re = /\b(\d{5})\s+([A-ZÀ-Ÿ][A-ZÀ-Ÿ \-']{2,40})\b/g;
  const hits = [];
  let m;
  while ((m = re.exec(text)) !== null) {
    const cp = String(m[1] || "").trim();
    let ville = String(m[2] || "").trim();

    // Nettoyage: stop si on capte du bruit (APE/SIRET/téléphones)
    if (/APE|SIRET|TEL|GSM|VÉTÉRINAIRE|VETERINAIRE/i.test(ville)) continue;
    if (/\d{2,}/.test(ville)) continue;

    // Coupe ville trop longue
    if (ville.length > 40) ville = ville.slice(0, 40).trim();

    hits.push({ cp, ville });
    if (hits.length > 10) break;
  }

  // Unique uniquement (mode “tentative sûre”)
  const uniq = {};
  hits.forEach(h => { uniq[h.cp + "|" + h.ville] = h; });
  const keys = Object.keys(uniq);
  if (keys.length === 1) return uniq[keys[0]];

  return { cp: "", ville: "" };
}


function OCR_parseClientPostalVille_(ocrText, clientNom) {
  const raw = String(ocrText || "");
  if (!raw) return null;

  const text = raw.replace(/\r/g, "\n");
  const upper = text.toUpperCase();

  // On essaie d'isoler le bloc "A L'ATTENTION DE / ATTN" pour éviter de capter la zone bas de page (SIRET/APE/vétérinaire etc.)
  const anchors = [
    "A L'ATTENTION DE",
    "A L’ATTENTION DE",
    "À L'ATTENTION DE",
    "À L’ATTENTION DE",
    "ATTN",
    "ATTENTION"
  ];

  let start = -1;
  for (let i = 0; i < anchors.length; i++) {
    const idx = upper.indexOf(anchors[i]);
    if (idx >= 0) { start = idx; break; }
  }

  // Fenêtre d'analyse : si anchor trouvé -> proche du bloc client, sinon on prend le début du doc (mais fenêtre limitée)
  const windowText = (start >= 0) ? text.slice(start, start + 500) : text.slice(0, 500);

  // Adresse (facultatif) : on récupère quelques lignes après l’ancre
  const lines = windowText.split("\n").map(s => s.trim()).filter(Boolean);

  // Cherche un code postal FR (5 digits) suivi d'une ville (lettres/espaces/-)
  // IMPORTANT: on évite les faux positifs en demandant 5 chiffres + ville sur la même ligne, ou sur deux lignes consécutives.
  let codePostal = "";
  let ville = "";
  let adresse = "";

  for (let i = 0; i < lines.length; i++) {
    const ln = lines[i];

    // pattern "97120 PETIT-BOURG" / "75008 PARIS" etc.
    let m = ln.match(/\b(\d{5})\b\s+([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ \-']{2,})/);
    if (m) {
      codePostal = String(m[1] || "").trim();
      ville = String(m[2] || "").trim().replace(/\s*-\s*/g, "-");
      break;
    }

    // pattern sur 2 lignes:
    // ligne i contient CP seul, ligne i+1 contient ville
    m = ln.match(/\b(\d{5})\b/);
    if (m && (i + 1) < lines.length) {
      const next = lines[i + 1];
      const m2 = next.match(/^[A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ \-']{2,}$/);
      if (m2) {
        codePostal = String(m[1] || "").trim();
        ville = String(next || "").trim().replace(/\s*-\s*/g, "-");
        break;
      }
    }
  }

  // Adresse : on reconstitue une mini-adresse depuis les lignes autour du CP
  if (codePostal) {
    const cpIndex = lines.findIndex(l => l.includes(codePostal));
    if (cpIndex > 0) {
      const a = [];
      // On prend jusqu'à 2 lignes avant le CP (souvent rue / complément)
      if (lines[cpIndex - 2]) a.push(lines[cpIndex - 2]);
      if (lines[cpIndex - 1]) a.push(lines[cpIndex - 1]);
      // Et la ligne CP+Ville
      a.push(lines[cpIndex]);
      adresse = a.join(", ").trim().replace(/\s*-\s*/g, "-");
    }
  }

  // Si on a un clientNom, on filtre un peu : si ville trouvée mais aucune trace du clientNom dans la fenêtre, on reste prudent
  const cn = String(clientNom || "").trim().toUpperCase();
  if (cn && start >= 0) {
    const winUpper = windowText.toUpperCase();
    if (winUpper.indexOf(cn) < 0) {
      // On ne bloque pas complètement, mais on évite de retourner une adresse “hors bloc client”
      // => on laisse cp/ville si déjà trouvé (souvent OK), mais on vide adresse.
      adresse = "";
    }
  }

  if (!codePostal && !ville && !adresse) return null;

  return {
    code_postal: codePostal,
    ville: ville,
    adresse: adresse
  };
}


function BM_IAMEMORY_hasHashDocument_(hashDocument) {
  const h = String(hashDocument || "").trim();
  if (!h) return false;

  const ss = SpreadsheetApp.getActiveSpreadsheet();

  const sheetsToCheck = [
    ss.getSheetByName("IA_MEMORY"),
    ss.getSheetByName("IAMemory")
  ].filter(Boolean);

  if (!sheetsToCheck.length) throw new Error("Onglet IA_MEMORY / IAMemory introuvable");

  for (let s = 0; s < sheetsToCheck.length; s++) {
    const sh = sheetsToCheck[s];

    const lastCol = sh.getLastColumn();
    if (lastCol < 1) continue;

    const headers = sh.getRange(1, 1, 1, lastCol).getValues()[0];
    const colIndex = {};
    headers.forEach((hh, i) => colIndex[String(hh || "").trim()] = i + 1);

    const col = colIndex["Hash_Document"];
    if (!col) continue;

    const lastRow = sh.getLastRow();
    if (lastRow < 2) continue;

    const values = sh.getRange(2, col, lastRow - 1, 1).getValues();
    for (let i = 0; i < values.length; i++) {
      if (String(values[i][0] || "").trim() === h) return true;
    }
  }

  return false;
}


function BM_IAMEMORY_hasTemplateSignature_(templateSignature) {
  const sig = String(templateSignature || "").trim();
  if (!sig) return false;

  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // ✅ Priorité: IA_MEMORY (ta fonction append écrit ici)
  // Puis fallback: IAMemory (legacy)
  const sheetsToCheck = [
    ss.getSheetByName("IA_MEMORY"),
    ss.getSheetByName("IAMemory")
  ].filter(Boolean);

  if (!sheetsToCheck.length) throw new Error("Onglet IA_MEMORY / IAMemory introuvable");

  for (let s = 0; s < sheetsToCheck.length; s++) {
    const sh = sheetsToCheck[s];

    const lastCol = sh.getLastColumn();
    if (lastCol < 1) continue;

    const headers = sh.getRange(1, 1, 1, lastCol).getValues()[0];
    const colIndex = {};
    headers.forEach((h, i) => colIndex[String(h || "").trim()] = i + 1);

    const col = colIndex["Template_Signature"];
    if (!col) continue;

    const lastRow = sh.getLastRow();
    if (lastRow < 2) continue;

    const values = sh.getRange(2, col, lastRow - 1, 1).getValues();
    for (let i = 0; i < values.length; i++) {
      if (String(values[i][0] || "").trim() === sig) return true;
    }
  }

  return false;
}


function BM_RESOLVE_CLIENT_ID_FROM_CRM_(clientNom) {
  const name = String(clientNom || "").trim();
  if (!name) return "";

  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sh = ss.getSheetByName("CRM_CLIENTS");
  if (!sh) return "";

  const lastCol = sh.getLastColumn();
  const lastRow = sh.getLastRow();
  if (lastCol < 1 || lastRow < 2) return "";

  const headers = sh.getRange(1, 1, 1, lastCol).getValues()[0];
  const idx = {};
  headers.forEach((h, i) => idx[String(h || "").trim()] = i + 1);

  const colId = idx["Client_ID"];
  const colNom = idx["Nom"];
  if (!colId || !colNom) return "";

  const values = sh.getRange(2, 1, lastRow - 1, lastCol).getValues();
  for (let i = 0; i < values.length; i++) {
    const row = values[i];
    const nom = String(row[colNom - 1] || "").trim();
    if (nom && nom.toUpperCase() === name.toUpperCase()) {
      return String(row[colId - 1] || "").trim();
    }
  }

  return "";
}


// ============================================================================
// STABILISATION A — EXTRACTION DÉTERMINISTE (APPS SCRIPT)
// ============================================================================

/**
 * Extraction minimaliste et déterministe depuis le texte OCR.
 * Objectif : débloquer NOM_FINAL / CHEMIN_FINAL en fournissant :
 * - numero_facture
 * - ht, tva_montant, ttc
 *
 * Règles :
 * - Ne PAS écraser des champs déjà renseignés.
 * - Ne PAS "inventer" : on ne remplit que si motifs forts détectés.
 */

function _BM_extractFromCanonicalFilename_(filename) {
  // Parse strict canonical filenames only:
  // YYYY-MM-DD_FOURNISSEUR_TTC_<montant>EUR_<TYPE>_<NUMERO>.pdf
  // Returns null if not matching or incomplete.
  try {
    var name = String(filename || "").trim();
    name = name.replace(/\.pdf$/i, "");
    // Example: 2026-01-13_PROMOCASH_TTC_593.72EUR_FACTURE_777807
    var m = name.match(/^([0-9]{4}-[0-9]{2}-[0-9]{2})_([^_]+)_TTC_([0-9]+(?:\.[0-9]{2})?)EUR_(FACTURE|TICKET|RECU)(?:_([^_]+))?$/i);
    if (!m) return null;

    var date_doc = m[1];
    var fournisseur = m[2];
    var ttc_point = m[3];
    var type = String(m[4]).toUpperCase();
    var numero = (m[5] != null && String(m[5]).trim() !== "") ? String(m[5]).trim() : "";

    // Convert 593.72 -> 593,72 for sheet/business fields
    var ttc = String(ttc_point).replace(".", ",");
    return { date_doc: date_doc, fournisseur: fournisseur, ttc: ttc, type: type, numero_facture: numero };
  } catch (e) {
    return null;
  }
}

function _BM_extractDeterministicInvoiceDataFromOcrText_(txt) {
  try {
    var s = String(txt || "");
    if (!s) return null;

    // Normaliser espaces
    var flat = s.replace(/\u00A0/g, " ");

    var out = {
      numero_facture: "",
      ht: "",
      tva_montant: "",
      ttc: ""
    };

    // --------
    // Numéro de pièce / facture (PROMOCASH / caisse)
    // Exemple (scan) : "Numéro pièce" puis 6 chiffres.
    // --------
    var mNum = flat.match(/Num[ée]ro\s*pi[èe]ce[\s:\-]*\s*([0-9]{5,})/i);
    if (!mNum) {
      // fallback : "N°" proche de "pièce" (tolérance OCR)
      mNum = flat.match(/pi[èe]ce[\s\S]{0,40}?\b([0-9]{5,})\b/i);
    }
    if (mNum) out.numero_facture = String(mNum[1] || "").trim();

    // --------
    // Totaux (mots-clés forts) : Base HT / Total TVA / Total TTC
    // Exemple : "Base HT 567,00" "Total TVA 26,72" "Total TTC 593,72"
    // --------
    function _normAmount_(raw) {
      var v = String(raw || "").trim();
      if (!v) return "";
      // enlever espaces milliers
      v = v.replace(/\s/g, "");
      // remplacer point décimal par virgule si présent
      v = v.replace(/(\d)\.(\d{2})\b/g, "$1,$2");
      // si format 1.234,56 : enlever points milliers
      v = v.replace(/\.(?=\d{3}(?:\D|$))/g, "");
      // garder uniquement chiffres et virgule
      v = v.replace(/[^0-9,]/g, "");
      // forcer 2 décimales si possible
      var mm = v.match(/^(\d+),(\d{1,2})$/);
      if (mm) {
        var dec = mm[2];
        if (dec.length === 1) dec = dec + "0";
        v = mm[1] + "," + dec;
      }
      return v;
    }

    var mHT = flat.match(/(?:Base\s*HT|Total\s*HT|Montant\s*HT|Net\s*HT)[\s:\-]*([0-9][0-9\s\.,]*[0-9][0-9])/i);
    if (mHT) out.ht = _normAmount_(mHT[1]);

    var mTVA = flat.match(/(?:Total\s*TVA|TVA\s*Totale|Montant\s*TVA)[\s:\-]*([0-9][0-9\s\.,]*[0-9][0-9])/i);
    if (mTVA) out.tva_montant = _normAmount_(mTVA[1]);

    var mTTC = flat.match(/(?:Total\s*(?:TTC|T\.?T\.?C\.?|G[eé]n[eé]ral)|Total\s*(?:A|À)\s*Payer|Montant\s*(?:A|À)\s*Payer|Net\s*(?:A|À)\s*Payer|Net\s*(?:A|À)\s*R[eé]gler|NET\s*(?:A|À)\s*PAYER)[\s:\-]*([0-9][0-9\s\.,]*[0-9][0-9])/i);
    if (mTTC) out.ttc = _normAmount_(mTTC[1]);

    // Si aucun signal fort => null
    var hasAny = Boolean(out.numero_facture || out.ht || out.tva_montant || out.ttc);
    if (!hasAny) return null;

    return out;
  } catch (e) {
    return null;
  }
}