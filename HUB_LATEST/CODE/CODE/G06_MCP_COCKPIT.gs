// File: /CODE/06_MCP_COCKPIT.gs
//
// MCP Cockpit UI actions from the HUB
// - Exports (HUB + BOX) as: ZIP Apps Script + XLSX Sheet copy
// - Optional: trigger Cloud Run Job "healthcheck" via Run API (if settings present)
// - Guardrails: never write SNAPSHOT_ACTIVE directly, only via snapshot generator

/**
 * ===== Public menu actions =====
 */

function MCP_auditHub() {
  MCP_runHealthcheckOrExplain_("HUB");
}

function MCP_auditBox2026() {
  MCP_runHealthcheckOrExplain_("BOX2026");
}

function MCP_exportHubBundle() {
  const ui = SpreadsheetApp.getUi();
  const archives = MCP_getOrCreateArchivesFolder_();

  const ts = MCP_ts_();
  const ss = MCP_getActiveSS_();

  // 1) Export HUB Apps Script project as ZIP
  const hubZip = MCP_exportBoundScriptAsZip_(archives, "HUB_APPS_SCRIPT_BACKUP", ts);

  // 2) Export HUB Sheet as XLSX
  const hubXlsx = MCP_exportSpreadsheetAsXlsx_(ss.getId(), archives, "HUB_SHEET_EXPORT", ts);

  ui.alert(
    "OK",
    "Export HUB terminé.\n\nZIP: " + hubZip.getName() + "\nXLSX: " + hubXlsx.getName() +
      "\n\nOuvre le dossier ARCHIVES pour télécharger.",
    ui.ButtonSet.OK
  );
}

function MCP_exportBoxBundle() {
  const ui = SpreadsheetApp.getUi();
  const archives = MCP_getOrCreateArchivesFolder_();

  const boxScriptId = MCP_requireSetting_("box2026_script_id", "ID du script Apps Script BOX2026 (Cyril).");
  if (!boxScriptId) return;

  const boxSheetId = MCP_requireSetting_("box2026_sheet_id", "ID de la Google Sheet BOX2026 (Cyril).");
  if (!boxSheetId) return;

  const ts = MCP_ts_();

  // 1) Export BOX Apps Script project as ZIP (via Apps Script API)
  const boxZip = MCP_exportExternalAppsScriptProjectAsZip_(boxScriptId, archives, "BOX2026_APPS_SCRIPT_BACKUP", ts);

  // 2) Export BOX Sheet as XLSX
  const boxXlsx = MCP_exportSpreadsheetAsXlsx_(boxSheetId, archives, "BOX2026_SHEET_EXPORT", ts);

  ui.alert(
    "OK",
    "Export BOX2026 terminé.\n\nZIP: " + boxZip.getName() + "\nXLSX: " + boxXlsx.getName() +
      "\n\nOuvre le dossier ARCHIVES pour télécharger.",
    ui.ButtonSet.OK
  );
}

function MCP_checkDependencies() {
  // Minimal non-destructive placeholder: log + guidance
  const ui = SpreadsheetApp.getUi();

  // Optionnel: tu peux brancher ici une vraie vérif interne (cartographie/dépendances)
  // Pour l’instant on respecte gouvernance: aucun “auto-correct”.
  const msg =
    "Check dépendances (mode gouverné).\n\n" +
    "1) Lance 'Audit complet HUB' (MCP Cockpit)\n" +
    "2) Le rapport MCP doit proposer les corrections\n" +
    "3) Tu valides puis seulement on applique.\n\n" +
    "Aucune écriture automatique sur SNAPSHOT_ACTIVE.";
  ui.alert("MCP Cockpit", msg, ui.ButtonSet.OK);
}

function MCP_uiOpenArchivesFolder() {
  const ui = SpreadsheetApp.getUi();
  const folder = MCP_getOrCreateArchivesFolder_();
  ui.alert("ARCHIVES", "Dossier: " + folder.getUrl(), ui.ButtonSet.OK);
}

/**
 * ===== Cloud Run Job trigger (optional) =====
 * Requires Settings:
 * - mcp_project_id
 * - mcp_region
 * - mcp_job_healthcheck
 *
 * Uses UrlFetchApp + OAuth token.
 */
