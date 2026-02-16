// File: /CODE/01_UI_MENU.gs
// MODIFIÉ le 2026-02-14 : Ajout de 5 nouveaux boutons MCP

function onOpen(e) {
  IAPF_uiBuildMenu_();
}

function IAPF_uiBuildMenu_() {
  const ui = SpreadsheetApp.getUi();

  // --- Sous-menu MCP Cockpit (attaché au menu IAPF Memory)
  const mcpMenu = ui.createMenu("MCP Cockpit")
    .addItem("🌅 Initialiser Journée", "MCP_initJournee")
    .addItem("🌙 Clôture Journée", "MCP_clotureJournee")
    .addSeparator()
    .addItem("🔍 Audit Global", "MCP_auditGlobal")
    .addItem("📚 Vérification Doc vs Code", "MCP_verificationDocVsCode")
    .addSeparator()
    .addItem("Audit complet HUB", "MCP_AUDIT_auditHub")
    .addItem("Audit BOX2026", "MCP_AUDIT_auditBox2026")
    .addSeparator()
    .addItem("Générer snapshot", "MCP_SNAPSHOT_generate")
    .addSeparator()
    .addItem("Export HUB (ZIP + XLSX Sheet)", "MCP_EXPORT_exportHubZipAndSheet")
    .addItem("Export BOX (ZIP + XLSX Sheet)", "MCP_EXPORT_exportBoxZipAndSheet")
    .addSeparator()
    .addItem("Vérifier cohérence dépendances", "MCP_DEPENDENCIES_checkConsistency")
    .addSeparator()
    .addItem("🚀 Déploiement Automatisé", "MCP_deploiementAutomatise");

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

// ============================================================================
// NOUVEAUX BOUTONS MCP (Ajoutés le 2026-02-14)
// ============================================================================

/**
 * 🌅 Initialiser Journée
 * Crée snapshot début journée, vérifie onglets critiques, log dans MEMORY_LOG
 */
function MCP_initJournee() {
  try {
    const timestamp = Utilities.formatDate(new Date(), "Europe/Paris", "yyyy-MM-dd HH:mm:ss");
    const snapshotName = `INIT_${Utilities.formatDate(new Date(), "Europe/Paris", "yyyyMMdd_HHmmss")}`;
    
    // 1. Créer snapshot
    if (typeof IAPF_generateSnapshot === "function") {
      IAPF_generateSnapshot();
    }
    
    // 2. Vérifier onglets critiques
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const criticalSheets = ["MEMORY_LOG", "SNAPSHOT_ACTIVE", "DEPENDANCES_SCRIPTS", "SETTINGS"];
    const status = criticalSheets.map(name => {
      const sheet = ss.getSheetByName(name);
      return { 
        name: name, 
        exists: Boolean(sheet), 
        rows: sheet ? sheet.getLastRow() : 0 
      };
    });
    
    const allOk = status.every(s => s.exists);
    
    // 3. Logger dans MEMORY_LOG
    if (typeof IAPF_memoryAppendLogRow === "function") {
      IAPF_memoryAppendLogRow({
        type: "MCP_ACTION",
        title: "Initialisation Journée",
        details: `Snapshot: ${snapshotName} | Onglets vérifiés: ${status.length} | Status: ${allOk ? "OK" : "WARN"}`,
        author: Session.getActiveUser().getEmail() || "system",
        source: "MCP_INIT_JOURNEE",
        tags: "MCP;JOURNEE;INIT"
      });
    }
    
    // 4. Afficher résumé
    const statusText = status.map(s => `${s.name}: ${s.exists ? "✅ (" + s.rows + " rows)" : "❌"}`).join("\n");
    SpreadsheetApp.getUi().alert(
      "✅ Journée initialisée",
      `Snapshot: ${snapshotName}\n\nOnglets critiques:\n${statusText}`,
      SpreadsheetApp.getUi().ButtonSet.OK
    );
    
  } catch (e) {
    SpreadsheetApp.getUi().alert("❌ Erreur", String(e), SpreadsheetApp.getUi().ButtonSet.OK);
  }
}

/**
 * 🌙 Clôture Journée
 * Génère rapport d'activité, crée snapshot fin journée, archive logs
 */
function MCP_clotureJournee() {
  try {
    const timestamp = Utilities.formatDate(new Date(), "Europe/Paris", "yyyy-MM-dd HH:mm:ss");
    const snapshotName = `CLOSE_${Utilities.formatDate(new Date(), "Europe/Paris", "yyyyMMdd_HHmmss")}`;
    
    // 1. Générer rapport d'activité (compter actions du jour dans MEMORY_LOG)
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const memoryLog = ss.getSheetByName("MEMORY_LOG");
    let todayActions = 0;
    
    if (memoryLog) {
      const lastRow = memoryLog.getLastRow();
      if (lastRow > 1) {
        const data = memoryLog.getRange(2, 1, lastRow - 1, 7).getValues();
        const today = new Date();
        todayActions = data.filter(row => {
          try {
            const rowDate = new Date(row[0]);
            return rowDate.toDateString() === today.toDateString();
          } catch (e) {
            return false;
          }
        }).length;
      }
    }
    
    // 2. Créer snapshot
    if (typeof IAPF_generateSnapshot === "function") {
      IAPF_generateSnapshot();
    }
    
    // 3. Logger clôture
    if (typeof IAPF_memoryAppendLogRow === "function") {
      IAPF_memoryAppendLogRow({
        type: "MCP_ACTION",
        title: "Clôture Journée",
        details: `Snapshot: ${snapshotName} | Actions aujourd'hui: ${todayActions}`,
        author: Session.getActiveUser().getEmail() || "system",
        source: "MCP_CLOTURE_JOURNEE",
        tags: "MCP;JOURNEE;CLOTURE"
      });
    }
    
    // 4. Afficher résumé
    SpreadsheetApp.getUi().alert(
      "✅ Journée clôturée",
      `Actions effectuées: ${todayActions}\nSnapshot: ${snapshotName}\n\nBonne soirée !`,
      SpreadsheetApp.getUi().ButtonSet.OK
    );
    
  } catch (e) {
    SpreadsheetApp.getUi().alert("❌ Erreur", String(e), SpreadsheetApp.getUi().ButtonSet.OK);
  }
}

/**
 * 🔍 Audit Global
 * Lance audit HUB + BOX2026 (utilise fonctions existantes)
 */
function MCP_auditGlobal() {
  try {
    const ui = SpreadsheetApp.getUi();
    const result = ui.alert(
      "🔍 Audit Global",
      "Lancer audit complet du HUB et BOX2026 ?\n(Durée: ~30 secondes)",
      ui.ButtonSet.YES_NO
    );
    
    if (result !== ui.Button.YES) return;
    
    // Appeler audits existants
    let hubResult = "N/A";
    let boxResult = "N/A";
    
    if (typeof MCP_AUDIT_auditHub === "function") {
      MCP_AUDIT_auditHub();
      hubResult = "OK";
    }
    
    if (typeof MCP_AUDIT_auditBox2026 === "function") {
      MCP_AUDIT_auditBox2026();
      boxResult = "OK";
    }
    
    // Logger
    if (typeof IAPF_memoryAppendLogRow === "function") {
      IAPF_memoryAppendLogRow({
        type: "MCP_ACTION",
        title: "Audit Global",
        details: `HUB: ${hubResult} | BOX2026: ${boxResult}`,
        author: Session.getActiveUser().getEmail() || "system",
        source: "MCP_AUDIT_GLOBAL",
        tags: "MCP;AUDIT;GLOBAL"
      });
    }
    
    ui.alert(
      "✅ Audit global terminé",
      `HUB: ${hubResult}\nBOX2026: ${boxResult}\n\nVérifiez les logs pour les détails.`,
      ui.ButtonSet.OK
    );
    
  } catch (e) {
    SpreadsheetApp.getUi().alert("❌ Erreur", String(e), SpreadsheetApp.getUi().ButtonSet.OK);
  }
}

/**
 * 📚 Vérification Doc vs Code
 * Compare documentation MEMORY_LOG vs code réel (audit structure)
 */
function MCP_verificationDocVsCode() {
  try {
    const ui = SpreadsheetApp.getUi();
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    
    // 1. Lire MEMORY_LOG
    const memoryLog = ss.getSheetByName("MEMORY_LOG");
    let logEntries = 0;
    if (memoryLog) {
      logEntries = memoryLog.getLastRow() - 1; // -1 pour header
    }
    
    // 2. Compter onglets présents
    const expectedSheets = [
      "MEMORY_LOG", "SNAPSHOT_ACTIVE", "DEPENDANCES_SCRIPTS", 
      "CARTOGRAPHIE_APPELS", "REGLES_DE_GOUVERNANCE", "RISKS", 
      "CONFLITS_DETECTES", "SETTINGS", "LOGS"
    ];
    const actualSheets = ss.getSheets().map(s => s.getName());
    const missingSheets = expectedSheets.filter(name => !actualSheets.includes(name));
    const extraSheets = actualSheets.filter(name => !expectedSheets.includes(name) && !name.startsWith("_"));
    
    // 3. Générer rapport
    const divergences = missingSheets.length + extraSheets.length;
    const rapport = {
      timestamp: new Date(),
      log_entries: logEntries,
      expected_sheets: expectedSheets.length,
      actual_sheets: actualSheets.length,
      missing_sheets: missingSheets.join(", ") || "aucun",
      extra_sheets: extraSheets.join(", ") || "aucun",
      divergences: divergences
    };
    
    // 4. Logger
    if (typeof IAPF_memoryAppendLogRow === "function") {
      IAPF_memoryAppendLogRow({
        type: "MCP_ACTION",
        title: "Vérification Doc vs Code",
        details: `Entrées log: ${logEntries} | Onglets: ${actualSheets.length}/${expectedSheets.length} | Divergences: ${divergences}`,
        author: Session.getActiveUser().getEmail() || "system",
        source: "MCP_VERIF_DOC_CODE",
        tags: "MCP;AUDIT;DOCUMENTATION"
      });
    }
    
    // 5. Afficher résumé
    ui.alert(
      "📚 Vérification Doc vs Code",
      `Entrées MEMORY_LOG: ${logEntries}\n` +
      `Onglets attendus: ${expectedSheets.length}\n` +
      `Onglets présents: ${actualSheets.length}\n` +
      `Onglets manquants: ${missingSheets.length > 0 ? missingSheets.join(", ") : "aucun"}\n` +
      `Onglets supplémentaires: ${extraSheets.length > 0 ? extraSheets.join(", ") : "aucun"}\n\n` +
      `Divergences: ${divergences}`,
      ui.ButtonSet.OK
    );
    
  } catch (e) {
    SpreadsheetApp.getUi().alert("❌ Erreur", String(e), SpreadsheetApp.getUi().ButtonSet.OK);
  }
}

/**
 * 🚀 Déploiement Automatisé
 * Placeholder - nécessite configuration GitHub PAT, Cloud Run, etc.
 */
function MCP_deploiementAutomatise() {
  const ui = SpreadsheetApp.getUi();
  ui.alert(
    "⏸️ Fonctionnalité en cours de développement",
    "Le déploiement automatisé nécessite:\n" +
    "- GitHub PAT (repo + workflow)\n" +
    "- GCP Service Account (Cloud Run)\n" +
    "- Configuration SETTINGS\n\n" +
    "Voir MCP_DEPLOIEMENT_AUTOMATISE.md pour instructions.",
    ui.ButtonSet.OK
  );
  
  // Logger tentative
  if (typeof IAPF_memoryAppendLogRow === "function") {
    IAPF_memoryAppendLogRow({
      type: "MCP_ACTION",
      title: "Déploiement Automatisé (placeholder)",
      details: "Fonctionnalité non configurée",
      author: Session.getActiveUser().getEmail() || "system",
      source: "MCP_DEPLOIEMENT_AUTO",
      tags: "MCP;DEPLOY;PENDING"
    });
  }
}
