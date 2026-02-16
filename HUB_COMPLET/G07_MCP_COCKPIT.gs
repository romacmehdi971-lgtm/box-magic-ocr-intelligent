/**
 * FILE: 07_MCP_COCKPIT.gs
 * PROJECT: IAPF MEMORY HUB V1
 *
 * Objectif:
 * - Fournir des actions "cockpit" déclenchées depuis le HUB (menus)
 * - Aucun automatique. Aucune écriture destructive.
 * - Exports: ZIP code + XLSX du Sheet dans 09_ARCHIVES.
 *
 * Pré-requis:
 * - Advanced Google Services:
 *   - Drive API (Drive)
 *   - Apps Script API (Script)
 */

var MCP = (function () {

  function _ss() {
    return SpreadsheetApp.getActiveSpreadsheet();
  }

  function _ui() {
    return SpreadsheetApp.getUi();
  }

  function _getSettingsMap_() {
    var sh = _ss().getSheetByName("SETTINGS");
    if (!sh) throw new Error("Sheet SETTINGS introuvable.");
    var values = sh.getDataRange().getValues();
    var map = {};
    for (var i = 1; i < values.length; i++) {
      var k = (values[i][0] || "").toString().trim();
      var v = (values[i][1] || "").toString().trim();
      if (k) map[k] = v;
    }
    return map;
  }

  function _requireSettings_(keys, title) {
    var s = _getSettingsMap_();
    var missing = [];
    keys.forEach(function (k) {
      if (!s[k]) missing.push(k);
    });

    if (missing.length) {
      _ui().alert(
        title || "SETTINGS manquant",
        "Ajoute dans SETTINGS (col A=key, col B=value) :\n- " + missing.join("\n- "),
        _ui().ButtonSet.OK
      );
      return null;
    }
    return s;
  }

  function _getFolderById_(id) {
    return DriveApp.getFolderById(id);
  }

  function _ts_() {
    // YYYYMMDD_HHMMSS
    var d = new Date();
    function pad(n) { return (n < 10 ? "0" : "") + n; }
    return d.getFullYear().toString()
      + pad(d.getMonth() + 1)
      + pad(d.getDate())
      + "_"
      + pad(d.getHours())
      + pad(d.getMinutes())
      + pad(d.getSeconds());
  }

  function _exportSheetXlsxBlob_(spreadsheetId, outName) {
    // Drive API advanced service: Drive.Files.export
    var blob = Drive.Files.export(spreadsheetId, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet");
    blob.setName(outName);
    return blob;
  }

  function _exportAppsScriptProjectZipBlob_(scriptId, zipName, prefixFolder) {
    // Apps Script API advanced service: Script.Projects.getContent
    var content = Script.Projects.getContent(scriptId);
    var files = content.files || [];

    var blobs = [];
    for (var i = 0; i < files.length; i++) {
      var f = files[i];
      var name = f.name || ("FILE_" + i);
      var type = f.type || "SERVER_JS";
      var ext = (type === "JSON") ? ".json" : ".gs";
      var filename = (prefixFolder ? (prefixFolder + "/") : "") + name + ext;
      var source = f.source || "";
      blobs.push(Utilities.newBlob(source, "text/plain", filename));
    }

    var zipBlob = Utilities.zip(blobs, zipName);
    return zipBlob;
  }

  function _zipAll_(blobs, zipName) {
    return Utilities.zip(blobs, zipName);
  }

  function _createFile_(folderId, blob) {
    var folder = _getFolderById_(folderId);
    return folder.createFile(blob);
  }

  return {
    requireSettings: _requireSettings_,
    ts: _ts_,
    exportSheetXlsxBlob: _exportSheetXlsxBlob_,
    exportAppsScriptProjectZipBlob: _exportAppsScriptProjectZipBlob_,
    zipAll: _zipAll_,
    createFile: _createFile_
  };

})();

/** =========================
 *  AUDITS (stubs gouvernés)
 *  ========================= */

function MCP_AUDIT_auditHub() {
  // Ici: soit appel MCP réel (endpoint), soit simple “lanceur”.
  var s = MCP.requireSettings(
    ["mcp_project_id", "mcp_region", "mcp_job_healthcheck"],
    "MCP Cockpit — Settings manquants"
  );
  if (!s) return;

  // Minimal safe: guide utilisateur (sans supposer ton endpoint exact)
  SpreadsheetApp.getUi().alert(
    "Audit HUB",
    "OK: settings MCP présents.\n\nÉtape suivante:\n- Déclencher le job MCP (healthcheck/audit) via ton cockpit MCP.\n- Puis coller le résultat dans MEMORY_LOG si besoin.",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

function MCP_AUDIT_auditBox2026() {
  var s = MCP.requireSettings(
    ["box2026_script_id", "box2026_sheet_id"],
    "MCP Cockpit — Settings manquants"
  );
  if (!s) return;

  SpreadsheetApp.getUi().alert(
    "Audit BOX2026",
    "OK: box2026_script_id + box2026_sheet_id présents.\n\nProchaine étape:\n- Le vrai audit peut être branché sur MCP (endpoint) si tu veux.\n- Sinon, utilise Export BOX pour fournir un paquet complet (code+sheet).",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

function MCP_AUDIT_checkDependenciesCoherence() {
  // Ici tu brancheras ton analyse réelle (DEPENDANCES_SCRIPTS/CARTOGRAPHIE_APPELS).
  SpreadsheetApp.getUi().alert(
    "Cohérence dépendances",
    "Action cockpit prête.\n\nÀ brancher sur:\n- lecture DEPENDANCES_SCRIPTS\n- lecture CARTOGRAPHIE_APPELS\n- détection écarts\n- proposition corrections (sans appliquer automatiquement).",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

/** =========================
 *  EXPORTS (HUB + BOX)
 *  ZIP = code + XLSX sheet
 *  Output dans 09_ARCHIVES (archives_folder_id)
 *  ========================= */

function MCP_EXPORT_exportHubZipAndSheet() {
  var s = MCP.requireSettings(
    ["archives_folder_id"],
    "MCP Cockpit — Settings manquants"
  );
  if (!s) return;

  var ts = MCP.ts();
  var hubScriptId = ScriptApp.getScriptId();
  var hubSheetId = SpreadsheetApp.getActiveSpreadsheet().getId();

  var codeZip = MCP.exportAppsScriptProjectZipBlob(
    hubScriptId,
    "HUB_CODE__" + ts + ".zip",
    "CODE"
  );

  var sheetXlsx = MCP.exportSheetXlsxBlob_(
    hubSheetId,
    "HUB_SHEET__" + ts + ".xlsx"
  );

  // Zip final unique: CODE + XLSX
  var finalZip = MCP.zipAll(
    [
      // On ré-emballe le zip code comme un fichier dans le zip final
      codeZip.setName("HUB_CODE__" + ts + ".zip"),
      sheetXlsx
    ],
    "IAPF_HUB_EXPORT__" + ts + ".zip"
  );

  var f = MCP.createFile(s.archives_folder_id, finalZip);

  SpreadsheetApp.getUi().alert(
    "Export HUB terminé",
    "Fichier créé dans 09_ARCHIVES :\n" + f.getName(),
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

function MCP_EXPORT_exportBoxZipAndSheet() {
  var s = MCP.requireSettings(
    ["archives_folder_id", "box2026_script_id", "box2026_sheet_id"],
    "MCP Cockpit — Settings manquants"
  );
  if (!s) return;

  var ts = MCP.ts();

  var codeZip = MCP.exportAppsScriptProjectZipBlob(
    s.box2026_script_id,
    "BOX2026_CODE__" + ts + ".zip",
    "CODE"
  );

  var sheetXlsx = MCP.exportSheetXlsxBlob_(
    s.box2026_sheet_id,
    "BOX2026_SHEET__" + ts + ".xlsx"
  );

  var finalZip = MCP.zipAll(
    [
      codeZip.setName("BOX2026_CODE__" + ts + ".zip"),
      sheetXlsx
    ],
    "BOX2026_EXPORT__" + ts + ".zip"
  );

  var f = MCP.createFile(s.archives_folder_id, finalZip);

  SpreadsheetApp.getUi().alert(
    "Export BOX2026 terminé",
    "Fichier créé dans 09_ARCHIVES :\n" + f.getName(),
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}
