/**
 * G12_API_DISPATCH.gs
 * Allowlist dispatcher with dry-run default and confirm_token execution gate.
 * PATCH: add READ-only actions for GPT Desktop (no confirm needed).
 */

var IAPF_DISPATCH = (function () {

  var ALLOWLIST = {
    "INITIALIZE_DAY": true,
    "CLOSE_DAY": true,
    "GENERATE_SNAPSHOT": true,
    "APPEND_MEMORY_ENTRY": true,
    "GLOBAL_AUDIT": true,
    "EXPORT_HUB": true,

    // READ-only
    "READ_MEMORY_LOG": true,
    "READ_SNAPSHOT_ACTIVE": true,
    "READ_HUB_STATUS": true,
    "LIST_ACTIONS": true,

    // READ-only connectors (inspection)
    "RO_DRIVE_TREE": true,
    "RO_DRIVE_FILE_META": true,
    "RO_DRIVE_CHANGES": true,

    "RO_SCRIPT_PROJECT_DETAIL": true,
    "RO_SCRIPT_PROJECT_CONTENT": true,
    "RO_SCRIPT_DEPLOYMENTS": true,
    "RO_SCRIPT_VERSIONS": true,

    "RO_GITHUB_REPOS": true,
    "RO_GITHUB_REPO_DETAIL": true,
    "RO_GITHUB_WORKFLOW_RUNS": true
  };

  var READ_ONLY = {
    "READ_MEMORY_LOG": true,
    "READ_SNAPSHOT_ACTIVE": true,
    "READ_HUB_STATUS": true,
    "LIST_ACTIONS": true,

    // READ-only connectors (inspection)
    "RO_DRIVE_TREE": true,
    "RO_DRIVE_FILE_META": true,
    "RO_DRIVE_CHANGES": true,

    "RO_SCRIPT_PROJECT_DETAIL": true,
    "RO_SCRIPT_PROJECT_CONTENT": true,
    "RO_SCRIPT_DEPLOYMENTS": true,
    "RO_SCRIPT_VERSIONS": true,

    "RO_GITHUB_REPOS": true,
    "RO_GITHUB_REPO_DETAIL": true,
    "RO_GITHUB_WORKFLOW_RUNS": true
  };

  function dispatch(req) {
    const action = String(req.action || "");
    const payload = req.payload || {};
    const confirm = (req.confirm === true);
    const requestId = String(req.request_id || "unknown");
    const mode = IAPF_AUTH.getApiMode_();
    const role = (req && req._auth && req._auth.role) ? String(req._auth.role) : "OPERATOR";

    if (!ALLOWLIST[action]) {
      return build_(false, true, requestId, "API_ACTION_REFUSED", {
        request_id: requestId,
        action: action,
        reason: "Action not allowed"
      }, {
        ok: false,
        mode: mode,
        request_id: requestId,
        dry_run: true,
        errors: [{ code: "ACTION_NOT_ALLOWED", message: "Action not allowed" }]
      });
    }

    // READ-only: execute immediately (auth already done at API layer), still logged.
    if (READ_ONLY[action]) {
      const out = execute_(action, payload, { auth: (req && req._auth) ? req._auth : {} });
      return build_(true, false, requestId, "API_READ_OK", {
        request_id: requestId,
        action: action,
        role: role
      }, {
        ok: true,
        mode: mode,
        request_id: requestId,
        dry_run: false,
        result: out
      });
    }

    // WRITE actions are restricted to OPERATOR role
    if (role !== "OPERATOR") {
      return build_(false, true, requestId, "API_ROLE_REFUSED", {
        request_id: requestId,
        action: action,
        role: role,
        reason: "Role not allowed for write actions"
      }, {
        ok: false,
        mode: mode,
        request_id: requestId,
        dry_run: true,
        errors: [{ code: "ROLE_NOT_ALLOWED", message: "Role not allowed for write actions" }]
      });
    }

    // Build a plan (dry-run) for every WRITE action
    const plan = planFor_(action, payload);

    if (!confirm) {
      const confirmToken = IAPF_AUTH.mintConfirmToken(plan);
      return build_(true, true, requestId, "API_DRY_RUN_PLAN", {
        request_id: requestId,
        action: action,
        plan: plan
      }, {
        ok: true,
        mode: mode,
        request_id: requestId,
        dry_run: true,
        confirm_token: confirmToken,
        result: { plan: plan }
      });
    }

    // confirm=true requires confirm_token and verification
    const ver = IAPF_AUTH.verifyAndConsumeConfirmToken(String(req.confirm_token || ""), plan);
    if (!ver.ok) {
      return build_(false, true, requestId, "API_CONFIRM_REFUSED", {
        request_id: requestId,
        action: action,
        reason: ver.reason
      }, {
        ok: false,
        mode: mode,
        request_id: requestId,
        dry_run: true,
        errors: [{ code: "CONFIRM_REFUSED", message: ver.reason }]
      });
    }

    // Execute now (controlled)
    const exec = execute_(action, payload, { auth: (req && req._auth) ? req._auth : {} });

    return build_(true, false, requestId, "API_EXECUTED", {
      request_id: requestId,
      action: action,
      execution: exec
    }, {
      ok: true,
      mode: mode,
      request_id: requestId,
      dry_run: false,
      result: exec
    });
  }

  function planFor_(action, payload) {
    switch (action) {
      case "INITIALIZE_DAY":
        return { action: action, will_call: "MCP_IMPL_initializeDay", side_effects: ["writes: HUB day state", "writes: MEMORY_LOG"] };
      case "CLOSE_DAY":
        return { action: action, will_call: "MCP_IMPL_closeDay", side_effects: ["writes: HUB day state", "writes: MEMORY_LOG"] };
      case "GENERATE_SNAPSHOT":
        return { action: action, will_call: "IAPF_generateSnapshot", side_effects: ["writes: Drive snapshot", "writes: SNAPSHOT_ACTIVE"] };
      case "APPEND_MEMORY_ENTRY":
        return { action: action, will_call: "IAPF_appendMemoryEntry_", side_effects: ["writes: MEMORY_LOG"], input: sanitizeMemoryPayload_(payload) };
      case "GLOBAL_AUDIT":
        return { action: action, will_call: "MCP_IMPL_globalAudit", side_effects: ["reads: all hub tabs", "writes: audit output tabs"] };
      case "EXPORT_HUB":
        return { action: action, will_call: "MCP_EXPORT_exportHubZipAndSheet", side_effects: ["writes: Drive export ZIP+XLSX"] };
      default:
        return { action: action, will_call: "UNKNOWN" };
    }
  }

  function execute_(action, payload, ctx) {
    ctx = ctx || {};
    switch (action) {

      // WRITE actions
      case "INITIALIZE_DAY":
        return { action: action, output: MCP_IMPL_initializeDay() };
      case "CLOSE_DAY":
        return { action: action, output: MCP_IMPL_closeDay() };
      case "GENERATE_SNAPSHOT":
        return { action: action, output: IAPF_generateSnapshot() };
      case "APPEND_MEMORY_ENTRY": {
        var p = sanitizeMemoryPayload_(payload);
        // Use the canonical writer in your HUB (supports positional & object)
        if (typeof IAPF_appendMemoryEntry_ === "function") {
          IAPF_appendMemoryEntry_(p.type, p.title, p.details, { source: p.source, tags: p.tags, author: p.author, ts_iso: p.ts_iso });
        } else if (typeof IAPF_appendMemoryEntry === "function") {
          IAPF_appendMemoryEntry(p.ts_iso, p.type, p.title, p.details, p.author, p.source, p.tags);
        } else {
          throw new Error("No memory writer found (IAPF_appendMemoryEntry_ / IAPF_appendMemoryEntry)");
        }
        return { action: action, output: "MEMORY_LOG_APPENDED" };
      }
      case "GLOBAL_AUDIT":
        return { action: action, output: MCP_IMPL_globalAudit() };
      case "EXPORT_HUB":
        return { action: action, output: MCP_EXPORT_exportHubZipAndSheet() };

      // READ-only actions
      case "LIST_ACTIONS":
        return {
          allowlist: Object.keys(ALLOWLIST).sort(),
          read_only: Object.keys(READ_ONLY).sort(),
          roles: ["OPERATOR", "AUDITOR"]
        };

      case "READ_MEMORY_LOG":
        return readMemoryLog_(payload);

      case "READ_SNAPSHOT_ACTIVE":
        return readSnapshotActive_(payload);

      case "READ_HUB_STATUS":
        return readHubStatus_();

      // CONNECTORS — Drive
      case "RO_DRIVE_TREE":
        return (typeof IAPF_RO_driveTree_ === "function") ? IAPF_RO_driveTree_(payload) : { error: "Missing IAPF_RO_driveTree_" };
      case "RO_DRIVE_FILE_META":
        return (typeof IAPF_RO_driveFileMeta_ === "function") ? IAPF_RO_driveFileMeta_(payload, (ctx && ctx.auth) ? ctx.auth : {}) : { error: "Missing IAPF_RO_driveFileMeta_" };
      case "RO_DRIVE_CHANGES":
        return (typeof IAPF_RO_driveChanges_ === "function") ? IAPF_RO_driveChanges_(payload) : { error: "Missing IAPF_RO_driveChanges_" };

      // CONNECTORS — Apps Script
      case "RO_SCRIPT_PROJECT_DETAIL":
        return (typeof IAPF_RO_scriptProjectDetail_ === "function") ? IAPF_RO_scriptProjectDetail_(payload) : { error: "Missing IAPF_RO_scriptProjectDetail_" };
      case "RO_SCRIPT_PROJECT_CONTENT":
        return (typeof IAPF_RO_scriptProjectContent_ === "function") ? IAPF_RO_scriptProjectContent_(payload) : { error: "Missing IAPF_RO_scriptProjectContent_" };
      case "RO_SCRIPT_DEPLOYMENTS":
        return (typeof IAPF_RO_scriptDeployments_ === "function") ? IAPF_RO_scriptDeployments_(payload) : { error: "Missing IAPF_RO_scriptDeployments_" };
      case "RO_SCRIPT_VERSIONS":
        return (typeof IAPF_RO_scriptVersions_ === "function") ? IAPF_RO_scriptVersions_(payload) : { error: "Missing IAPF_RO_scriptVersions_" };

      // CONNECTORS — GitHub
      case "RO_GITHUB_REPOS":
        return (typeof IAPF_RO_githubRepos_ === "function") ? IAPF_RO_githubRepos_(payload) : { error: "Missing IAPF_RO_githubRepos_" };
      case "RO_GITHUB_REPO_DETAIL":
        return (typeof IAPF_RO_githubRepoDetail_ === "function") ? IAPF_RO_githubRepoDetail_(payload) : { error: "Missing IAPF_RO_githubRepoDetail_" };
      case "RO_GITHUB_WORKFLOW_RUNS":
        return (typeof IAPF_RO_githubWorkflowRuns_ === "function") ? IAPF_RO_githubWorkflowRuns_(payload) : { error: "Missing IAPF_RO_githubWorkflowRuns_" };

      default:
        throw new Error("Action not executable: " + action);
    }
  }

  function readMemoryLog_(payload) {
    var p = payload || {};
    // Backward compatible paging:
    // - legacy: { limit, offset }
    // - new:    { page_size, cursor }
    var limit = clamp_(Number(p.page_size || p.limit || 50), 1, 200);
    var offset = Math.max(0, Number(p.offset || 0));
    if (p.cursor) {
      var decoded = decodeCursorOffset_(String(p.cursor || ""));
      if (!isNaN(decoded)) offset = Math.max(0, decoded);
    }
    var reverse = (p.reverse !== false); // default true

    var sh = getSheetByKey_("MEMORY_LOG");
    var lastRow = sh.getLastRow();
    if (lastRow < 2) {
      return { rows: [], count: 0, limit: limit, offset: offset, reverse: reverse };
    }

    // Read all rows then slice (safe enough; capped by limit+offset, but we keep simple & stable)
    var data = sh.getRange(2, 1, lastRow - 1, 7).getValues();
    if (reverse) data.reverse();

    var sliced = data.slice(offset, offset + limit);

    var rows = sliced.map(function (r) {
      return {
        ts_iso: String(r[0] || ""),
        type: String(r[1] || ""),
        title: String(r[2] || ""),
        details: String(r[3] || ""),
        author: String(r[4] || ""),
        source: String(r[5] || ""),
        tags: String(r[6] || "")
      };
    });

    var nextOffset = offset + rows.length;
    var nextCursor = (nextOffset < data.length) ? encodeCursorOffset_(nextOffset) : "";

    return {
      rows: rows,
      count: data.length,
      limit: limit,
      page_size: limit,
      offset: offset,
      reverse: reverse,
      next_cursor: nextCursor
    };
  }

  function encodeCursorOffset_(offset) {
    try {
      var json = JSON.stringify({ o: Number(offset || 0) });
      return Utilities.base64EncodeWebSafe(json);
    } catch (e) {
      return "";
    }
  }

  function decodeCursorOffset_(cursor) {
    try {
      var json = Utilities.newBlob(Utilities.base64DecodeWebSafe(cursor)).getDataAsString();
      var obj = JSON.parse(json || "{}");
      return Number(obj.o || 0);
    } catch (e) {
      return NaN;
    }
  }

  function readSnapshotActive_(payload) {
    var sh = getSheetByKey_("SNAPSHOT_ACTIVE");
    var lastRow = sh.getLastRow();
    var lastCol = sh.getLastColumn();
    if (lastRow < 1 || lastCol < 1) return { values: [] };

    var maxRows = clamp_(Number((payload || {}).max_rows || 20), 1, 200);
    var maxCols = clamp_(Number((payload || {}).max_cols || 10), 1, 50);

    var r = Math.min(lastRow, maxRows);
    var c = Math.min(lastCol, maxCols);

    var values = sh.getRange(1, 1, r, c).getValues();
    return { values: values, rows: r, cols: c };
  }

  function readHubStatus_() {
    var keys = ["MEMORY_LOG", "SNAPSHOT_ACTIVE", "DEPENDANCES_SCRIPTS", "CARTOGRAPHIE_APPELS", "REGLES_DE_GOUVERNANCE", "RISKS", "CONFLITS_DETECTES"];
    var out = {};
    keys.forEach(function (k) {
      try {
        var sh = getSheetByKey_(k);
        out[k] = { ok: true, name: sh.getName() };
      } catch (e) {
        out[k] = { ok: false, error: String(e && e.message ? e.message : e) };
      }
    });
    return out;
  }

  function getSheetByKey_(key) {
    if (typeof IAPF_SHEETS !== "undefined" && IAPF_SHEETS && typeof IAPF_SHEETS.getSheet_ === "function") {
      return IAPF_SHEETS.getSheet_(key);
    }
    // fallback: direct name
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sh = ss.getSheetByName(String(key));
    if (!sh) throw new Error("Sheet not found: " + key);
    return sh;
  }

  function clamp_(n, min, max) {
    if (isNaN(n)) return min;
    return Math.max(min, Math.min(max, n));
  }

  function sanitizeMemoryPayload_(payload) {
    var p = payload || {};
    return {
      ts_iso: String(p.ts_iso || new Date().toISOString()),
      type: String(p.type || "CONSTAT"),
      title: String(p.title || "API_ENTRY"),
      details: String(p.details || "{}"),
      author: String(p.author || (Session.getActiveUser().getEmail() || "system")),
      source: String(p.source || "API"),
      tags: String(p.tags || "IAPF;MCP;API")
    };
  }

  function build_(ok, dryRun, requestId, logTitle, logDetails, response) {
    return {
      ok: ok,
      dry_run: dryRun,
      log_title: logTitle,
      log_details: logDetails,
      response: response
    };
  }

  return {
    dispatch: dispatch
  };

})();
