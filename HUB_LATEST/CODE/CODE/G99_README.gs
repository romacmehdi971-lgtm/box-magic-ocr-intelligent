// File: /CODE/99_README.gs

function IAPF_initHub() {
  const ui = SpreadsheetApp.getUi();
  const res = IAPF_initHub_({ quiet: false });
  if (!res.ok) {
    ui.alert("Init HUB: ERREUR", res.error || "Unknown error", ui.ButtonSet.OK);
    return;
  }
  ui.alert("Init HUB: OK", "Onglets/headers validés. (Voir LOGS)", ui.ButtonSet.OK);
}

function IAPF_installDailyTrigger() {
  const ui = SpreadsheetApp.getUi();
  const res = IAPF_installDailyTrigger_();
  if (!res.ok) {
    ui.alert("Trigger daily: ERREUR", res.error || "Unknown error", ui.ButtonSet.OK);
    return;
  }
  ui.alert("Trigger daily: OK", "Déclencheur daily 06:00 configuré.", ui.ButtonSet.OK);
}

function IAPF_installDailyTrigger_() {
  try {
    const fnName = "IAPF_generateSnapshot_";
    const triggers = ScriptApp.getProjectTriggers();
    triggers.forEach((t) => {
      if (t.getHandlerFunction && t.getHandlerFunction() === fnName) {
        ScriptApp.deleteTrigger(t);
      }
    });

    ScriptApp.newTrigger(fnName)
      .timeBased()
      .everyDays(1)
      .atHour(6)
      .create();

    IAPF_log_("INFO", "TRIGGER_DAILY_SET", "Daily trigger set at 06:00", {});
    return { ok: true };
  } catch (err) {
    IAPF_log_("ERROR", "TRIGGER_DAILY_FAIL", String(err), {});
    return { ok: false, error: String(err) };
  }
}

function IAPF_initHub_(opts) {
  try {
    const ss = IAPF_getActiveSS_();
    IAPF_ensureSheet_(ss, IAPF.SETTINGS_SHEET, ["key", "value", "notes"]);
    IAPF_ensureSheet_(ss, IAPF.MEMORY_LOG_SHEET, ["ts_iso", "type", "title", "details", "author", "source", "tags"]);
    IAPF_ensureSheet_(ss, IAPF.SNAPSHOT_SHEET, ["generated_ts_iso", "snapshot_text"]);
    IAPF_ensureSheet_(ss, IAPF.ERRORS_SHEET, ["code", "title", "status", "last_seen_ts_iso", "details"]);
    IAPF_ensureSheet_(ss, IAPF.LOGS_SHEET, ["ts_iso", "level", "event", "message", "data_json"]);

    IAPF_seedErrorsIfEmpty_();

    if (!opts || !opts.quiet) {
      IAPF_log_("INFO", "INIT_HUB_OK", "Hub initialized/validated", {});
    }
    return { ok: true };
  } catch (err) {
    IAPF_log_("ERROR", "INIT_HUB_FAIL", String(err && err.stack ? err.stack : err), {});
    return { ok: false, error: String(err) };
  }
}

function IAPF_ensureSheet_(ss, name, headers) {
  let sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);

  const firstRow = sh.getRange(1, 1, 1, headers.length).getValues()[0];
  let needsHeader = false;
  for (let i = 0; i < headers.length; i++) {
    if (String(firstRow[i] || "").trim() !== headers[i]) {
      needsHeader = true;
      break;
    }
  }
  if (needsHeader) {
    sh.getRange(1, 1, 1, headers.length).setValues([headers]);
    sh.getRange(1, 1, 1, headers.length).setFontWeight("bold");
  }
}

