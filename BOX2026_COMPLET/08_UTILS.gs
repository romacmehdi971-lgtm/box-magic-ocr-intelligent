/**
 * ============================================================================
 * BOX MAGIC — 08_UTILS.gs
 * Rôle : utilitaires transverses (logs, droits, fichiers)
 * SOURCE CONFIG UNIQUE : BM_CFG.get(KEY)
 * ============================================================================
 */

/**
 * Retourne true si le moteur est en mode "production"
 * (mapping conservateur)
 * MODE_EXECUTION = ACTIF  => production
 * sinon                   => observation
 */
function BM_isProduction_() {
  try {
    return BM_CFG.get("MODE_EXECUTION") === "ACTIF";
  } catch (e) {
    return false;
  }
}

/**
 * Log une action moteur
 */
function logAction(action, message, payloadOrLevel, maybeStackOrLevel, maybeLevel) {
  const ss = SpreadsheetApp.getActiveSpreadsheet() || SpreadsheetApp.getActive();
  if (!ss) return;

  const sheet = ss.getSheetByName("LOGS_SYSTEM");
  if (!sheet) return;

  const toStr_ = (v) => {
    if (v === null || typeof v === "undefined") return "";
    if (typeof v === "string") return v;
    if (typeof v === "number" || typeof v === "boolean") return String(v);
    try { return JSON.stringify(v); } catch (e) { return String(v); }
  };

  // Compat :
  // 3 args : (action, message, level) OU (action, message, payload)
  // 4 args : (action, message, payload, level)
  // 5 args : (action, message, payload, stack, level)  <-- SCAN
  let level = "INFO";
  let msg = (message || "");

  // 5 args : payload + stack + level
  if (typeof maybeLevel !== "undefined") {
    const payloadStr = toStr_(payloadOrLevel);
    const stackStr = toStr_(maybeStackOrLevel);

    if (payloadStr) msg = (msg ? msg + " " : "") + payloadStr;
    if (stackStr) msg = (msg ? msg + " " : "") + stackStr;

    level = (toStr_(maybeLevel) || "INFO");

  // 4 args : payload + level
  } else if (typeof maybeStackOrLevel !== "undefined") {
    const payloadStr = toStr_(payloadOrLevel);
    if (payloadStr) msg = (msg ? msg + " " : "") + payloadStr;

    level = (toStr_(maybeStackOrLevel) || "INFO");

  // 3 args : si string => level, sinon payload
  } else if (typeof payloadOrLevel !== "undefined") {
    if (typeof payloadOrLevel === "string") {
      level = (payloadOrLevel || "INFO");
    } else {
      const payloadStr = toStr_(payloadOrLevel);
      if (payloadStr) msg = (msg ? msg + " " : "") + payloadStr;
    }
  }

  const production = BM_isProduction_();

  try {
    sheet.appendRow([
      new Date(),
      action || "",
      msg,
      level || "INFO",
      production
    ]);
    SpreadsheetApp.flush();
  } catch (e) {
    try {
      Logger.log("[LOGS_SYSTEM_WRITE_FAILED] " + String(e && e.message ? e.message : e));
      Logger.log("[LOGS_SYSTEM_CTX] ss=" + (ss ? ss.getName() : "NULL") + " / sheet=" + (sheet ? sheet.getName() : "NULL"));
      Logger.log("[LOGS_SYSTEM_PAYLOAD] action=" + String(action || "") + " level=" + String(level || "") + " msg=" + String(msg || ""));
    } catch (_) {}
  }
}

/**
 * Vérifie les droits utilisateur
 * Règle actuelle : mono-admin
 */
function verifierDroits(role) {
  const email = Session.getActiveUser().getEmail();
  const admin = BM_CFG.get("ADMIN_EMAIL");

  if (role === "ADMIN") {
    return email === admin;
  }

  return false;
}

/**
 * Copie un fichier dans un dossier cible
 * Empêche toute écriture à la racine Drive
 */
function copierFichier(fileId, dossierId) {
  if (!fileId || !dossierId) {
    throw new Error("copierFichier : paramètres manquants");
  }

  const rootId = BM_CFG.get("DRIVE_ROOT_ID");
  if (dossierId === rootId) {
    throw new Error("Écriture directe à la racine Drive interdite");
  }

  const file = DriveApp.getFileById(fileId);
  const target = DriveApp.getFolderById(dossierId);

  return file.makeCopy(file.getName(), target);
}

/**
 * Wrapper lecture config (lecture seule)
 * Remplace les anciens getConfig / ScriptProperties
 */
function obtenirConfiguration() {
  return {
    mode_execution: BM_CFG.get("MODE_EXECUTION"),
    admin_email: BM_CFG.get("ADMIN_EMAIL"),
    drive_root_id: BM_CFG.get("DRIVE_ROOT_ID"),
    inbox_folder_id: BM_CFG.get("INBOX_FOLDER_ID")
  };
}

/**
 * Désactivé volontairement :
 * Toute écriture de configuration est interdite ici.
 */
function mettreAJourConfiguration() {
  throw new Error("Écriture de configuration interdite (source unique = Sheet CONFIG)");
}
