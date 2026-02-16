// File: /CODE/02_SNAPSHOT_ENGINE.gs

function IAPF_generateSnapshot() {
  const op = IAPF_generateSnapshot_();
  const ui = SpreadsheetApp.getUi();
  if (!op.ok) {
    ui.alert("Snapshot: ERREUR", op.error || "Unknown error", ui.ButtonSet.OK);
    return;
  }
  ui.alert("Snapshot: OK", "SNAPSHOT_ACTIVE mis à jour. Snapshot Drive créé si configuré.", ui.ButtonSet.OK);
}

function IAPF_exportContextPack() {
  const op = IAPF_buildContextPack_();
  const ui = SpreadsheetApp.getUi();
  if (!op.ok) {
    ui.alert("Context Pack: ERREUR", op.error || "Unknown error", ui.ButtonSet.OK);
    return;
  }
  ui.alert("CONTEXT PACK", op.text || "(vide)", ui.ButtonSet.OK);
}

function IAPF_generateSnapshot_() {
  try {
    IAPF_initHub_({ quiet: true });

    const memItems = IAPF_readLastMemoryEntries_(IAPF.MAX_MEMORY_ITEMS);
    const errors = IAPF_readErrorsActive_();
    const roadmapHint = IAPF_getRoadmapHint_();

    const lines = [];
    lines.push(`IAPF — SNAPSHOT ACTIF`);
    lines.push(`generated: ${IAPF_nowIso_()}`);
    lines.push("");

    lines.push("CONTEXTE ACTIF");
    const ctxLines = IAPF_buildContextLines_(memItems, roadmapHint);
    ctxLines.forEach(l => lines.push(l));
    if (!ctxLines.length) lines.push("- (aucune entrée mémoire récente)");

    lines.push("");
    lines.push("RÈGLES & ERREURS ACTIVES");
    const ruleErrLines = IAPF_buildRulesErrorsLines_(errors);
    ruleErrLines.forEach(l => lines.push(l));
    if (!ruleErrLines.length) lines.push("- (aucune erreur active)");

    const snapshotText = lines.join("\n").trim();

    IAPF_writeSnapshotActive_(snapshotText);

    const ioRes = IAPF_createDriveSnapshotIfConfigured_(snapshotText);
    if (!ioRes.ok) {
      IAPF_log_("WARN", "SNAPSHOT_DRIVE_NOT_CREATED", ioRes.error || "Drive snapshot not created", {});
    }

    return { ok: true };
  } catch (err) {
    IAPF_log_("ERROR", "SNAPSHOT_FAIL", String(err && err.stack ? err.stack : err), {});
    return { ok: false, error: String(err) };
  }
}

function IAPF_buildContextPack_() {
  try {
    IAPF_initHub_({ quiet: true });

    const memItems = IAPF_readLastMemoryEntries_(IAPF.MAX_MEMORY_ITEMS);
    const errors = IAPF_readErrorsActive_();
    const roadmapHint = IAPF_getRoadmapHint_();

    const lines = [];
    lines.push("CONTEXT PACK — IAPF");
    lines.push(`generated: ${IAPF_nowIso_()}`);
    lines.push("");
    lines.push("1) CONTEXTE ACTIF");
    const ctxLines = IAPF_buildContextLines_(memItems, roadmapHint, IAPF.MAX_LINES_CONTEXT);
    ctxLines.forEach(l => lines.push(l));
    if (!ctxLines.length) lines.push("- (aucune entrée mémoire récente)");
    lines.push("");
    lines.push("2) RÈGLES & ERREURS ACTIVES");
    const ruleErrLines = IAPF_buildRulesErrorsLines_(errors, 12);
    ruleErrLines.forEach(l => lines.push(l));
    if (!ruleErrLines.length) lines.push("- (aucune erreur active)");

    const text = lines.join("\n").trim();
    return { ok: true, text };
  } catch (err) {
    IAPF_log_("ERROR", "CONTEXT_PACK_FAIL", String(err && err.stack ? err.stack : err), {});
    return { ok: false, error: String(err) };
  }
}

function IAPF_buildContextLines_(memItems, roadmapHint, limit) {
  const out = [];
  const max = limit || IAPF.MAX_LINES_CONTEXT;

  if (roadmapHint) {
    out.push(`- Roadmap liée: ${roadmapHint}`);
  }

  memItems.slice(0, max).forEach((it) => {
    const t = (it.type || "").toUpperCase();
    const title = it.title || "";
    const ts = it.ts_iso || "";
    out.push(`- [${t}] ${title} (${ts})`);
  });

  return out.slice(0, max);
}

function IAPF_buildRulesErrorsLines_(errors, limit) {
  const out = [];
  const max = limit || 20;
  errors.slice(0, max).forEach((e) => {
    out.push(`- ${e.code}: ${e.title} — ${e.status}`);
  });
  return out.slice(0, max);
}

function IAPF_writeSnapshotActive_(snapshotText) {
  const ss = IAPF_getActiveSS_();
  const sh = ss.getSheetByName(IAPF.SNAPSHOT_SHEET);

  sh.getRange(2, 1, Math.max(1, sh.getLastRow() - 1), 2).clearContent();

  const ts = IAPF_nowIso_();
  sh.getRange(2, 1).setValue(ts);
  sh.getRange(2, 2).setValue(snapshotText);

  sh.setColumnWidths(1, 1, 220);
  sh.setColumnWidths(2, 1, 900);
  sh.getRange(1, 1, 1, 2).setFontWeight("bold");
  sh.getRange(2, 2).setWrap(true);
}
