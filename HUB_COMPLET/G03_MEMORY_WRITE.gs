// File: /CODE/03_MEMORY_WRITE.gs

function IAPF_appendMemoryEntry_(type, title, details, opts) {
  try {
    IAPF_initHub_({ quiet: true });

    const safeCheck = IAPF_guardNoSecrets_(`${title}\n${details}`, "MEMORY_LOG");
    if (!safeCheck.ok) {
      return { ok: false, error: "Secret détecté (pattern). Stockage refusé. Mettre en coffre + ScriptProperties." };
    }

    const ss = IAPF_getActiveSS_();
    const sh = ss.getSheetByName(IAPF.MEMORY_LOG_SHEET);

    const row = [
      IAPF_nowIso_(),
      (type || "CONSTAT").toUpperCase(),
      (title || "").trim(),
      (details || "").trim(),
      Session.getActiveUser().getEmail() || "",
      (opts && opts.source) ? String(opts.source) : "",
      (opts && opts.tags) ? String(opts.tags) : ""
    ];

    sh.appendRow(row);
    IAPF_log_("INFO", "MEMORY_APPEND_OK", "Appended entry to MEMORY_LOG", { type: row[1], title: row[2] });

    return { ok: true };
  } catch (err) {
    IAPF_log_("ERROR", "MEMORY_APPEND_FAIL", String(err && err.stack ? err.stack : err), {});
    return { ok: false, error: String(err) };
  }
}

function IAPF_upsertError_(code, title, status, details) {
  try {
    IAPF_initHub_({ quiet: true });

    const safeCheck = IAPF_guardNoSecrets_(`${code}\n${title}\n${details}`, "ERRORS");
    if (!safeCheck.ok) {
      return { ok: false, error: "Secret détecté (pattern). Stockage refusé." };
    }

    const ss = IAPF_getActiveSS_();
    const sh = ss.getSheetByName(IAPF.ERRORS_SHEET);

    const lastRow = sh.getLastRow();
    const data = lastRow >= 2 ? sh.getRange(2, 1, lastRow - 1, 5).getValues() : [];
    const targetCode = (code || "").trim();
    if (!targetCode) return { ok: false, error: "Code erreur vide" };

    let foundRowIndex = -1;
    for (let i = 0; i < data.length; i++) {
      if (String(data[i][0] || "").trim() === targetCode) {
        foundRowIndex = i + 2;
        break;
      }
    }

    const row = [
      targetCode,
      (title || "").trim(),
      (status || "ACTIVE").trim().toUpperCase(),
      IAPF_nowIso_(),
      (details || "").trim()
    ];

    if (foundRowIndex === -1) {
      sh.appendRow(row);
      IAPF_log_("INFO", "ERROR_UPSERT_CREATE", "Created new error entry", { code: targetCode });
    } else {
      sh.getRange(foundRowIndex, 1, 1, 5).setValues([row]);
      IAPF_log_("INFO", "ERROR_UPSERT_UPDATE", "Updated error entry", { code: targetCode });
    }

    return { ok: true };
  } catch (err) {
    IAPF_log_("ERROR", "ERROR_UPSERT_FAIL", String(err && err.stack ? err.stack : err), {});
    return { ok: false, error: String(err) };
  }
}
