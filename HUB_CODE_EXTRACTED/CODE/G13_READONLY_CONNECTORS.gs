/**
 * G13_READONLY_CONNECTORS.gs
 *
 * READ-ONLY Connectors for inspection (Apps Script / Drive / GitHub).
 * Goal: enable MCP to audit environments without external console.
 *
 * Governance:
 * - No destructive operation.
 * - Pagination via cursor tokens.
 * - Minimal payloads by default (avoid giant responses).
 * - Secrets NEVER returned.
 */

/** =========================
 *  Helpers
 *  ========================= */

function IAPF_RO_getSetting_(key) {
  try {
    if (typeof IAPF_getConfig_ === "function") return String(IAPF_getConfig_(String(key)) || "");
  } catch (e) {}

  // Fallback: SETTINGS sheet (col A=key, col B=value)
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sh = ss.getSheetByName("SETTINGS");
    if (!sh) return "";
    var last = sh.getLastRow();
    if (last < 2) return "";
    var data = sh.getRange(2, 1, last - 1, 2).getValues();
    for (var i = 0; i < data.length; i++) {
      if (String(data[i][0] || "").trim() === String(key).trim()) {
        return String(data[i][1] || "").trim();
      }
    }
  } catch (e2) {}

  return "";
}

function IAPF_RO_clamp_(n, min, max) {
  n = Number(n);
  if (isNaN(n)) n = min;
  return Math.max(min, Math.min(max, n));
}

function IAPF_RO_encodeCursor_(obj) {
  try {
    return Utilities.base64EncodeWebSafe(JSON.stringify(obj || {}));
  } catch (e) {
    return "";
  }
}

function IAPF_RO_decodeCursor_(cursor) {
  try {
    if (!cursor) return null;
    var json = Utilities.newBlob(Utilities.base64DecodeWebSafe(String(cursor))).getDataAsString();
    return JSON.parse(json || "{}");
  } catch (e) {
    return null;
  }
}

function IAPF_RO_sha256_(text) {
  try {
    var bytes = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, String(text || ""), Utilities.Charset.UTF_8);
    return bytes.map(function (b) {
      var v = (b < 0) ? b + 256 : b;
      var h = v.toString(16);
      return h.length === 1 ? "0" + h : h;
    }).join("");
  } catch (e) {
    return "";
  }
}

/** =========================
 *  Drive
 *  ========================= */

function IAPF_RO_driveListChildren_(parentId, pageToken, pageSize) {
  var args = {
    q: "'" + String(parentId) + "' in parents and trashed = false",
    pageSize: IAPF_RO_clamp_(pageSize || 100, 1, 200),
    fields: "nextPageToken,files(id,name,mimeType,parents,modifiedTime,createdTime,size,md5Checksum,webViewLink,trashed)"
  };
  if (pageToken) args.pageToken = String(pageToken);

  // Advanced Drive service (Drive API v3) is enabled in appsscript.json
  return Drive.Files.list(args);
}

function IAPF_RO_driveTree_(payload) {
  var p = payload || {};

  // Defaults grounded in existing SETTINGS
  var rootId = String(p.root_id || IAPF_RO_getSetting_("memory_root_folder_id") || "");
  if (!rootId) {
    return { ok: false, error: "Missing root_id and SETTINGS.memory_root_folder_id" };
  }

  var maxDepth = IAPF_RO_clamp_(p.max_depth || 2, 0, 10);
  var maxItems = IAPF_RO_clamp_(p.max_items || 200, 1, 500);
  var pageSize = IAPF_RO_clamp_(p.page_size || 100, 1, 200);

  // Cursor state
  // { q: [{id,depth}], idx, pageToken }
  var state = IAPF_RO_decodeCursor_(p.cursor) || { q: [{ id: rootId, depth: 0 }], idx: 0, pageToken: "" };
  if (!state.q || !state.q.length) state = { q: [{ id: rootId, depth: 0 }], idx: 0, pageToken: "" };

  var out = [];
  var safety = 0;

  while (out.length < maxItems && state.idx < state.q.length && safety < 1000) {
    safety++;

    var node = state.q[state.idx];
    var parentId = String(node.id);
    var depth = Number(node.depth || 0);

    // Always list children for current node
    var resp = IAPF_RO_driveListChildren_(parentId, state.pageToken || "", pageSize);
    var files = (resp && resp.files) ? resp.files : [];

    files.forEach(function (f) {
      var mime = String(f.mimeType || "");
      var isFolder = (mime === "application/vnd.google-apps.folder");

      out.push({
        id: String(f.id || ""),
        name: String(f.name || ""),
        mimeType: mime,
        isFolder: isFolder,
        parentId: parentId,
        depth: depth + 1,
        modifiedTime: String(f.modifiedTime || ""),
        createdTime: String(f.createdTime || ""),
        size: (f.size !== undefined && f.size !== null) ? String(f.size) : "",
        md5Checksum: String(f.md5Checksum || ""),
        webViewLink: String(f.webViewLink || ""),
        trashed: !!f.trashed
      });

      // Expand queue (folders only) within maxDepth
      if (isFolder && (depth + 1) <= maxDepth) {
        state.q.push({ id: String(f.id), depth: depth + 1 });
      }
    });

    // Pagination handling for current folder
    if (resp && resp.nextPageToken) {
      state.pageToken = String(resp.nextPageToken);
    } else {
      state.idx = Number(state.idx || 0) + 1;
      state.pageToken = "";
    }

    if (out.length >= maxItems) break;
  }

  var nextCursor = (state.idx < state.q.length) ? IAPF_RO_encodeCursor_(state) : "";

  return {
    ok: true,
    root_id: rootId,
    max_depth: maxDepth,
    returned: out.length,
    items: out,
    next_cursor: nextCursor
  };
}

