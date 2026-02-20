// File: /CODE/G17_MCP_HTTP_CLIENT_EXTENDED.gs
// HUB IAPF Memory — Phase 2 HTTP Client Extended (Drive, Apps Script, Cloud Run, Secrets, Web, Terminal)

/**
 * Client HTTP pour les endpoints Phase 2 MCP
 * Wrapper d'accès au proxy mcp-memory-proxy avec:
 * - run_id (côté proxy) + journalisation obligatoire
 * - Retry (5xx) + erreurs explicites
 * - Pagination support (page_token)
 *
 * IMPORTANT (Apps Script):
 * - URLSearchParams n'existe PAS => querystring construit manuellement
 * - UrlFetchApp n'expose pas de "timeout" param -> on évite les options non supportées
 */

var MCP_HTTP = (function () {

  // Fallback si SETTINGS manquant (dev uniquement)
  const FALLBACK_BASE_URL = "https://mcp-memory-proxy-522732657254.us-central1.run.app";
  const MAX_RETRIES = 3;

  // ----------------------------------------------------------------------------
  // SETTINGS helpers
  // ----------------------------------------------------------------------------

  function _getSettingsValue_(key) {
    try {
      const ss = SpreadsheetApp.getActiveSpreadsheet();
      const settingsSheet = ss.getSheetByName("SETTINGS");
      if (!settingsSheet) return null;

      const data = settingsSheet.getDataRange().getValues();
      for (let i = 1; i < data.length; i++) {
        if (data[i][0] === key) return data[i][1];
      }
      return null;
    } catch (e) {
      Logger.log("[MCP_HTTP] Error reading SETTINGS: " + e);
      return null;
    }
  }

  function _getApiKey_() {
    const apiKey = _getSettingsValue_("mcp_api_key");
    return apiKey ? String(apiKey).trim() : null;
  }

  function _getProxyUrl_() {
    const fromSettings = _getSettingsValue_("mcp_proxy_url");
    if (fromSettings && String(fromSettings).trim()) return String(fromSettings).trim();
    return FALLBACK_BASE_URL;
  }

  // ----------------------------------------------------------------------------
  // Querystring helper (Apps Script compatible)
  // ----------------------------------------------------------------------------

  function _toQueryString_(params) {
    if (!params) return "";
    const parts = [];

    const keys = Object.keys(params);
    for (let i = 0; i < keys.length; i++) {
      const k = keys[i];
      const v = params[k];

      // Skip null/undefined/empty
      if (v === null || v === undefined) continue;
      if (typeof v === "string" && v.trim() === "") continue;

      // Array => repeat key
      if (Array.isArray(v)) {
        for (let j = 0; j < v.length; j++) {
          const av = v[j];
          if (av === null || av === undefined) continue;
          parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(String(av)));
        }
        continue;
      }

      // Bool => "true/false"
      if (typeof v === "boolean") {
        parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(v ? "true" : "false"));
        continue;
      }

      // Default
      parts.push(encodeURIComponent(k) + "=" + encodeURIComponent(String(v)));
    }

    return parts.length ? ("?" + parts.join("&")) : "";
  }

  // ----------------------------------------------------------------------------
  // HTTP core
  // ----------------------------------------------------------------------------

  function _makeRequest_(method, endpoint, options) {
    options = options || {};

    const apiKey = _getApiKey_();
    if (!apiKey) {
      throw new Error("API Key non configurée - voir SETTINGS.mcp_api_key");
    }

    const baseUrl = _getProxyUrl_();
    const url = baseUrl + endpoint;

    const httpOptions = {
      method: method,
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey
      },
      muteHttpExceptions: true
    };

    if (options.payload !== undefined && options.payload !== null) {
      httpOptions.payload = JSON.stringify(options.payload);
    }

    let lastError = null;

    for (let retry = 0; retry < MAX_RETRIES; retry++) {
      try {
        const response = UrlFetchApp.fetch(url, httpOptions);
        const code = response.getResponseCode();
        const text = response.getContentText();

        if (code >= 200 && code < 300) {
          try {
            return JSON.parse(text);
          } catch (e) {
            return { ok: true, raw: text };
          }
        }

        lastError = new Error("HTTP " + code + ": " + text);

        // Retry uniquement sur 5xx
        if (code >= 500 && retry < MAX_RETRIES - 1) {
          Utilities.sleep(1000 * (retry + 1));
          continue;
        }
        throw lastError;

      } catch (e) {
        lastError = e;
        if (retry < MAX_RETRIES - 1) {
          Utilities.sleep(1000 * (retry + 1));
          continue;
        }
      }
    }

    throw lastError || new Error("Request failed after retries");
  }

  // ============================================================================
  // DRIVE ENDPOINTS
  // ============================================================================

  function driveListTree(folderId, options) {
    options = options || {};
    const qs = _toQueryString_({
      folder_id: folderId,
      max_depth: (options.max_depth !== undefined ? options.max_depth : 2),
      limit: (options.limit !== undefined ? options.limit : 100),
      include_trashed: (options.include_trashed !== undefined ? options.include_trashed : false),
      page_token: options.page_token
    });
    return _makeRequest_("get", "/drive/tree" + qs, {});
  }

  function driveFileMetadata(fileId) {
    return _makeRequest_("get", "/drive/file/" + encodeURIComponent(fileId) + "/metadata", {});
  }

  function driveSearch(query, options) {
    options = options || {};
    const qs = _toQueryString_({
      query: query,
      folder_id: options.folder_id,
      mime_type: options.mime_type,
      modified_after: options.modified_after,
      page_token: options.page_token,
      limit: (options.limit !== undefined ? options.limit : 50)
    });
    return _makeRequest_("get", "/drive/search" + qs, {});
  }

  function driveReadText(fileId, options) {
    options = options || {};
    const qs = _toQueryString_({
      file_id: fileId,
      max_size: (options.max_size !== undefined ? options.max_size : 1048576)
    });
    return _makeRequest_("get", "/drive/file/" + encodeURIComponent(fileId) + "/text" + qs, {});
  }

  // ============================================================================
  // APPS SCRIPT ENDPOINTS
  // ============================================================================

  function appsScriptDeployments(scriptId, options) {
    options = options || {};
    const qs = _toQueryString_({
      limit: (options.limit !== undefined ? options.limit : 20),
      page_token: options.page_token
    });
    return _makeRequest_("get", "/apps-script/project/" + encodeURIComponent(scriptId) + "/deployments" + qs, {});
  }

  function appsScriptStructure(scriptId) {
    return _makeRequest_("get", "/apps-script/project/" + encodeURIComponent(scriptId) + "/structure", {});
  }

  function appsScriptFileMetadata(scriptId, fileName) {
    const qs = _toQueryString_({ file_name: fileName });
    return _makeRequest_("get", "/apps-script/project/" + encodeURIComponent(scriptId) + "/file-metadata" + qs, {});
  }

  function appsScriptLogs(scriptId, options) {
    options = options || {};
    const qs = _toQueryString_({
      limit: (options.limit !== undefined ? options.limit : 100),
      start_time: options.start_time,
      end_time: options.end_time,
      page_token: options.page_token
    });
    return _makeRequest_("get", "/apps-script/project/" + encodeURIComponent(scriptId) + "/logs" + qs, {});
  }

  // ============================================================================
  // CLOUD RUN ENDPOINTS
  // ============================================================================

  function cloudRunServiceStatus(serviceName, options) {
    options = options || {};
    const qs = _toQueryString_({
      region: options.region
    });
    return _makeRequest_("get", "/cloud-run/service/" + encodeURIComponent(serviceName) + "/status" + qs, {});
  }

  function cloudRunJobsStatus(jobName, options) {
    options = options || {};
    const qs = _toQueryString_({
      region: options.region
    });
    return _makeRequest_("get", "/cloud-run/job/" + encodeURIComponent(jobName) + "/status" + qs, {});
  }

  function cloudLoggingQuery(resourceType, resourceLabels, options) {
    options = options || {};

    const payload = {
      resource_type: resourceType,
      resource_labels: resourceLabels,
      filter: (options.filter !== undefined ? options.filter : "severity>=INFO"),
      limit: (options.limit !== undefined ? options.limit : 100)
    };

    if (options.start_time) payload.start_time = options.start_time;
    if (options.end_time) payload.end_time = options.end_time;
    if (options.page_token) payload.page_token = options.page_token;

    return _makeRequest_("post", "/cloud-logging/query", { payload: payload });
  }

  // ============================================================================
  // SECRET MANAGER ENDPOINTS (GOVERNED)
  // ============================================================================

  function secretsList(options) {
    options = options || {};
    const qs = _toQueryString_({
      project_id: options.project_id,
      filter: options.filter,
      page_token: options.page_token,
      limit: (options.limit !== undefined ? options.limit : 50)
    });
    return _makeRequest_("get", "/secrets/list" + qs, {});
  }

  function secretGetReference(secretId, options) {
    options = options || {};
    const qs = _toQueryString_({
      project_id: options.project_id,
      version: (options.version !== undefined ? options.version : "latest")
    });
    return _makeRequest_("get", "/secrets/" + encodeURIComponent(secretId) + "/reference" + qs, {});
  }

  function secretCreate(secretId, value, options) {
    options = options || {};
    const payload = {
      project_id: options.project_id,
      secret_id: secretId,
      value: value,
      labels: options.labels || {},
      replication: (options.replication !== undefined ? options.replication : "automatic"),
      dry_run: (options.dry_run !== false)
    };
    return _makeRequest_("post", "/secrets/create", { payload: payload });
  }

  function secretRotate(secretId, newValue, options) {
    options = options || {};
    const payload = {
      project_id: options.project_id,
      secret_id: secretId,
      new_value: newValue,
      disable_previous_version: (options.disable_previous_version !== undefined ? options.disable_previous_version : false),
      dry_run: (options.dry_run !== false)
    };
    return _makeRequest_("post", "/secrets/" + encodeURIComponent(secretId) + "/rotate", { payload: payload });
  }

  // ============================================================================
  // WEB ACCESS ENDPOINTS
  // ============================================================================

  function webSearch(query, options) {
    options = options || {};
    const payload = {
      query: query,
      max_results: (options.max_results !== undefined ? options.max_results : 10),
      allowed_domains: (options.allowed_domains !== undefined ? options.allowed_domains : [])
    };
    return _makeRequest_("post", "/web/search", { payload: payload });
  }

  function webFetch(url, options) {
    options = options || {};
    const payload = {
      url: url,
      method: (options.method !== undefined ? options.method : "GET"),
      headers: (options.headers !== undefined ? options.headers : {}),
      max_size: (options.max_size !== undefined ? options.max_size : 1048576)
    };
    return _makeRequest_("post", "/web/fetch", { payload: payload });
  }

  // ============================================================================
  // TERMINAL RUNNER ENDPOINT (GOVERNED)
  // ============================================================================

  function terminalRun(command, options) {
    options = options || {};
    const payload = {
      command: command,
      mode: (options.mode !== undefined ? options.mode : "READ_ONLY"),
      timeout_seconds: (options.timeout_seconds !== undefined ? options.timeout_seconds : 30),
      dry_run: (options.dry_run !== false)
    };
    return _makeRequest_("post", "/terminal/run", { payload: payload });
  }

  // ============================================================================
  // PUBLIC API
  // ============================================================================

  return {
    // Drive
    driveListTree: driveListTree,
    driveFileMetadata: driveFileMetadata,
    driveSearch: driveSearch,
    driveReadText: driveReadText,

    // Apps Script
    appsScriptDeployments: appsScriptDeployments,
    appsScriptStructure: appsScriptStructure,
    appsScriptFileMetadata: appsScriptFileMetadata,
    appsScriptLogs: appsScriptLogs,

    // Cloud Run
    cloudRunServiceStatus: cloudRunServiceStatus,
    cloudRunJobsStatus: cloudRunJobsStatus,
    cloudLoggingQuery: cloudLoggingQuery,

    // Secrets (GOVERNED)
    secretsList: secretsList,
    secretGetReference: secretGetReference,
    secretCreate: secretCreate,
    secretRotate: secretRotate,

    // Web
    webSearch: webSearch,
    webFetch: webFetch,

    // Terminal (GOVERNED)
    terminalRun: terminalRun
  };

})();