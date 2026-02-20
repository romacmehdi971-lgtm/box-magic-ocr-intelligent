// File: /CODE/G01_UI_MENU.gs
// HUB IAPF Memory V1 — Menu principal + sous-menu MCP Cockpit

function onOpen(e) {
  IAPF_uiBuildMenu_();
}

function IAPF_uiBuildMenu_() {
  const ui = SpreadsheetApp.getUi();

  // --- Sous-menu MCP Cockpit (attaché au menu IAPF Memory)
  const mcpMenu = ui.createMenu("MCP Cockpit")
    .addItem("🔌 Test Connection", "MCP_COCKPIT_testConnection")
    .addItem("🔍 GET /infra/whoami", "MCP_COCKPIT_getWhoami")
    .addItem("📊 Test Pagination", "MCP_COCKPIT_testPagination")
    .addItem("🛠️ HTTP GET Tool", "MCP_COCKPIT_httpGetTool")
    .addSeparator()
    .addItem("🌐 Audit Lecture Partout (P1)", "MCP_AUDIT_readEverywhere")
    .addSeparator()
    .addItem("1️⃣ Initialiser Journée", "MCP_ACTION_initializeDay")
    .addItem("2️⃣ Clôture Journée", "MCP_ACTION_closeDay")
    .addSeparator()
    .addItem("3️⃣ Audit Global", "MCP_ACTION_globalAudit")
    .addItem("4️⃣ Vérification Doc vs Code", "MCP_ACTION_verifyDocVsCode")
    .addItem("5️⃣ Déploiement Automatisé (SAFE)", "MCP_ACTION_automatedDeploy")
    .addSeparator()
    .addItem("Audit complet HUB", "MCP_AUDIT_auditHub")
    .addItem("Audit BOX2026", "MCP_AUDIT_auditBox2026")
    .addSeparator()
    .addItem("Export HUB (ZIP + XLSX Sheet)", "MCP_EXPORT_exportHubZipAndSheet")
    .addItem("Export BOX (ZIP + XLSX Sheet)", "MCP_EXPORT_exportBoxZipAndSheet")
    .addSeparator()
    .addItem("Vérifier cohérence dépendances", "MCP_DEPENDENCIES_checkConsistency");
  
  // --- Sous-menu Actions MCP Phase 2 (18 endpoints)
  const actionsMcpMenu = ui.createMenu("Actions MCP")
    .addItem("📁 Drive — List Tree", "MCP_ACTION_driveListTree")
    .addItem("📄 Drive — File Metadata", "MCP_ACTION_driveFileMetadata")
    .addItem("🔍 Drive — Search", "MCP_ACTION_driveSearch")
    .addSeparator()
    .addItem("📜 Apps Script — Deployments", "MCP_ACTION_appsScriptDeployments")
    .addItem("🏗️ Apps Script — Structure", "MCP_ACTION_appsScriptStructure")
    .addSeparator()
    .addItem("☁️ Cloud Run — Service Status", "MCP_ACTION_cloudRunServiceStatus")
    .addSeparator()
    .addItem("🔐 Secret Manager — List", "MCP_ACTION_secretsList")
    .addItem("🔑 Secret Manager — Get Reference", "MCP_ACTION_secretGetReference")
    .addItem("➕ Secret Manager — Create (DRY_RUN)", "MCP_ACTION_secretCreateDryRun")
    .addItem("✅ Secret Manager — Create (APPLY)", "MCP_ACTION_secretCreateApply")
    .addSeparator()
    .addItem("🌐 Web — Search", "MCP_ACTION_webSearch")
    .addSeparator()
    .addItem("💻 Terminal — Run (READ_ONLY)", "MCP_ACTION_terminalRunReadOnly");

  // --- Menu principal IAPF Memory
  ui.createMenu(IAPF.MENU_NAME)
    .addItem("Initialiser / Valider HUB", "IAPF_initHub")
    .addSeparator()
    .addItem("Inventaire Drive (rechercher existants)", "IAPF_inventoryDrive")
    .addSeparator()
    .addItem("Générer Snapshot", "IAPF_generateSnapshot")
    .addItem("Exporter Context Pack", "IAPF_exportContextPack")
    .addSeparator()
    .addItem("Ajouter décision / règle / constat", "IAPF_uiAddMemoryEntry")
    .addItem("Ajouter / maj erreur Orion", "IAPF_uiUpsertError")
    .addSeparator()
    .addItem("Installer / Mettre à jour trigger daily (06:00)", "IAPF_installDailyTrigger")
    .addSeparator()
    // IMPORTANT: ouvre le dossier ARCHIVES (pas BACKUP_BOX2026)
    .addItem("BOX2026 — Ouvrir dossier ARCHIVES", "MCP_UI_openArchivesFolder")
    .addSeparator()
    .addSubMenu(mcpMenu)
    .addSubMenu(actionsMcpMenu)
    .addSeparator()
    .addItem("Ouvrir LOGS", "IAPF_uiOpenLogs")
    .addToUi();
}

function IAPF_uiOpenLogs() {
  const ss = IAPF_getActiveSS_();
  const sh = ss.getSheetByName(IAPF.LOGS_SHEET);
  if (sh) ss.setActiveSheet(sh);
}

