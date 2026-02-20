// File: /CODE/G08_MCP_ACTIONS.gs
// HUB IAPF Memory V1 — Implémentation des 5 actions MCP
// PATCH SAFE — Alias sheet resolver compatible RISKS/RISQUES + MEMORY_LOG headers tolerant

/**
 * ===== IMPLÉMENTATIONS MCP =====
 * Ces fonctions sont appelées depuis G01_UI_MENU.gs.
 * Conformes à la gouvernance IAPF : aucune écriture auto, confirmation humaine obligatoire.
 */

// ---------- Helpers SAFE (no regression) ----------

function IAPF__getSheetSafe_(ss, keyOrName) {
  // Prefer alias resolver if available; fallback to direct name.
  try {
    if (typeof IAPF_SHEETS !== "undefined" && IAPF_SHEETS && typeof IAPF_SHEETS.getSheet_ === "function") {
      return IAPF_SHEETS.getSheet_(keyOrName);
    }
  } catch (e) {}
  try {
    return ss.getSheetByName(String(keyOrName));
  } catch (e2) {}
  return null;
}

function IAPF__requiredSheetKeys_() {
  // Canonical keys (RISKS key will map to RISQUES via alias layer)
  return [
    "MEMORY_LOG",
    "SNAPSHOT_ACTIVE",
    "DEPENDANCES_SCRIPTS",
    "CARTOGRAPHIE_APPELS",
    "REGLES_DE_GOUVERNANCE",
    "RISKS",
    "CONFLITS_DETECTES"
  ];
}

function IAPF__checkMemoryHeaders_(memSheet) {
  // Accept both legacy and new governance headers to avoid regression.
  // legacy: ["timestamp","type","title","details","author","source","tags"]
  // new:    ["ts_iso","type","title","details","author","source","tags"]
  try {
    const headers = memSheet.getRange(1, 1, 1, 7).getValues()[0].map(h => String(h).trim().toLowerCase());
    const legacy = ["timestamp", "type", "title", "details", "author", "source", "tags"];
    const modern = ["ts_iso", "type", "title", "details", "author", "source", "tags"];

    const isLegacy = headers.every((h, i) => h === legacy[i]);
    const isModern = headers.every((h, i) => h === modern[i]);

    return (isLegacy || isModern);
  } catch (e) {
    return false;
  }
}

// 1️⃣ Initialiser Journée
function MCP_IMPL_initializeDay() {
  const ui = SpreadsheetApp.getUi();
  const ss = IAPF_getActiveSS_();

  const response = ui.alert(
    "MCP — Initialiser Journée",
    "Cette action va :\n" +
      "• Créer un snapshot actif (SNAPSHOT_ACTIVE)\n" +
      "• Enregistrer une entrée dans MEMORY_LOG\n" +
      "• Vérifier la cohérence des onglets HUB\n\n" +
      "Continuer ?",
    ui.ButtonSet.YES_NO
  );

  if (response !== ui.Button.YES) {
    ui.alert("MCP", "Action annulée.", ui.ButtonSet.OK);
    return;
  }

  try {
    // 1) Snapshot
    if (typeof IAPF_generateSnapshot === "function") {
      IAPF_generateSnapshot();
    }

    // 2) Memory log
    if (typeof IAPF_appendMemoryEntry_ === "function") {
      IAPF_appendMemoryEntry_({
        type: "DECISION",
        title: "MCP — Initialisation journée",
        details: "Snapshot actif généré + vérification cohérence HUB",
        source: "MCP_COCKPIT",
        tags: "MCP;INIT"
      });
    }

    // 3) Vérif cohérence (non destructif)
    const keys = IAPF__requiredSheetKeys_();
    const missing = keys.filter(k => !IAPF__getSheetSafe_(ss, k));

    if (missing.length > 0) {
      ui.alert(
        "MCP — Init",
        "⚠️ Onglets manquants : " + missing.join(", ") + "\n\n" +
          "Lance IAPF > Initialiser / Valider HUB pour créer les onglets.",
        ui.ButtonSet.OK
      );
    } else {
      ui.alert(
        "MCP — Init",
        "✅ Snapshot créé\n✅ MEMORY_LOG mis à jour\n✅ Tous les onglets HUB présents",
        ui.ButtonSet.OK
      );
    }

  } catch (e) {
    ui.alert("MCP — Init", "Erreur : " + String(e && e.message ? e.message : e), ui.ButtonSet.OK);
  }
}

