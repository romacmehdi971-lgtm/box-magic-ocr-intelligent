// File: /CODE/04_DRIVE_IO.gs

function IAPF_inventoryDrive() {
  const ui = SpreadsheetApp.getUi();
  const res = IAPF_inventoryDrive_();
  if (!res.ok) {
    ui.alert("Inventaire Drive: ERREUR", res.error || "Unknown error", ui.ButtonSet.OK);
    return;
  }
  ui.alert("Inventaire Drive: OK", res.summary || "(voir LOGS / DRIVE_INVENTORY)", ui.ButtonSet.OK);
}

function IAPF_inventoryDrive_() {
  try {
    IAPF_initHub_({ quiet: true });

    // 1) Root folder (OBLIGATOIRE)
    const rootId = IAPF_getConfig_("memory_root_folder_id");
    if (!rootId) {
      return { ok: false, error: "memory_root_folder_id non configuré (onglet SETTINGS)" };
    }

    // 2) Paramètres scan (sécurités Apps Script)
    const started = Date.now();
    const TIME_BUDGET_MS = 4.5 * 60 * 1000; // < 6 min, marge de sécurité
    const MAX_FOLDERS = 5000;               // garde-fou
    const MAX_FILES_PER_FOLDER = 0;         // 0 = ne pas lister les fichiers (focus architecture)
    const MAX_DEPTH = 30;                   // garde-fou
    const runId = IAPF_nowIso_().replace(/[:.]/g, "-");

    // 3) Scan BFS (folders)
    const rootFolder = DriveApp.getFolderById(rootId);
    const rootName = rootFolder.getName();

    const rows = [];
    const header = ["run_id", "ts_iso", "depth", "kind", "name", "id", "url", "parent_id", "path"];

    // Always include root
    rows.push([
      runId,
      IAPF_nowIso_(),
      0,
      "FOLDER",
      rootName,
      rootId,
      rootFolder.getUrl(),
      "",
      "/" + rootName
    ]);

    const queue = [{ folder: rootFolder, depth: 0, path: "/" + rootName, parentId: "" }];
    let foldersCount = 1;
    let filesCount = 0;

    while (queue.length > 0) {
      if (Date.now() - started > TIME_BUDGET_MS) break;
      if (foldersCount >= MAX_FOLDERS) break;

      const cur = queue.shift();
      if (cur.depth >= MAX_DEPTH) continue;

      // Subfolders
      const sub = cur.folder.getFolders();
      while (sub.hasNext()) {
        if (Date.now() - started > TIME_BUDGET_MS) break;
        if (foldersCount >= MAX_FOLDERS) break;

        const f = sub.next();
        const id = f.getId();
        const name = f.getName();
        const url = f.getUrl();
        const depth = cur.depth + 1;
        const path = cur.path + "/" + name;

        rows.push([runId, IAPF_nowIso_(), depth, "FOLDER", name, id, url, cur.folder.getId(), path]);
        foldersCount++;

        queue.push({ folder: f, depth, path, parentId: cur.folder.getId() });
      }

      // Files (optionnel)
      if (MAX_FILES_PER_FOLDER > 0) {
        const files = cur.folder.getFiles();
        let c = 0;
        while (files.hasNext() && c < MAX_FILES_PER_FOLDER) {
          if (Date.now() - started > TIME_BUDGET_MS) break;
          const fi = files.next();
          rows.push([
            runId,
            IAPF_nowIso_(),
            cur.depth + 1,
            "FILE",
            fi.getName(),
            fi.getId(),
            fi.getUrl(),
            cur.folder.getId(),
            cur.path + "/" + fi.getName()
          ]);
          filesCount++;
          c++;
        }
      }
    }

    const timedOut = (Date.now() - started > TIME_BUDGET_MS);
    const clipped = (foldersCount >= MAX_FOLDERS);

    // 4) Ecriture onglet DRIVE_INVENTORY (clear + write)
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const invSheetName = "DRIVE_INVENTORY";
    const invSheet = IAPF_getOrCreateSheet_(ss, invSheetName);

    invSheet.clearContents();
    invSheet.getRange(1, 1, 1, header.length).setValues([header]);
    if (rows.length > 0) {
      invSheet.getRange(2, 1, rows.length, header.length).setValues(rows);
    }
    invSheet.autoResizeColumns(1, header.length);

    // 5) Vérif gouvernance : template canonique racine
    const expected = [
      "00_GOUVERNANCE",
      "01_BOX_CENTRALE",
      "02_PRODUCTION",
      "03_CLIENTS",
      "04_ENTREPRISE_IAPF",
      "05_COMPTABILITE",
      "06_DIGITAL",
      "07_ACCES_PROTEGES",
      "08_TESTS_LAB",
      "09_ARCHIVES",
      "99_LEGACY_HORS_SYSTEME"
    ];

    const present = {};
    expected.forEach(n => present[n] = { found: false, id: "", url: "" });

    // On ne check que le niveau 1 sous la racine
    const top = rootFolder.getFolders();
    while (top.hasNext()) {
      const f = top.next();
      const n = f.getName();
      if (present[n]) {
        present[n].found = true;
        present[n].id = f.getId();
        present[n].url = f.getUrl();
      }
    }

    const govHeader = ["run_id", "ts_iso", "expected_folder", "present", "folder_id", "folder_url"];
    const govRows = expected.map(n => [
      runId,
      IAPF_nowIso_(),
      n,
      present[n].found ? "YES" : "NO",
      present[n].id,
      present[n].url
    ]);

    const govSheetName = "DRIVE_GOV_CHECK";
    const govSheet = IAPF_getOrCreateSheet_(ss, govSheetName);
    govSheet.clearContents();
    govSheet.getRange(1, 1, 1, govHeader.length).setValues([govHeader]);
    govSheet.getRange(2, 1, govRows.length, govHeader.length).setValues(govRows);
    govSheet.autoResizeColumns(1, govHeader.length);

    // 6) Snapshot texte opposable
    const missing = expected.filter(n => !present[n].found);
    const okCount = expected.length - missing.length;

    const snapshotLines = [];
    snapshotLines.push("IAPF — DRIVE INVENTORY SNAPSHOT");
    snapshotLines.push(`generated: ${IAPF_nowIso_()}`);
    snapshotLines.push(`run_id: ${runId}`);
    snapshotLines.push("");
    snapshotLines.push("ROOT");
    snapshotLines.push(`- name: ${rootName}`);
    snapshotLines.push(`- id: ${rootId}`);
    snapshotLines.push(`- url: ${rootFolder.getUrl()}`);
    snapshotLines.push("");
    snapshotLines.push("STATS");
    snapshotLines.push(`- folders_scanned: ${foldersCount}`);
    snapshotLines.push(`- files_listed: ${filesCount}`);
    snapshotLines.push(`- time_budget_hit: ${timedOut ? "YES" : "NO"}`);
    snapshotLines.push(`- max_folders_hit: ${clipped ? "YES" : "NO"}`);
    snapshotLines.push("");
    snapshotLines.push("GOV CHECK (ROOT TEMPLATE)");
    snapshotLines.push(`- expected: ${expected.length}`);
    snapshotLines.push(`- present: ${okCount}`);
    snapshotLines.push(`- missing: ${missing.length}`);
    missing.forEach(n => snapshotLines.push(`  - MISSING: ${n}`));
    snapshotLines.push("");
    snapshotLines.push("NOTES");
    snapshotLines.push("- DRIVE_INVENTORY + DRIVE_GOV_CHECK écrits dans le Hub.");
    snapshotLines.push("- Scan lecture seule (aucune création/suppression de dossiers).");

    const snapshotText = snapshotLines.join("\n");
    const snapRes = IAPF_createDriveSnapshotIfConfigured_(snapshotText);

    // 7) Logs
    IAPF_log_("INFO", "DRIVE_SCAN_DONE", "Drive scan completed", {
      runId,
      rootId,
      foldersCount,
      filesCount,
      timedOut,
      clipped,
      missing_root_folders: missing
    });

    // 8) Summary UI
    const summaryLines = [];
    summaryLines.push(`run_id: ${runId}`);
    summaryLines.push(`Racine: ${rootName}`);
    summaryLines.push(`Dossiers scannés: ${foldersCount}`);
    summaryLines.push(`Check gouvernance (racine): ${okCount}/${expected.length} OK`);
    if (missing.length) summaryLines.push(`Manquants: ${missing.join(", ")}`);
    if (timedOut) summaryLines.push("ATTENTION: time budget atteint (scan partiel).");
    if (clipped) summaryLines.push("ATTENTION: MAX_FOLDERS atteint (scan partiel).");
    if (snapRes && snapRes.ok && snapRes.fileId) summaryLines.push(`Snapshot Drive: OK (${snapRes.fileId})`);

    return { ok: true, summary: summaryLines.join("\n") };
  } catch (err) {
    IAPF_log_("ERROR", "DRIVE_SCAN_FAIL", String(err && err.stack ? err.stack : err), {});
    return { ok: false, error: String(err) };
  }
}

