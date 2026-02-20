 // File: /CODE/00_BOOTSTRAP.gs

/**
 * IAPF MEMORY HUB V1 — Bootstrap & Guardrails
 * Bound script: uses SpreadsheetApp.getActiveSpreadsheet()
 * No destructive ops: MEMORY_LOG append-only
 */

const IAPF = {
  APP_NAME: "IAPF Memory Hub V1",
  MENU_NAME: "IAPF Memory",
  TZ: Session.getScriptTimeZone(),
  SETTINGS_SHEET: "SETTINGS",
  MEMORY_LOG_SHEET: "MEMORY_LOG",
  SNAPSHOT_SHEET: "SNAPSHOT_ACTIVE",
  ERRORS_SHEET: "ERRORS",
  LOGS_SHEET: "LOGS",

  PROP_PREFIX: "IAPF_MEMORY_",
  PROP_KEYS: {
    MEMORY_ROOT_FOLDER_ID: "memory_root_folder_id",
    SNAPSHOTS_FOLDER_ID: "snapshots_folder_id",
    LOGS_FOLDER_ID: "logs_folder_id",
    ROADMAP_FILE_ID: "roadmap_file_id",
    SOURCES: "sources"
  },

  // Snapshot params
  MAX_MEMORY_ITEMS: 30,
  MAX_LINES_CONTEXT: 20,

  // Secret detection (very conservative)
  SECRET_PATTERNS: [
    /sk-[A-Za-z0-9]{10,}/g,
    /AIza[0-9A-Za-z\-_]{10,}/g,
    /-----BEGIN [A-Z ]+ PRIVATE KEY-----/g,
    /xox[baprs]-[A-Za-z0-9-]{10,}/g
  ]
};

function IAPF_getActiveSS_() {
  return SpreadsheetApp.getActiveSpreadsheet();
}

function IAPF_nowIso_() {
  return new Date().toISOString();
}

function IAPF_getScriptProp_(key) {
  const p = PropertiesService.getScriptProperties();
  return p.getProperty(IAPF.PROP_PREFIX + key);
}

function IAPF_setScriptProp_(key, value) {
  const p = PropertiesService.getScriptProperties();
  if (value === null || value === undefined) return;
  p.setProperty(IAPF.PROP_PREFIX + key, String(value).trim());
}

function IAPF_guardNoSecrets_(text, contextLabel) {
  if (!text) return { ok: true, hits: [] };
  const hits = [];
  IAPF.SECRET_PATTERNS.forEach((re) => {
    const m = text.match(re);
    if (m && m.length) {
      hits.push({ pattern: String(re), matches: Array.from(new Set(m)).slice(0, 3) });
    }
  });
  if (hits.length) {
    IAPF_log_("WARN", "SECRET_DETECTED", `Secret-like pattern detected in ${contextLabel}. NOT storing raw content in logs.`, { hitsCount: hits.length });
    return { ok: false, hits };
  }
  return { ok: true, hits: [] };
}