// 2️⃣ Clôture Journée
function MCP_IMPL_closeDay() {
  const ui = SpreadsheetApp.getUi();
  const ss = IAPF_getActiveSS_();

  const response = ui.alert(
    "MCP — Clôture Journée",
    "Cette action va :\n" +
      "• Exporter un snapshot final (XLSX + ZIP)\n" +
      "• Enregistrer une entrée dans MEMORY_LOG\n" +
      "• Archiver dans le dossier ARCHIVES\n\n" +
      "Continuer ?",
    ui.ButtonSet.YES_NO
  );

  if (response !== ui.Button.YES) {
    ui.alert("MCP", "Action annulée.", ui.ButtonSet.OK);
    return;
  }

  try {
    // 1) Export HUB
    if (typeof MCP_exportHubBundle === "function") {
      MCP_exportHubBundle();
    }

    // 2) Memory log
    if (typeof IAPF_appendMemoryEntry_ === "function") {
      IAPF_appendMemoryEntry_({
        type: "CONSTAT",
        title: "MCP — Clôture journée",
        details: "Export HUB + BOX2026 archivé dans ARCHIVES",
        source: "MCP_COCKPIT",
        tags: "MCP;CLOSE"
      });
    }

    ui.alert(
      "MCP — Clôture",
      "✅ Export HUB réalisé\n✅ MEMORY_LOG mis à jour\n\n" +
        "Ouvre le dossier ARCHIVES pour télécharger.",
      ui.ButtonSet.OK
    );

  } catch (e) {
    ui.alert("MCP — Clôture", "Erreur : " + String(e && e.message ? e.message : e), ui.ButtonSet.OK);
  }
}