function IAPF_RO_driveFileMeta_(payload, auth) {
  var p = payload || {};
  var role = (auth && auth.role) ? String(auth.role) : "OPERATOR";

  var fileId = String(p.file_id || "");
  if (!fileId) return { ok: false, error: "Missing file_id" };

  var fields = "id,name,mimeType,parents,owners,createdTime,modifiedTime,size,md5Checksum,webViewLink,iconLink,trashed";
  var meta = Drive.Files.get(fileId, { fields: fields });

  var out = {
    id: String(meta.id || ""),
    name: String(meta.name || ""),
    mimeType: String(meta.mimeType || ""),
    parents: meta.parents || [],
    createdTime: String(meta.createdTime || ""),
    modifiedTime: String(meta.modifiedTime || ""),
    size: (meta.size !== undefined && meta.size !== null) ? String(meta.size) : "",
    md5Checksum: String(meta.md5Checksum || ""),
    webViewLink: String(meta.webViewLink || ""),
    iconLink: String(meta.iconLink || ""),
    trashed: !!meta.trashed
  };

  // Owners: redact email addresses by default (AUDITOR always redacted)
  var owners = meta.owners || [];
  out.owners = owners.map(function (o) {
    return {
      displayName: String(o.displayName || ""),
      permissionId: String(o.permissionId || ""),
      // emailAddress only for OPERATOR if explicitly asked
      emailAddress: (role === "OPERATOR" && p.include_emails === true) ? String(o.emailAddress || "") : ""
    };
  });

  // Optional permissions list (redacted by default)
  if (p.include_permissions === true) {
    try {
      var permResp = Drive.Permissions.list(fileId, {
        fields: "permissions(id,type,role,domain,allowFileDiscovery,deleted,displayName,emailAddress)"
      });
      var perms = (permResp && permResp.permissions) ? permResp.permissions : [];

      out.permissions = perms.map(function (x) {
        return {
          id: String(x.id || ""),
          type: String(x.type || ""),
          role: String(x.role || ""),
          domain: String(x.domain || ""),
          allowFileDiscovery: !!x.allowFileDiscovery,
          deleted: !!x.deleted,
          displayName: String(x.displayName || ""),
          emailAddress: (role === "OPERATOR" && p.include_emails === true) ? String(x.emailAddress || "") : ""
        };
      });
    } catch (e) {
      out.permissions_error = String(e && e.message ? e.message : e);
    }
  }

  return { ok: true, file: out };
}

