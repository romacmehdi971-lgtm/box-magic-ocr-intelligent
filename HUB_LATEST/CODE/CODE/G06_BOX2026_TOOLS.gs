// File: /CODE/06_BOX2026_TOOLS.gs
//
// BOX2026 helpers for HUB UI.
// Governance: Drive-only read actions + safe link display.
// No write to SNAPSHOT_ACTIVE here. No destructive operations.

function IAPF_box2026OpenBackupFolder() {
  const ui = SpreadsheetApp.getUi();
  const folderId = IAPF_getSettingValue_("box2026_backup_folder_id");
  if (!folderId) {
    ui.alert(
      "SETTINGS manquant",
      "Ajoute la clé SETTINGS: box2026_backup_folder_id = <ID dossier Drive backups BOX2026>.",
      ui.ButtonSet.OK
    );
    return;
  }

  const url = "https://drive.google.com/drive/folders/" + encodeURIComponent(folderId);
  IAPF_uiShowLink_("BOX2026 — Dossier BACKUP", url);
}

function IAPF_box2026DownloadLatestZip() {
  const ui = SpreadsheetApp.getUi();
  const folderId = IAPF_getSettingValue_("box2026_backup_folder_id");
  if (!folderId) {
    ui.alert(
      "SETTINGS manquant",
      "Ajoute la clé SETTINGS: box2026_backup_folder_id = <ID dossier Drive backups BOX2026>.",
      ui.ButtonSet.OK
    );
    return;
  }

  let folder;
  try {
    folder = DriveApp.getFolderById(folderId);
  } catch (e) {
    ui.alert("Erreur", "Impossible d'ouvrir le dossier Drive: " + String(e), ui.ButtonSet.OK);
    return;
  }

  // Heuristique: on prend le ZIP le plus récent dans ce dossier.
  // Si tu veux filtrer par préfixe exact (ex: APPS_SCRIPT_BACKUP_), on le fera ensuite.
  const files = folder.getFilesByType(MimeType.ZIP);
  let latest = null;

  while (files.hasNext()) {
    const f = files.next();
    if (!latest) {
      latest = f;
      continue;
    }
    if (f.getDateCreated().getTime() > latest.getDateCreated().getTime()) {
      latest = f;
    }
  }

  if (!latest) {
    ui.alert(
      "Aucun ZIP trouvé",
      "Aucun fichier .zip trouvé dans le dossier. Lance d'abord 99_BACKUP_ALL_BOX2026 côté projet BOX2026 pour générer le ZIP.",
      ui.ButtonSet.OK
    );
    return;
  }

  // Lien direct Drive (download au clic via UI Drive).
  const url = "https://drive.google.com/file/d/" + encodeURIComponent(latest.getId()) + "/view";
  IAPF_uiShowLink_("BOX2026 — Dernier ZIP Apps Script", url);
}

/** Minimal SETTINGS getter: reads key/value from SETTINGS sheet (columns A/B). */
function IAPF_getSettingValue_(key) {
  const ss = IAPF_getActiveSS_();
  const sh = ss.getSheetByName(IAPF.SETTINGS_SHEET);
  if (!sh) return "";

  const values = sh.getDataRange().getValues();
  // Expect header row: key | value | notes
  for (let i = 1; i < values.length; i++) {
    const k = String(values[i][0] || "").trim();
    if (k === key) return String(values[i][1] || "").trim();
  }
  return "";
}

/** Shows a clickable link via HtmlService dialog (alerts are not clickable). */
function IAPF_uiShowLink_(title, url) {
  const html = HtmlService.createHtmlOutput(
    '<div style="font-family:Arial,sans-serif;font-size:13px">' +
      '<p><b>' + IAPF_escapeHtml_(title) + '</b></p>' +
      '<p><a href="' + IAPF_escapeHtml_(url) + '" target="_blank" rel="noopener">Ouvrir / Télécharger</a></p>' +
      '<p style="color:#666">Si ton navigateur bloque les popups, autorise-les pour Google Sheets.</p>' +
    '</div>'
  ).setWidth(420).setHeight(180);

  SpreadsheetApp.getUi().showModalDialog(html, title);
}

function IAPF_escapeHtml_(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