function IAPF_seedErrorsIfEmpty_() {
  const ss = IAPF_getActiveSS_();
  const sh = ss.getSheetByName(IAPF.ERRORS_SHEET);
  const last = sh.getLastRow();
  if (last >= 2) return;

  const seed = [
    ["M3.7-001", "runner .cmd incomplet", "ACTIVE", IAPF_nowIso_(), "Ne pas produire de runner incomplet."],
    ["M3.7-002", "ParserError accents/encodage", "ACTIVE", IAPF_nowIso_(), "Forcer UTF-8, éviter pièges d’accents."],
    ["M3.7-003", "Set-StrictMode avant param", "ACTIVE", IAPF_nowIso_(), "Si PowerShell, ordre correct."],
    ["M3.7-005", "New-Item -LiteralPath non supporté", "ACTIVE", IAPF_nowIso_(), "Remplacer par -Path."],
    ["M3.8-001", "$events.Count scalaire", "ACTIVE", IAPF_nowIso_(), "Utiliser @($events) en PowerShell."],
    ["M3.8-002", "ArgumentException types arguments", "ACTIVE", IAPF_nowIso_(), "Normaliser chemins + logs détaillés."]
  ];
  sh.getRange(2, 1, seed.length, 5).setValues(seed);
}

function IAPF_getConfig_(key) {
  const fromProps = IAPF_getScriptProp_(key);
  if (fromProps) return fromProps;

  const ss = IAPF_getActiveSS_();
  const sh = ss.getSheetByName(IAPF.SETTINGS_SHEET);
  const last = sh.getLastRow();
  if (last < 2) return "";

  const data = sh.getRange(2, 1, last - 1, 3).getValues();
  for (let i = 0; i < data.length; i++) {
    const k = String(data[i][0] || "").trim();
    if (k === key) return String(data[i][1] || "").trim();
  }
  return "";
}

function IAPF_setConfig_(key, value) {
  IAPF_setScriptProp_(key, value);

  const ss = IAPF_getActiveSS_();
  const sh = ss.getSheetByName(IAPF.SETTINGS_SHEET);
  const last = sh.getLastRow();
  const v = String(value || "").trim();

  if (last < 2) {
    sh.appendRow([key, v, ""]);
    return;
  }

  const data = sh.getRange(2, 1, last - 1, 3).getValues();
  for (let i = 0; i < data.length; i++) {
    const k = String(data[i][0] || "").trim();
    if (k === key) {
      sh.getRange(i + 2, 2).setValue(v);
      return;
    }
  }
  sh.appendRow([key, v, ""]);
}

function IAPF_readLastMemoryEntries_(n) {
  const ss = IAPF_getActiveSS_();
  const sh = ss.getSheetByName(IAPF.MEMORY_LOG_SHEET);
  const last = sh.getLastRow();
  if (last < 2) return [];

  const take = Math.min(n || 30, last - 1);
  const start = last - take + 1;
  const vals = sh.getRange(start, 1, take, 7).getValues();

  const items = vals.map((r) => ({
    ts_iso: String(r[0] || ""),
    type: String(r[1] || ""),
    title: String(r[2] || ""),
    details: String(r[3] || ""),
    author: String(r[4] || ""),
    source: String(r[5] || ""),
    tags: String(r[6] || "")
  }));

  items.sort((a, b) => (a.ts_iso < b.ts_iso ? 1 : -1));
  return items;
}

function IAPF_readErrorsActive_() {
  const ss = IAPF_getActiveSS_();
  const sh = ss.getSheetByName(IAPF.ERRORS_SHEET);
  const last = sh.getLastRow();
  if (last < 2) return [];

  const vals = sh.getRange(2, 1, last - 1, 5).getValues();
  const items = vals.map((r) => ({
    code: String(r[0] || ""),
    title: String(r[1] || ""),
    status: String(r[2] || ""),
    last_seen_ts_iso: String(r[3] || ""),
    details: String(r[4] || "")
  }));

  const active = items.filter(x => String(x.status || "").toUpperCase() === "ACTIVE");
  return active;
}

function IAPF_getRoadmapHint_() {
  const id = IAPF_getConfig_("roadmap_file_id");
  if (!id) return "";
  try {
    const f = DriveApp.getFileById(id);
    return `${f.getName()} (${id})`;
  } catch (e) {
    IAPF_log_("WARN", "ROADMAP_ID_INVALID", "roadmap_file_id invalid or no access", { id });
    return "";
  }
}