function IAPF_RO_driveChanges_(payload) {
  var p = payload || {};
  var maxItems = IAPF_RO_clamp_(p.max_items || 100, 1, 200);

  // Cursor state: { pageToken, startPageToken }
  var state = IAPF_RO_decodeCursor_(p.cursor) || {};

  var startPageToken = String(p.start_page_token || state.startPageToken || "");
  var pageToken = String(p.page_token || state.pageToken || "");

  if (!pageToken) {
    if (!startPageToken) {
      // Create a new startPageToken
      var spt = Drive.Changes.getStartPageToken();
      startPageToken = String(spt.startPageToken || "");
    }
    pageToken = startPageToken;
  }

  var resp = Drive.Changes.list(pageToken, {
    pageSize: maxItems,
    fields: "newStartPageToken,nextPageToken,changes(fileId,time,removed,file(id,name,mimeType,parents,modifiedTime,trashed))"
  });

  var changes = (resp && resp.changes) ? resp.changes : [];
  var items = changes.map(function (c) {
    var f = c.file || {};
    return {
      fileId: String(c.fileId || ""),
      time: String(c.time || ""),
      removed: !!c.removed,
      file: f ? {
        id: String(f.id || ""),
        name: String(f.name || ""),
        mimeType: String(f.mimeType || ""),
        parents: f.parents || [],
        modifiedTime: String(f.modifiedTime || ""),
        trashed: !!f.trashed
      } : null
    };
  });

  var next = "";
  if (resp && resp.nextPageToken) {
    next = IAPF_RO_encodeCursor_({
      startPageToken: startPageToken,
      pageToken: String(resp.nextPageToken)
    });
  }

  return {
    ok: true,
    start_page_token: startPageToken,
    new_start_page_token: String(resp && resp.newStartPageToken ? resp.newStartPageToken : ""),
    returned: items.length,
    changes: items,
    next_cursor: next
  };
}

/** =========================
 *  Apps Script (script.googleapis.com)
 *  ========================= */

function IAPF_RO_scriptApiGet_(path, query) {
  var base = "https://script.googleapis.com/v1";
  var url = base + String(path || "");

  var q = query || {};
  var parts = [];
  Object.keys(q).forEach(function (k) {
    if (q[k] === undefined || q[k] === null || q[k] === "") return;
    parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(String(q[k])));
  });
  if (parts.length) url += (url.indexOf("?") === -1 ? "?" : "&") + parts.join("&");

  var token = ScriptApp.getOAuthToken();
  var resp = UrlFetchApp.fetch(url, {
    method: "get",
    muteHttpExceptions: true,
    headers: {
      Authorization: "Bearer " + token
    }
  });

  var status = resp.getResponseCode();
  var text = resp.getContentText() || "";
  if (status < 200 || status >= 300) {
    return { ok: false, http: status, error: text.substring(0, 2000) };
  }

  try {
    return { ok: true, data: JSON.parse(text || "{}") };
  } catch (e) {
    return { ok: true, data: { raw: text } };
  }
}

function IAPF_RO_resolveScriptId_(payload) {
  var p = payload || {};
  var target = String(p.target || "HUB").toUpperCase();

  if (p.script_id) return String(p.script_id);

  if (target === "HUB") {
    return ScriptApp.getScriptId();
  }

  if (target === "BOX2026") {
    var id = IAPF_RO_getSetting_("box2026_script_id");
    return String(id || "");
  }

  return "";
}

function IAPF_RO_scriptProjectDetail_(payload) {
  var scriptId = IAPF_RO_resolveScriptId_(payload);
  if (!scriptId) return { ok: false, error: "Missing script_id and cannot resolve target" };

  var res = IAPF_RO_scriptApiGet_("/projects/" + encodeURIComponent(scriptId), {});
  if (!res.ok) return res;

  // Return only stable fields
  var d = res.data || {};
  return {
    ok: true,
    script_id: scriptId,
    title: String(d.title || ""),
    parentId: String(d.parentId || ""),
    updateTime: String(d.updateTime || ""),
    createTime: String(d.createTime || "")
  };
}

function IAPF_RO_scriptProjectContent_(payload) {
  var p = payload || {};
  var scriptId = IAPF_RO_resolveScriptId_(p);
  if (!scriptId) return { ok: false, error: "Missing script_id and cannot resolve target" };
  var maxFiles = IAPF_RO_clamp_(p.max_files || 200, 1, 500);

  var res = IAPF_RO_scriptApiGet_("/projects/" + encodeURIComponent(scriptId) + "/content", {});
  if (!res.ok) return res;

  var files = (res.data && res.data.files) ? res.data.files : [];
  files = files.slice(0, maxFiles);

  var outFiles = files.map(function (f) {
    var name = String(f.name || "");
    var type = String(f.type || "");
    var source = (f.source !== undefined && f.source !== null) ? String(f.source) : "";
    var hash = IAPF_RO_sha256_(source);

    return {
      name: name,
      type: type,
      sha256: hash
    };
  });

  return {
    ok: true,
    script_id: scriptId,
    returned: outFiles.length,
    files: outFiles
  };
}