function IAPF_createDriveSnapshotIfConfigured_(snapshotText) {
  try {
    const snapshotsFolderId = IAPF_getConfig_("snapshots_folder_id");
    if (!snapshotsFolderId) {
      return { ok: false, error: "snapshots_folder_id non configuré" };
    }

    const folder = DriveApp.getFolderById(snapshotsFolderId);
    const ts = IAPF_nowIso_().replace(/[:.]/g, "-");
    const name = `IAPF_DRIVE_SCAN_${ts}.txt`;

    const file = folder.createFile(name, snapshotText, MimeType.PLAIN_TEXT);
    IAPF_log_("INFO", "SNAPSHOT_DRIVE_CREATED", "Created snapshot file in Drive", { name, id: file.getId() });

    return { ok: true, fileId: file.getId() };
  } catch (err) {
    IAPF_log_("WARN", "SNAPSHOT_DRIVE_CREATE_FAIL", String(err), {});
    return { ok: false, error: String(err) };
  }
}

function IAPF_ensureDriveFoldersConfigured_() {
  const ui = SpreadsheetApp.getUi();

  let rootId = IAPF_getConfig_("memory_root_folder_id");
  if (!rootId) {
    const resp = ui.prompt(
      "Configuration Drive requise",
      "Colle memory_root_folder_id (dossier Drive racine mémoire).",
      ui.ButtonSet.OK_CANCEL
    );
    if (resp.getSelectedButton() !== ui.Button.OK) return { ok: false, error: "Configuration annulée" };
    rootId = (resp.getResponseText() || "").trim();
    if (!rootId) return { ok: false, error: "memory_root_folder_id vide" };
    IAPF_setConfig_("memory_root_folder_id", rootId);
  }

  const rootFolder = DriveApp.getFolderById(rootId);

  let snapshotsId = IAPF_getConfig_("snapshots_folder_id");
  if (!snapshotsId) {
    const existing = IAPF_findChildFolderByName_(rootFolder, "Mémoire — Snapshots");
    const folder = existing || rootFolder.createFolder("Mémoire — Snapshots");
    snapshotsId = folder.getId();
    IAPF_setConfig_("snapshots_folder_id", snapshotsId);
  }

  let logsId = IAPF_getConfig_("logs_folder_id");
  if (!logsId) {
    const existing = IAPF_findChildFolderByName_(rootFolder, "Mémoire — Logs");
    const folder = existing || rootFolder.createFolder("Mémoire — Logs");
    logsId = folder.getId();
    IAPF_setConfig_("logs_folder_id", logsId);
  }

  return { ok: true, rootId, snapshotsId, logsId };
}

function IAPF_findChildFolderByName_(parentFolder, name) {
  const it = parentFolder.getFoldersByName(name);
  if (it.hasNext()) return it.next();
  return null;
}

function IAPF_getOrCreateSheet_(ss, name) {
  let sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name);
  return sh;
}