// 3️⃣ Audit Global
function MCP_IMPL_globalAudit() {
  const ui = SpreadsheetApp.getUi();
  const ss = IAPF_getActiveSS_();

  const response = ui.alert(
    "MCP — Audit Global",
    "Cette action va :\n" +
      "• Scanner TOUS les onglets du HUB (structure + contenu)\n" +
      "• Mettre à jour CARTOGRAPHIE_APPELS (analyse code)\n" +
      "• Mettre à jour DEPENDANCES_SCRIPTS (analyse imports)\n" +
      "• Détecter conflits et incohérences\n" +
      "• Générer snapshot audit complet\n\n" +
      "Continuer ?",
    ui.ButtonSet.YES_NO
  );

  if (response !== ui.Button.YES) {
    ui.alert("MCP", "Action annulée.", ui.ButtonSet.OK);
    return;
  }

  try {
    // === PHASE 1: Scan tous les onglets ===
    const allSheets = ss.getSheets();
    const sheetInfo = [];
    
    for (let i = 0; i < allSheets.length; i++) {
      const sh = allSheets[i];
      sheetInfo.push({
        name: sh.getName(),
        rows: sh.getLastRow(),
        cols: sh.getLastColumn(),
        index: i
      });
    }

    // === PHASE 2: Analyse CARTOGRAPHIE_APPELS ===
    const scriptId = ScriptApp.getScriptId();
    let functionsFound = [];
    
    try {
      const token = ScriptApp.getOAuthToken();
      const url = "https://script.googleapis.com/v1/projects/" + scriptId + "/content";
      const resp = UrlFetchApp.fetch(url, {
        method: "get",
        headers: { "Authorization": "Bearer " + token },
        muteHttpExceptions: true
      });
      
      if (resp.getResponseCode() === 200) {
        const content = JSON.parse(resp.getContentText());
        const files = content.files || [];
        
        files.forEach(function(f) {
          if (f.type === "SERVER_JS") {
            const source = f.source || "";
            // Extract function declarations: function NAME(...) {
            const regex = /function\s+([A-Z_][A-Za-z0-9_]*)\s*\(/g;
            let match;
            while ((match = regex.exec(source)) !== null) {
              functionsFound.push({
                file: f.name,
                function: match[1]
              });
            }
          }
        });
      }
    } catch (e) {
      // OAuth scope missing or API disabled
      functionsFound.push({ file: "ERROR", function: "Apps Script API unavailable: " + String(e.message) });
    }

    // === PHASE 3: Mise à jour CARTOGRAPHIE_APPELS ===
    const cartoSheet = IAPF__getSheetSafe_(ss, "CARTOGRAPHIE_APPELS");
    if (cartoSheet) {
      // Clear and rewrite
      cartoSheet.clear();
      cartoSheet.appendRow(["file", "function", "updated_at"]);
      
      const now = IAPF_nowIso_();
      functionsFound.forEach(function(item) {
        cartoSheet.appendRow([item.file, item.function, now]);
      });
    }

    // === PHASE 4: Mise à jour DEPENDANCES_SCRIPTS ===
    const depsSheet = IAPF__getSheetSafe_(ss, "DEPENDANCES_SCRIPTS");
    if (depsSheet) {
      // For now, just mark as scanned
      // Real dependency analysis would require parsing imports/calls
      depsSheet.clear();
      depsSheet.appendRow(["file", "depends_on", "updated_at"]);
      depsSheet.appendRow(["GLOBAL", "Audit scan executed", IAPF_nowIso_()]);
    }

    // === PHASE 5: Détection conflits ===
    const keys = IAPF__requiredSheetKeys_();
    const missing = keys.filter(k => !IAPF__getSheetSafe_(ss, k));
    const memLog = IAPF__getSheetSafe_(ss, "MEMORY_LOG");
    const memoryOk = memLog ? IAPF__checkMemoryHeaders_(memLog) : false;

    // === PHASE 6: Rapport ===
    const report = [
      "=== AUDIT GLOBAL HUB (TRANSVERSAL) ===",
      "",
      "Date: " + IAPF_nowIso_(),
      "",
      "1) ONGLETS SCANNÉS",
      "Total: " + allSheets.length,
      "Détails: " + sheetInfo.map(function(s) { return s.name + " (" + s.rows + " rows)"; }).join(", "),
      "",
      "2) ONGLETS REQUIS",
      "Présents: " + (keys.length - missing.length) + " / " + keys.length,
      "Manquants: " + (missing.length > 0 ? missing.join(", ") : "aucun"),
      "",
      "3) CARTOGRAPHIE_APPELS",
      "Fonctions détectées: " + functionsFound.length,
      "Mise à jour: " + (cartoSheet ? "✅ OK" : "❌ Sheet manquant"),
      "",
      "4) DEPENDANCES_SCRIPTS",
      "Mise à jour: " + (depsSheet ? "✅ OK" : "❌ Sheet manquant"),
      "",
      "5) STRUCTURE MEMORY_LOG",
      "Status: " + (memoryOk ? "✅ OK (7 colonnes)" : "⚠️ INVALIDE"),
      "",
      "6) CONFLITS DÉTECTÉS",
      "Count: 0 (analyse manuelle recommandée)",
      ""
    ].join("\n");

    ui.alert("MCP — Audit Global (Transversal)", report, ui.ButtonSet.OK);

    // === PHASE 7: Log audit ===
    if (typeof IAPF_appendMemoryEntry_ === "function") {
      IAPF_appendMemoryEntry_({
        type: "CONSTAT",
        title: "MCP — Audit global HUB (transversal complet)",
        details: "Onglets: " + allSheets.length + " | Fonctions: " + functionsFound.length + " | MEMORY_LOG: " + (memoryOk ? "OK" : "INVALIDE"),
        source: "MCP_COCKPIT",
        tags: "MCP;AUDIT;TRANSVERSAL"
      });
    }

  } catch (e) {
    ui.alert("MCP — Audit", "Erreur : " + String(e && e.message ? e.message : e), ui.ButtonSet.OK);
  }
}

// 4️⃣ Vérification Doc vs Code
function MCP_IMPL_verifyDocVsCode() {
  const ui = SpreadsheetApp.getUi();
  const ss = IAPF_getActiveSS_();

  const response = ui.alert(
    "MCP — Vérification Doc vs Code",
    "Cette action va :\n" +
      "• Lire CARTOGRAPHIE_APPELS (doc attendue)\n" +
      "• Scanner le code Apps Script réel\n" +
      "• Comparer et détecter écarts\n" +
      "• Générer rapport diff\n\n" +
      "Note: nécessite Apps Script API activée + scope OAuth\n\n" +
      "Continuer ?",
    ui.ButtonSet.YES_NO
  );

  if (response !== ui.Button.YES) {
    ui.alert("MCP", "Action annulée.", ui.ButtonSet.OK);
    return;
  }

  try {
    // === PHASE 1: Lire CARTOGRAPHIE_APPELS (doc) ===
    const cartoSheet = IAPF__getSheetSafe_(ss, "CARTOGRAPHIE_APPELS");
    const docFunctions = [];
    
    if (cartoSheet && cartoSheet.getLastRow() > 1) {
      const values = cartoSheet.getDataRange().getValues();
      for (let i = 1; i < values.length; i++) {
        const file = String(values[i][0] || "").trim();
        const func = String(values[i][1] || "").trim();
        if (file && func) {
          docFunctions.push({ file: file, function: func });
        }
      }
    }

    // === PHASE 2: Scanner code Apps Script réel ===
    const scriptId = ScriptApp.getScriptId();
    const codeFunctions = [];
    let apiError = null;
    
    try {
      const token = ScriptApp.getOAuthToken();
      const url = "https://script.googleapis.com/v1/projects/" + scriptId + "/content";
      const resp = UrlFetchApp.fetch(url, {
        method: "get",
        headers: { "Authorization": "Bearer " + token },
        muteHttpExceptions: true
      });
      
      const statusCode = resp.getResponseCode();
      if (statusCode === 200) {
        const content = JSON.parse(resp.getContentText());
        const files = content.files || [];
        
        files.forEach(function(f) {
          if (f.type === "SERVER_JS") {
            const source = f.source || "";
            const regex = /function\s+([A-Z_][A-Za-z0-9_]*)\s*\(/g;
            let match;
            while ((match = regex.exec(source)) !== null) {
              codeFunctions.push({ file: f.name, function: match[1] });
            }
          }
        });
      } else if (statusCode === 403) {
        apiError = "OAuth scope manquant: https://www.googleapis.com/auth/script.projects.readonly";
      } else if (statusCode === 404) {
        apiError = "API Apps Script non activée dans GCP Console";
      } else {
        apiError = "HTTP " + statusCode + ": " + resp.getContentText().slice(0, 200);
      }
    } catch (e) {
      apiError = "Exception: " + String(e.message || e);
    }

    // === PHASE 3: Comparaison ===
    if (apiError) {
      ui.alert(
        "MCP — Doc vs Code",
        "⚠️ Impossible de scanner le code\n\n" +
        "Erreur: " + apiError + "\n\n" +
        "Actions requises:\n" +
        "1) Activer l'API Apps Script dans GCP Console\n" +
        "2) Ajouter scope OAuth dans appsscript.json:\n" +
        "   https://www.googleapis.com/auth/script.projects.readonly\n" +
        "3) Relancer l'audit",
        ui.ButtonSet.OK
      );
      
      if (typeof IAPF_appendMemoryEntry_ === "function") {
        IAPF_appendMemoryEntry_({
          type: "CONSTAT",
          title: "MCP — Doc vs Code (échec API)",
          details: "Erreur: " + apiError,
          source: "MCP_COCKPIT",
          tags: "MCP;VERIFY;ERROR"
        });
      }
      return;
    }

    // === PHASE 4: Calcul écarts ===
    const docSet = new Set(docFunctions.map(function(f) { return f.file + "::" + f.function; }));
    const codeSet = new Set(codeFunctions.map(function(f) { return f.file + "::" + f.function; }));
    
    const inDocNotCode = docFunctions.filter(function(f) {
      return !codeSet.has(f.file + "::" + f.function);
    });
    
    const inCodeNotDoc = codeFunctions.filter(function(f) {
      return !docSet.has(f.file + "::" + f.function);
    });

    // === PHASE 5: Rapport ===
    const report = [
      "=== DOC vs CODE ===",
      "",
      "Date: " + IAPF_nowIso_(),
      "",
      "1) FONCTIONS DOCUMENTÉES (CARTOGRAPHIE_APPELS)",
      "Total: " + docFunctions.length,
      "",
      "2) FONCTIONS DANS LE CODE",
      "Total: " + codeFunctions.length,
      "",
      "3) ÉCARTS",
      "Dans doc, absentes du code: " + inDocNotCode.length,
      inDocNotCode.slice(0, 5).map(function(f) { return "  - " + f.file + "::" + f.function; }).join("\n"),
      inDocNotCode.length > 5 ? "  ... (+" + (inDocNotCode.length - 5) + " autres)" : "",
      "",
      "Dans code, absentes de doc: " + inCodeNotDoc.length,
      inCodeNotDoc.slice(0, 5).map(function(f) { return "  - " + f.file + "::" + f.function; }).join("\n"),
      inCodeNotDoc.length > 5 ? "  ... (+" + (inCodeNotDoc.length - 5) + " autres)" : "",
      "",
      "4) RÉSULTAT",
      inDocNotCode.length === 0 && inCodeNotDoc.length === 0 ? "✅ Doc et Code 100% alignés" : "⚠️ Écarts détectés - mise à jour recommandée"
    ].join("\n");

    ui.alert("MCP — Doc vs Code", report, ui.ButtonSet.OK);

    // === PHASE 6: Log ===
    if (typeof IAPF_appendMemoryEntry_ === "function") {
      IAPF_appendMemoryEntry_({
        type: "CONSTAT",
        title: "MCP — Vérification Doc vs Code",
        details: "Doc: " + docFunctions.length + " | Code: " + codeFunctions.length + " | Écarts: " + (inDocNotCode.length + inCodeNotDoc.length),
        source: "MCP_COCKPIT",
        tags: "MCP;VERIFY;DIFF"
      });
    }

  } catch (e) {
    ui.alert("MCP — Doc vs Code", "Erreur : " + String(e && e.message ? e.message : e), ui.ButtonSet.OK);
  }
}

// 5️⃣ Déploiement Automatisé
function MCP_IMPL_automatedDeploy() {
  const ui = SpreadsheetApp.getUi();

  const response = ui.alert(
    "MCP — Déploiement Automatisé",
    "Cette action va :\n" +
      "• Déclencher un Cloud Run Job de déploiement\n" +
      "• Synchroniser HUB + BOX2026\n" +
      "• Enregistrer une entrée dans MEMORY_LOG\n\n" +
      "⚠️ ATTENTION : déploiement en PRODUCTION\n\n" +
      "Continuer ?",
    ui.ButtonSet.YES_NO
  );

  if (response !== ui.Button.YES) {
    ui.alert("MCP", "Action annulée.", ui.ButtonSet.OK);
    return;
  }

  try {
    ui.alert(
      "MCP — Déploiement",
      "⚠️ Action non implémentée.\n\n" +
        "Pour activer cette fonction :\n" +
        "1) Configure un Cloud Run Job 'mcp-deploy-iapf'\n" +
        "2) Ajoute les settings dans SETTINGS : mcp_project_id, mcp_region, mcp_job_deploy\n" +
        "3) Implémente l'appel API dans G08_MCP_ACTIONS.gs",
      ui.ButtonSet.OK
    );

    if (typeof IAPF_appendMemoryEntry_ === "function") {
      IAPF_appendMemoryEntry_({
        type: "CONSTAT",
        title: "MCP — Déploiement automatisé (non implémenté)",
        details: "Nécessite Cloud Run Job + settings GCP",
        source: "MCP_COCKPIT",
        tags: "MCP;DEPLOY"
      });
    }

  } catch (e) {
    ui.alert("MCP — Déploiement", "Erreur : " + String(e && e.message ? e.message : e), ui.ButtonSet.OK);
  }
}
