// File: /CODE/G03_MEMORY_WRITE.gs

/**
 * Get author email with safe fallback
 * Avoid MEMORY_APPEND_FAIL due to Session.getActiveUser() unavailable in some contexts
 */
function _getAuthorSafe_() {
  try {
    const email = Session.getActiveUser().getEmail();
    if (email) return email;
  } catch (e) {
    // Session unavailable (trigger, API call, etc.)
  }
  
  // Fallback: check if triggered by MCP/System
  try {
    const props = PropertiesService.getScriptProperties();
    const mcp_mode = props.getProperty("IAPF_API_MODE");
    if (mcp_mode) return "SYSTEM/MCP";
  } catch (e) {}
  
  // Last resort
  return "SYSTEM";
}

function IAPF_appendMemoryEntry_(type, title, details, opts) {
  // Backward-compatible call signature:
  // - Legacy: IAPF_appendMemoryEntry_(type, title, details, opts)
  // - New:    IAPF_appendMemoryEntry_({ type, title, details, source, tags, opts })
  if (type && typeof type === "object" && title === undefined && details === undefined && opts === undefined) {
    const payload = type;
    type = payload.type;
    title = payload.title;
    details = payload.details;
    const pOpts = payload.opts && typeof payload.opts === "object" ? payload.opts : {};
    opts = {
      source: payload.source !== undefined ? payload.source : (pOpts.source !== undefined ? pOpts.source : ""),
      tags: payload.tags !== undefined ? payload.tags : (pOpts.tags !== undefined ? pOpts.tags : "")
    };
  }

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
      _getAuthorSafe_(),
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

    const now = IAPF_nowIso_();
    const rows = sh.getDataRange().getValues();
    const header = rows[0] || [];

    const idxCode = header.indexOf("code");
    const idxTitle = header.indexOf("title");
    const idxStatus = header.indexOf("status");
    const idxDetails = header.indexOf("details");
    const idxUpdatedAt = header.indexOf("updated_at");

    if (idxCode < 0) throw new Error("ERRORS header missing: code");
    if (idxTitle < 0) throw new Error("ERRORS header missing: title");
    if (idxStatus < 0) throw new Error("ERRORS header missing: status");
    if (idxDetails < 0) throw new Error("ERRORS header missing: details");
    if (idxUpdatedAt < 0) throw new Error("ERRORS header missing: updated_at");

    let foundRow = -1;
    for (let i = 1; i < rows.length; i++) {
      if (String(rows[i][idxCode] || "").trim() === String(code).trim()) {
        foundRow = i + 1; // 1-based
        break;
      }
    }

    const row = new Array(header.length).fill("");
    row[idxCode] = String(code || "").trim();
    row[idxTitle] = String(title || "").trim();
    row[idxStatus] = String(status || "").trim();
    row[idxDetails] = String(details || "").trim();
    row[idxUpdatedAt] = now;

    if (foundRow > 0) {
      sh.getRange(foundRow, 1, 1, row.length).setValues([row]);
      IAPF_log_("INFO", "ERROR_UPSERT_UPDATE", "Updated ERRORS row", { code });
    } else {
      sh.appendRow(row);
      IAPF_log_("INFO", "ERROR_UPSERT_INSERT", "Inserted ERRORS row", { code });
    }

    return { ok: true };
  } catch (err) {
    IAPF_log_("ERROR", "ERROR_UPSERT_FAIL", String(err && err.stack ? err.stack : err), {});
    return { ok: false, error: String(err) };
  }
}