function MCP_runHealthcheckOrExplain_(scopeLabel) {
  const ui = SpreadsheetApp.getUi();

  const projectId = MCP_getSetting_("mcp_project_id");
  const region = MCP_getSetting_("mcp_region");
  const jobName = MCP_getSetting_("mcp_job_healthcheck");

  if (!projectId || !region || !jobName) {
    ui.alert(
      "MCP Cockpit — Settings manquants",
      "Pour déclencher l'audit via le HUB, renseigne dans SETTINGS :\n" +
        "- mcp_project_id\n- mcp_region\n- mcp_job_healthcheck\n\n" +
        "Ensuite relance: MCP Cockpit > Audit complet HUB / Audit BOX2026.",
      ui.ButtonSet.OK
    );
    return;
  }

  // Cloud Run Jobs v2 API
  const url = "https://run.googleapis.com/v2/projects/" + encodeURIComponent(projectId) +
              "/locations/" + encodeURIComponent(region) +
              "/jobs/" + encodeURIComponent(jobName) + ":run";

  const token = ScriptApp.getOAuthToken();
  const payload = {}; // No overrides for now (keep governance tight)

  const resp = UrlFetchApp.fetch(url, {
    method: "post",
    contentType: "application/json",
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
    headers: { Authorization: "Bearer " + token }
  });

  const code = resp.getResponseCode();
  const body = resp.getContentText() || "";

  if (code >= 200 && code < 300) {
    ui.alert(
      "OK",
      "Audit déclenché (" + scopeLabel + ").\n\n" +
        "Va voir les logs Cloud Run Job (Observabilité) + le report généré dans Drive (si ton job l’écrit).",
      ui.ButtonSet.OK
    );
    return;
  }

  ui.alert(
    "Erreur Cloud Run Job",
    "HTTP " + code + "\n\n" +
      "Causes fréquentes:\n" +
      "- Scope OAuth insuffisant\n" +
      "- Permission run.jobs.run manquante pour le compte Apps Script\n" +
      "- Nom job / region / project incorrect\n\n" +
      "Réponse:\n" + body.slice(0, 1500),
    ui.ButtonSet.OK
  );
}

/**
 * ===== Exports helpers =====
 */

/**
 * Export bound script (the HUB script) as ZIP into Drive folder.
 * Uses Apps Script API: projects.getContent (requires Advanced service or REST with OAuth).
 */
function MCP_exportBoundScriptAsZip_(targetFolder, prefix, ts) {
  const scriptId = ScriptApp.getScriptId();
  return MCP_exportExternalAppsScriptProjectAsZip_(scriptId, targetFolder, prefix, ts);
}

/**
 * Export any Apps Script project as ZIP using Apps Script API (REST).
 * Note: this exports the *sources* into a ZIP file generated here.
 */
function MCP_exportExternalAppsScriptProjectAsZip_(scriptId, targetFolder, prefix, ts) {
  const token = ScriptApp.getOAuthToken();
  const url = "https://script.googleapis.com/v1/projects/" + encodeURIComponent(scriptId) + "/content";

  const resp = UrlFetchApp.fetch(url, {
    method: "get",
    muteHttpExceptions: true,
    headers: { Authorization: "Bearer " + token }
  });

  const code = resp.getResponseCode();
  if (code < 200 || code >= 300) {
    throw new Error("Apps Script API error HTTP " + code + " => " + resp.getContentText());
  }

  const json = JSON.parse(resp.getContentText());
  const files = (json.files || []);

  // Create a ZIP in-memory
  const blobs = [];
  files.forEach(function(f) {
    const name = (f.name || "file") + "." + (f.type || "gs");
    const source = f.source || "";
    blobs.push(Utilities.newBlob(source, "text/plain", name));
  });

  const zipBlob = Utilities.zip(blobs, prefix + "_" + ts + ".zip");
  return targetFolder.createFile(zipBlob);
}

/**
 * Export a spreadsheet as XLSX into Drive folder.
 */
function MCP_exportSpreadsheetAsXlsx_(spreadsheetId, targetFolder, prefix, ts) {
  const token = ScriptApp.getOAuthToken();
  const url =
    "https://www.googleapis.com/drive/v3/files/" + encodeURIComponent(spreadsheetId) +
    "/export?mimeType=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

  const resp = UrlFetchApp.fetch(url, {
    method: "get",
    muteHttpExceptions: true,
    headers: { Authorization: "Bearer " + token }
  });

  const code = resp.getResponseCode();
  if (code < 200 || code >= 300) {
    throw new Error("Drive export error HTTP " + code + " => " + resp.getContentText());
  }

  const blob = resp.getBlob().setName(prefix + "_" + ts + ".xlsx");
  return targetFolder.createFile(blob);
}