function IAPF_RO_scriptDeployments_(payload) {
  var p = payload || {};
  var scriptId = IAPF_RO_resolveScriptId_(p);
  if (!scriptId) return { ok: false, error: "Missing script_id and cannot resolve target" };

  var pageSize = IAPF_RO_clamp_(p.page_size || 50, 1, 100);
  var cursor = IAPF_RO_decodeCursor_(p.cursor) || {};
  var pageToken = String(p.page_token || cursor.pageToken || "");

  var res = IAPF_RO_scriptApiGet_("/projects/" + encodeURIComponent(scriptId) + "/deployments", {
    pageSize: pageSize,
    pageToken: pageToken
  });
  if (!res.ok) return res;

  var d = res.data || {};
  var deployments = (d.deployments || []).map(function (x) {
    return {
      deploymentId: String(x.deploymentId || ""),
      updateTime: String(x.updateTime || ""),
      // manifestFileName is stable and helps debug without leaking config
      manifestFileName: (x.deploymentConfig && x.deploymentConfig.manifestFileName) ? String(x.deploymentConfig.manifestFileName) : "",
      versionNumber: (x.deploymentConfig && x.deploymentConfig.versionNumber !== undefined) ? String(x.deploymentConfig.versionNumber) : ""
    };
  });

  var next = "";
  if (d.nextPageToken) next = IAPF_RO_encodeCursor_({ pageToken: String(d.nextPageToken) });

  return {
    ok: true,
    script_id: scriptId,
    returned: deployments.length,
    deployments: deployments,
    next_cursor: next
  };
}

function IAPF_RO_scriptVersions_(payload) {
  var p = payload || {};
  var scriptId = IAPF_RO_resolveScriptId_(p);
  if (!scriptId) return { ok: false, error: "Missing script_id and cannot resolve target" };

  var pageSize = IAPF_RO_clamp_(p.page_size || 50, 1, 100);
  var cursor = IAPF_RO_decodeCursor_(p.cursor) || {};
  var pageToken = String(p.page_token || cursor.pageToken || "");

  var res = IAPF_RO_scriptApiGet_("/projects/" + encodeURIComponent(scriptId) + "/versions", {
    pageSize: pageSize,
    pageToken: pageToken
  });
  if (!res.ok) return res;

  var d = res.data || {};
  var versions = (d.versions || []).map(function (v) {
    return {
      versionNumber: (v.versionNumber !== undefined) ? String(v.versionNumber) : "",
      description: String(v.description || ""),
      createTime: String(v.createTime || "")
    };
  });

  var next = "";
  if (d.nextPageToken) next = IAPF_RO_encodeCursor_({ pageToken: String(d.nextPageToken) });

  return {
    ok: true,
    script_id: scriptId,
    returned: versions.length,
    versions: versions,
    next_cursor: next
  };
}

/** =========================
 *  GitHub (api.github.com)
 *  ========================= */

function IAPF_RO_getGithubToken_() {
  // Token MUST be stored in ScriptProperties (never in SHEET).
  // Property name is explicit to avoid confusion.
  var props = PropertiesService.getScriptProperties();
  return String(props.getProperty("IAPF_GITHUB_TOKEN") || "");
}

function IAPF_RO_githubGet_(path, query) {
  var token = IAPF_RO_getGithubToken_();
  if (!token) return { ok: false, error: "Missing ScriptProperty IAPF_GITHUB_TOKEN" };

  var url = "https://api.github.com" + String(path || "");
  var q = query || {};
  var parts = [];
  Object.keys(q).forEach(function (k) {
    if (q[k] === undefined || q[k] === null || q[k] === "") return;
    parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(String(q[k])));
  });
  if (parts.length) url += (url.indexOf("?") === -1 ? "?" : "&") + parts.join("&");

  var resp = UrlFetchApp.fetch(url, {
    method: "get",
    muteHttpExceptions: true,
    headers: {
      Authorization: "Bearer " + token,
      Accept: "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28"
    }
  });

  var status = resp.getResponseCode();
  var text = resp.getContentText() || "";

  if (status < 200 || status >= 300) {
    // Never return full raw body (may include sensitive info). Keep compact.
    return { ok: false, http: status, error: text.substring(0, 1200) };
  }

  try {
    return { ok: true, data: JSON.parse(text || "{}") };
  } catch (e) {
    return { ok: true, data: { raw: text } };
  }
}