function IAPF_uiAddMemoryEntry() {
  const ui = SpreadsheetApp.getUi();
  const typeResp = ui.prompt("Type", "DECISION / REGLE / CONSTAT", ui.ButtonSet.OK_CANCEL);
  if (typeResp.getSelectedButton() !== ui.Button.OK) return;

  const titleResp = ui.prompt("Titre", "Titre court", ui.ButtonSet.OK_CANCEL);
  if (titleResp.getSelectedButton() !== ui.Button.OK) return;

  const detailsResp = ui.prompt("Détails", "Détails (1-3 phrases, factuel)", ui.ButtonSet.OK_CANCEL);
  if (detailsResp.getSelectedButton() !== ui.Button.OK) return;

  const type = String(typeResp.getResponseText() || "").trim().toUpperCase();
  const title = String(titleResp.getResponseText() || "").trim();
  const details = String(detailsResp.getResponseText() || "").trim();

  if (!type || !title) {
    ui.alert("Champs manquants", "Type et Titre sont obligatoires.", ui.ButtonSet.OK);
    return;
  }

  // append-only MEMORY_LOG (géré par ton module 03_MEMORY_WRITE)
  IAPF_memoryAppendLogRow({
    type,
    title,
    details,
    author: Session.getActiveUser().getEmail() || "unknown",
    source: "UI",
    tags: "ORION;HUB"
  });

  ui.alert("OK", "Entrée ajoutée dans MEMORY_LOG.", ui.ButtonSet.OK);
}

function IAPF_uiUpsertError() {
  // Délégué au module erreurs existant (si présent)
  if (typeof IAPF_uiUpsertErrorImpl_ === "function") return IAPF_uiUpsertErrorImpl_();
  SpreadsheetApp.getUi().alert("Fonction indisponible", "IAPF_uiUpsertErrorImpl_ introuvable.", SpreadsheetApp.getUi().ButtonSet.OK);
}

/**
 * Ouvre le dossier ARCHIVES défini dans SETTINGS.archives_folder_id
 */
function MCP_UI_openArchivesFolder() {
  const ss = IAPF_getActiveSS_();
  const sh = ss.getSheetByName(IAPF.SETTINGS_SHEET);
  if (!sh) {
    SpreadsheetApp.getUi().alert("SETTINGS manquant", "Onglet SETTINGS introuvable.", SpreadsheetApp.getUi().ButtonSet.OK);
    return;
  }

  const values = sh.getDataRange().getValues();
  let archivesId = "";
  for (let i = 1; i < values.length; i++) {
    const k = String(values[i][0] || "").trim();
    if (k === "archives_folder_id") {
      archivesId = String(values[i][1] || "").trim();
      break;
    }
  }

  if (!archivesId) {
    SpreadsheetApp.getUi().alert(
      "SETTINGS manquant",
      "Ajoute la clé SETTINGS:archives_folder_id = <ID dossier Drive ARCHIVES>.",
      SpreadsheetApp.getUi().ButtonSet.OK
    );
    return;
  }

  const url = "https://drive.google.com/drive/folders/" + archivesId;
  const html = HtmlService.createHtmlOutput(
    '<script>window.open("' + url + '","_blank");google.script.host.close();</script>'
  ).setWidth(180).setHeight(40);

  SpreadsheetApp.getUi().showModalDialog(html, "Ouverture ARCHIVES");
}

/**
 * ===== 5 NOUVELLES ACTIONS MCP =====
 * Ces fonctions sont appelées depuis le sous-menu MCP Cockpit.
 * Elles doivent être implémentées dans G07_MCP_COCKPIT.gs ou équivalent.
 */

// 1️⃣ Initialiser Journée
function MCP_ACTION_initializeDay() {
  if (typeof MCP_IMPL_initializeDay === "function") {
    return MCP_IMPL_initializeDay();
  }
  SpreadsheetApp.getUi().alert(
    "Action MCP",
    "MCP_IMPL_initializeDay() non trouvée.\nAjoute cette fonction dans G07_MCP_COCKPIT.gs.",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

// 2️⃣ Clôture Journée
function MCP_ACTION_closeDay() {
  if (typeof MCP_IMPL_closeDay === "function") {
    return MCP_IMPL_closeDay();
  }
  SpreadsheetApp.getUi().alert(
    "Action MCP",
    "MCP_IMPL_closeDay() non trouvée.\nAjoute cette fonction dans G07_MCP_COCKPIT.gs.",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

// 3️⃣ Audit Global
function MCP_ACTION_globalAudit() {
  if (typeof MCP_IMPL_globalAudit === "function") {
    return MCP_IMPL_globalAudit();
  }
  SpreadsheetApp.getUi().alert(
    "Action MCP",
    "MCP_IMPL_globalAudit() non trouvée.\nAjoute cette fonction dans G07_MCP_COCKPIT.gs.",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

// 4️⃣ Vérification Doc vs Code
function MCP_ACTION_verifyDocVsCode() {
  if (typeof MCP_IMPL_verifyDocVsCode === "function") {
    return MCP_IMPL_verifyDocVsCode();
  }
  SpreadsheetApp.getUi().alert(
    "Action MCP",
    "MCP_IMPL_verifyDocVsCode() non trouvée.\nAjoute cette fonction dans G07_MCP_COCKPIT.gs.",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}

// 5️⃣ Déploiement Automatisé
function MCP_ACTION_automatedDeploy() {
  if (typeof MCP_IMPL_automatedDeploy === "function") {
    return MCP_IMPL_automatedDeploy();
  }
  SpreadsheetApp.getUi().alert(
    "Action MCP",
    "MCP_IMPL_automatedDeploy() non trouvée.\nAjoute cette fonction dans G07_MCP_COCKPIT.gs.",
    SpreadsheetApp.getUi().ButtonSet.OK
  );
}
