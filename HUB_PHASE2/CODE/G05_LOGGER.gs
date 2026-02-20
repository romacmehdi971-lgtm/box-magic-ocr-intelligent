// File: /CODE/05_LOGGER.gs

function IAPF_log_(level, event, message, data) {
  try {
    const ss = IAPF_getActiveSS_();
    const sh = ss.getSheetByName(IAPF.LOGS_SHEET);
    if (!sh) return;

    const payload = data ? JSON.stringify(data).slice(0, 45000) : "";
    sh.appendRow([IAPF_nowIso_(), String(level || "INFO"), String(event || ""), String(message || ""), payload]);
  } catch (err) {
    // last resort: do nothing
  }
}