function IAPF_RO_githubRepos_(payload) {
  var p = payload || {};
  var pageSize = IAPF_RO_clamp_(p.page_size || 50, 1, 100);

  var cursor = IAPF_RO_decodeCursor_(p.cursor) || {};
  var page = Number(p.page || cursor.page || 1);
  if (isNaN(page) || page < 1) page = 1;

  // Either org (preferred) or user
  var org = String(p.org || "").trim();
  var user = String(p.user || "").trim();

  var path = "";
  if (org) path = "/orgs/" + encodeURIComponent(org) + "/repos";
  else if (user) path = "/users/" + encodeURIComponent(user) + "/repos";
  else return { ok: false, error: "Missing org or user" };

  var res = IAPF_RO_githubGet_(path, {
    per_page: pageSize,
    page: page,
    sort: String(p.sort || "pushed")
  });
  if (!res.ok) return res;

  var items = (res.data || []).map(function (r) {
    return {
      id: (r.id !== undefined) ? String(r.id) : "",
      full_name: String(r.full_name || ""),
      private: !!r.private,
      default_branch: String(r.default_branch || ""),
      pushed_at: String(r.pushed_at || ""),
      updated_at: String(r.updated_at || ""),
      html_url: String(r.html_url || "")
    };
  });

  var next = (items.length === pageSize) ? IAPF_RO_encodeCursor_({ page: page + 1 }) : "";

  return {
    ok: true,
    returned: items.length,
    repos: items,
    next_cursor: next
  };
}

function IAPF_RO_githubRepoDetail_(payload) {
  var p = payload || {};
  var owner = String(p.owner || "").trim();
  var repo = String(p.repo || "").trim();
  if (!owner || !repo) return { ok: false, error: "Missing owner/repo" };

  var res = IAPF_RO_githubGet_("/repos/" + encodeURIComponent(owner) + "/" + encodeURIComponent(repo), {});
  if (!res.ok) return res;

  var r = res.data || {};
  return {
    ok: true,
    repo: {
      id: (r.id !== undefined) ? String(r.id) : "",
      full_name: String(r.full_name || ""),
      private: !!r.private,
      default_branch: String(r.default_branch || ""),
      description: String(r.description || ""),
      pushed_at: String(r.pushed_at || ""),
      updated_at: String(r.updated_at || ""),
      html_url: String(r.html_url || ""),
      open_issues_count: (r.open_issues_count !== undefined) ? Number(r.open_issues_count) : 0,
      forks_count: (r.forks_count !== undefined) ? Number(r.forks_count) : 0,
      stargazers_count: (r.stargazers_count !== undefined) ? Number(r.stargazers_count) : 0
    }
  };
}

function IAPF_RO_githubWorkflowRuns_(payload) {
  var p = payload || {};
  var owner = String(p.owner || "").trim();
  var repo = String(p.repo || "").trim();
  if (!owner || !repo) return { ok: false, error: "Missing owner/repo" };

  var pageSize = IAPF_RO_clamp_(p.page_size || 30, 1, 100);
  var cursor = IAPF_RO_decodeCursor_(p.cursor) || {};
  var page = Number(p.page || cursor.page || 1);
  if (isNaN(page) || page < 1) page = 1;

  var res = IAPF_RO_githubGet_("/repos/" + encodeURIComponent(owner) + "/" + encodeURIComponent(repo) + "/actions/runs", {
    per_page: pageSize,
    page: page,
    status: String(p.status || "")
  });
  if (!res.ok) return res;

  var d = res.data || {};
  var runs = (d.workflow_runs || []).map(function (x) {
    return {
      id: (x.id !== undefined) ? String(x.id) : "",
      name: String(x.name || ""),
      event: String(x.event || ""),
      status: String(x.status || ""),
      conclusion: String(x.conclusion || ""),
      created_at: String(x.created_at || ""),
      updated_at: String(x.updated_at || ""),
      head_branch: String(x.head_branch || ""),
      head_sha: String(x.head_sha || ""),
      actor: x.actor ? { login: String(x.actor.login || "") } : null,
      html_url: String(x.html_url || "")
    };
  });

  var next = (runs.length === pageSize) ? IAPF_RO_encodeCursor_({ page: page + 1 }) : "";

  return {
    ok: true,
    total_count: (d.total_count !== undefined) ? Number(d.total_count) : 0,
    returned: runs.length,
    workflow_runs: runs,
    next_cursor: next
  };
}
