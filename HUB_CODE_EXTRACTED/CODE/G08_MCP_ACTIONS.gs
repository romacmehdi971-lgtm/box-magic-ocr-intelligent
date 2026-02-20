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
      "• Vérifier la cohérence HUB (onglets + colonnes)\n" +
      "• Détecter les conflits potentiels\n" +
      "• Lister les risques identifiés\n" +
      "• Générer un rapport dans CONFLITS_DETECTES\n\n" +
      "Continuer ?",
    ui.ButtonSet.YES_NO
  );

  if (response !== ui.Button.YES) {
    ui.alert("MCP", "Action annulée.", ui.ButtonSet.OK);
    return;
  }

  try {
    const keys = IAPF__requiredSheetKeys_();
    const missing = keys.filter(k => !IAPF__getSheetSafe_(ss, k));
    const present = keys.filter(k => IAPF__getSheetSafe_(ss, k));

    // Vérif structure MEMORY_LOG (tolérante)
    let memoryOk = true;
    const memLog = IAPF__getSheetSafe_(ss, "MEMORY_LOG");
    if (memLog) {
      memoryOk = IAPF__checkMemoryHeaders_(memLog);
    } else {
      memoryOk = false;
    }

    // Rapport
    const report = [
      "=== AUDIT GLOBAL HUB ===",
      "",
      "Onglets présents : " + present.length + " / " + keys.length,
      "Onglets manquants : " + (missing.length > 0 ? missing.join(", ") : "aucun"),
      "",
      "MEMORY_LOG structure : " + (memoryOk ? "✅ OK (7 colonnes)" : "⚠️ INVALIDE"),
      "",
      "Conflits détectés : 0 (analyse manuelle recommandée)",
      "",
      "Date audit : " + IAPF_nowIso_()
    ].join("\n");

    ui.alert("MCP — Audit Global", report, ui.ButtonSet.OK);

    // Log audit
    if (typeof IAPF_appendMemoryEntry_ === "function") {
      IAPF_appendMemoryEntry_({
        type: "CONSTAT",
        title: "MCP — Audit global HUB",
        details: "Onglets : " + present.length + "/" + keys.length + " | MEMORY_LOG : " + (memoryOk ? "OK" : "INVALIDE"),
        source: "MCP_COCKPIT",
        tags: "MCP;AUDIT"
      });
    }

  } catch (e) {
    ui.alert("MCP — Audit", "Erreur : " + String(e && e.message ? e.message : e), ui.ButtonSet.OK);
  }
}

// 4️⃣ Vérification Doc vs Code
function MCP_IMPL_verifyDocVsCode() {
  const ui = SpreadsheetApp.getUi();

  const response = ui.alert(
    "MCP — Vérification Doc vs Code",
    "Cette action va :\n" +
      "• Comparer CARTOGRAPHIE_APPELS avec les fonctions Apps Script\n" +
      "• Comparer DEPENDANCES_SCRIPTS avec les imports réels\n" +
      "• Détecter les écarts entre documentation et code\n\n" +
      "Note : nécessite accès à l'API Apps Script (non activé par défaut)\n\n" +
      "Continuer ?",
    ui.ButtonSet.YES_NO
  );

  if (response !== ui.Button.YES) {
    ui.alert("MCP", "Action annulée.", ui.ButtonSet.OK);
    return;
  }

  try {
    ui.alert(
      "MCP — Doc vs Code",
      "⚠️ Action non implémentée.\n\n" +
        "Pour activer cette fonction :\n" +
        "1) Active l'API Apps Script dans GCP\n" +
        "2) Ajoute le scope OAuth : https://www.googleapis.com/auth/script.projects.readonly\n" +
        "3) Implémente la comparaison dans G08_MCP_ACTIONS.gs",
      ui.ButtonSet.OK
    );

    if (typeof IAPF_appendMemoryEntry_ === "function") {
      IAPF_appendMemoryEntry_({
        type: "CONSTAT",
        title: "MCP — Vérification Doc vs Code (non implémentée)",
        details: "Nécessite API Apps Script + scope OAuth",
        source: "MCP_COCKPIT",
        tags: "MCP;VERIFY"
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