/**
 * ===== Settings & folders =====
 */

function MCP_getOrCreateArchivesFolder_() {
  const ss = MCP_getActiveSS_();
  const archivesId = MCP_getSetting_("archives_folder_id");

  if (archivesId) {
    return DriveApp.getFolderById(archivesId);
  }

  // Fallback: create under memory_root_folder_id if present
  const rootId = MCP_getSetting_("memory_root_folder_id");
  if (!rootId) {
    // Create the key and ask user to fill it (governance)
    MCP_ensureSettingKeyExists_("archives_folder_id", "ID dossier Drive IA Process Factory / 09_ARCHIVES");
    const ui = SpreadsheetApp.getUi();
    ui.alert(
      "SETTINGS manquant",
      "Ajoute la clé SETTINGS:archives_folder_id = <ID dossier Drive IA Process Factory / 09_ARCHIVES>.\n" +
        "Puis relance l’export.",
      ui.ButtonSet.OK
    );
    throw new Error("Missing SETTINGS archives_folder_id");
  }

  const root = DriveApp.getFolderById(rootId);
  // Create / reuse "09_ARCHIVES"
  const it = root.getFoldersByName("09_ARCHIVES");
  const folder = it.hasNext() ? it.next() : root.createFolder("09_ARCHIVES");

  // Persist it for next time
  MCP_setSetting_("archives_folder_id", folder.getId(), "Auto-created under memory_root_folder_id");
  return folder;
}

function MCP_requireSetting_(key, notes) {
  const v = MCP_getSetting_(key);
  if (v) return v;

  MCP_ensureSettingKeyExists_(key, notes || "");
  SpreadsheetApp.getUi().alert(
    "SETTINGS manquant",
    "Ajoute la clé SETTINGS:" + key + " = <valeur>.\n" + (notes ? ("\n" + notes) : ""),
    SpreadsheetApp.getUi().ButtonSet.OK
  );
  return null;
}

function MCP_getSetting_(key) {
  const ss = MCP_getActiveSS_();
  const sh = ss.getSheetByName("SETTINGS");
  if (!sh) return "";

  const values = sh.getDataRange().getValues();
  // Expect header: key | value | notes
  for (let i = 1; i < values.length; i++) {
    const k = String(values[i][0] || "").trim();
    if (k === key) return String(values[i][1] || "").trim();
  }
  return "";
}

function MCP_setSetting_(key, value, notes) {
  const ss = MCP_getActiveSS_();
  const sh = ss.getSheetByName("SETTINGS");
  if (!sh) throw new Error("Missing SETTINGS sheet");

  const values = sh.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    const k = String(values[i][0] || "").trim();
    if (k === key) {
      sh.getRange(i + 1, 2).setValue(value);
      if (notes !== undefined) sh.getRange(i + 1, 3).setValue(notes);
      return;
    }
  }

  sh.appendRow([key, value, notes || ""]);
}

function MCP_ensureSettingKeyExists_(key, notes) {
  const ss = MCP_getActiveSS_();
  let sh = ss.getSheetByName("SETTINGS");
  if (!sh) {
    sh = ss.insertSheet("SETTINGS");
    sh.getRange(1, 1, 1, 3).setValues([["key", "value", "notes"]]);
  }

  const values = sh.getDataRange().getValues();
  for (let i = 1; i < values.length; i++) {
    const k = String(values[i][0] || "").trim();
    if (k === key) return;
  }
  sh.appendRow([key, "", notes || ""]);
}

function MCP_getActiveSS_() {
  // Prefer your existing helper if present
  if (typeof IAPF_getActiveSS_ === "function") return IAPF_getActiveSS_();
  return SpreadsheetApp.getActiveSpreadsheet();
}

function MCP_ts_() {
  const d = new Date();
  const pad = (n) => (n < 10 ? "0" + n : "" + n);
  return (
    d.getFullYear() +
    pad(d.getMonth() + 1) +
    pad(d.getDate()) +
    "_" +
    pad(d.getHours()) +
    pad(d.getMinutes()) +
    pad(d.getSeconds())
  );
}
