// File: /CODE/G17_MCP_HTTP_CLIENT_EXTENDED.gs
// HUB IAPF Memory — Phase 2 HTTP Client Extended (Drive, Apps Script, Cloud Run, Secrets, Web, Terminal)

/**
 * Client HTTP pour les endpoints Phase 2 MCP
 * Wrapper d'accès au proxy mcp-memory-proxy avec:
 * - Gestion run_id et logging
 * - Redaction automatique
 * - Retry/timeout
 * - Pagination support
 */

var MCP_HTTP = (function() {
  
  // Configuration
  const BASE_URL = "https://mcp-memory-proxy-jxjjoyxhgq-uc.a.run.app";
  const DEFAULT_TIMEOUT = 30000; // 30s
  const MAX_RETRIES = 3;
  
  /**
   * Récupère la clé API depuis SETTINGS
   */
  function _getApiKey_() {
    try {
      const ss = SpreadsheetApp.getActiveSpreadsheet();
      const settingsSheet = ss.getSheetByName("SETTINGS");
      if (!settingsSheet) {
        Logger.log("[MCP_HTTP] SETTINGS sheet not found");
        return null;
      }
      
      const data = settingsSheet.getDataRange().getValues();
      for (let i = 1; i < data.length; i++) {
        if (data[i][0] === "mcp_api_key") {
          return data[i][1];
        }
      }
      
      Logger.log("[MCP_HTTP] mcp_api_key not found in SETTINGS");
      return null;
    } catch (e) {
      Logger.log("[MCP_HTTP] Error getting API key: " + e);
      return null;
    }
  }
  
  /**
   * Effectue une requête HTTP avec retry et timeout
   */
  function _makeRequest_(method, endpoint, options) {
    options = options || {};
    const apiKey = _getApiKey_();
    
    if (!apiKey) {
      throw new Error("API Key non configurée - voir SETTINGS.mcp_api_key");
    }
    
    const url = BASE_URL + endpoint;
    
    const httpOptions = {
      method: method,
      headers: {
        "Content-Type": "application/json",
        "X-API-Key": apiKey
      },
      muteHttpExceptions: true,
      timeout: options.timeout || DEFAULT_TIMEOUT
    };
    
    if (options.payload) {
      httpOptions.payload = JSON.stringify(options.payload);
    }
    
    let lastError = null;
    
    for (let retry = 0; retry < MAX_RETRIES; retry++) {
      try {
        const response = UrlFetchApp.fetch(url, httpOptions);
        const responseCode = response.getResponseCode();
        const responseText = response.getContentText();
        
        if (responseCode >= 200 && responseCode < 300) {
          return JSON.parse(responseText);
        } else {
          lastError = new Error(`HTTP ${responseCode}: ${responseText}`);
          
          // Retry only on 5xx errors
          if (responseCode >= 500 && retry < MAX_RETRIES - 1) {
            Utilities.sleep(1000 * (retry + 1)); // Exponential backoff
            continue;
          } else {
            throw lastError;
          }
        }
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
  
  /**
   * List recursive folder tree
   */
  function driveListTree(folderId, options) {
    options = options || {};
    const queryParams = new URLSearchParams({
      folder_id: folderId,
      max_depth: options.max_depth || 2,
      limit: options.limit || 100,
      include_trashed: options.include_trashed || false
    });
    
    return _makeRequest_("get", `/drive/tree?${queryParams.toString()}`, {});
  }
  
  /**
   * Get file metadata
   */
  function driveFileMetadata(fileId) {
    return _makeRequest_("get", `/drive/file/${fileId}/metadata`, {});
  }
  
  /**
   * Search files by name/regex
   */
  function driveSearch(query, options) {
    options = options || {};
    const queryParams = new URLSearchParams({
      query: query,
      limit: options.limit || 50
    });
    
    if (options.folder_id) {
      queryParams.append("folder_id", options.folder_id);
    }
    if (options.mime_type) {
      queryParams.append("mime_type", options.mime_type);
    }
    if (options.modified_after) {
      queryParams.append("modified_after", options.modified_after);
    }
    if (options.page_token) {
      queryParams.append("page_token", options.page_token);
    }
    
    return _makeRequest_("get", `/drive/search?${queryParams.toString()}`, {});
  }
  
  /**
   * Read file text content (bounded)
   */
  function driveReadText(fileId, options) {
    options = options || {};
    const queryParams = new URLSearchParams({
      file_id: fileId,
      max_size: options.max_size || 1048576 // 1MB default
    });
    
    return _makeRequest_("get", `/drive/file/${fileId}/text?${queryParams.toString()}`, {});
  }
  
  // ============================================================================
  // APPS SCRIPT ENDPOINTS
  // ============================================================================
  
  /**
   * List Apps Script deployments
   */
  function appsScriptDeployments(scriptId, options) {
    options = options || {};
    const queryParams = new URLSearchParams({
      limit: options.limit || 20
    });
    
    return _makeRequest_("get", `/apps-script/project/${scriptId}/deployments?${queryParams.toString()}`, {});
  }
  
  /**
   * Get Apps Script project structure
   */
  function appsScriptStructure(scriptId) {
    return _makeRequest_("get", `/apps-script/project/${scriptId}/structure`, {});
  }
  
  /**
   * Get Apps Script file metadata
   */
  function appsScriptFileMetadata(scriptId, fileName) {
    const queryParams = new URLSearchParams({
      file_name: fileName
    });
    
    return _makeRequest_("get", `/apps-script/project/${scriptId}/file-metadata?${queryParams.toString()}`, {});
  }
  
  /**
   * Get Apps Script logs/executions
   */
  function appsScriptLogs(scriptId, options) {
    options = options || {};
    const queryParams = new URLSearchParams({
      limit: options.limit || 100
    });
    
    if (options.start_time) {
      queryParams.append("start_time", options.start_time);
    }
    if (options.end_time) {
      queryParams.append("end_time", options.end_time);
    }
    if (options.page_token) {
      queryParams.append("page_token", options.page_token);
    }
    
    return _makeRequest_("get", `/apps-script/project/${scriptId}/logs?${queryParams.toString()}`, {});
  }
  
  // ============================================================================
  // CLOUD RUN ENDPOINTS
  // ============================================================================
  
  /**
   * Get Cloud Run service status
   */
  function cloudRunServiceStatus(serviceName, options) {
    options = options || {};
    const queryParams = new URLSearchParams({});
    
    if (options.region) {
      queryParams.append("region", options.region);
    }
    
    return _makeRequest_("get", `/cloud-run/service/${serviceName}/status?${queryParams.toString()}`, {});
  }
  
  /**
   * Get Cloud Run jobs status (if used)
   */
  function cloudRunJobsStatus(jobName, options) {
    options = options || {};
    const queryParams = new URLSearchParams({});
    
    if (options.region) {
      queryParams.append("region", options.region);
    }
    
    return _makeRequest_("get", `/cloud-run/job/${jobName}/status?${queryParams.toString()}`, {});
  }
  
  /**
   * Query Cloud Logging
   */
  function cloudLoggingQuery(resourceType, resourceLabels, options) {
    options = options || {};
    
    const payload = {
      resource_type: resourceType,
      resource_labels: resourceLabels,
      filter: options.filter || "severity>=INFO",
      limit: options.limit || 100
    };
    
    if (options.start_time) {
      payload.start_time = options.start_time;
    }
    if (options.end_time) {
      payload.end_time = options.end_time;
    }
    if (options.page_token) {
      payload.page_token = options.page_token;
    }
    
    return _makeRequest_("post", "/cloud-logging/query", {payload: payload});
  }
  
  // ============================================================================
  // SECRET MANAGER ENDPOINTS (CRITICAL - GOVERNED)
  // ============================================================================
  
  /**
   * List Secret Manager secrets (metadata only, never values)
   */
  function secretsList(options) {
    options = options || {};
    const queryParams = new URLSearchParams({
      limit: options.limit || 50
    });
    
    if (options.project_id) {
      queryParams.append("project_id", options.project_id);
    }
    if (options.filter) {
      queryParams.append("filter", options.filter);
    }
    
    return _makeRequest_("get", `/secrets/list?${queryParams.toString()}`, {});
  }
  
  /**
   * Get secret reference (never the value)
   */
  function secretGetReference(secretId, options) {
    options = options || {};
    const queryParams = new URLSearchParams({
      version: options.version || "latest"
    });
    
    if (options.project_id) {
      queryParams.append("project_id", options.project_id);
    }
    
    return _makeRequest_("get", `/secrets/${secretId}/reference?${queryParams.toString()}`, {});
  }
  
  /**
   * Create secret (GOVERNED - DRY_RUN/APPLY)
   * ⚠️ Value is redacted in all logs
   */
  function secretCreate(secretId, value, options) {
    options = options || {};
    
    const payload = {
      secret_id: secretId,
      value: value,
      labels: options.labels || {},
      replication: options.replication || "automatic",
      dry_run: options.dry_run !== false // Default true
    };
    
    if (options.project_id) {
      payload.project_id = options.project_id;
    }
    
    return _makeRequest_("post", "/secrets/create", {payload: payload});
  }
  
  /**
   * Rotate secret (GOVERNED - DRY_RUN/APPLY)
   * ⚠️ Value is redacted in all logs
   */
  function secretRotate(secretId, newValue, options) {
    options = options || {};
    
    const payload = {
      secret_id: secretId,
      new_value: newValue,
      disable_previous_version: options.disable_previous_version || false,
      dry_run: options.dry_run !== false // Default true
    };
    
    return _makeRequest_("post", `/secrets/${secretId}/rotate`, {payload: payload});
  }
  
  // ============================================================================
  // WEB ACCESS ENDPOINTS
  // ============================================================================
  
  /**
   * Web search with allowlist domains + quota
   */
  function webSearch(query, options) {
    options = options || {};
    
    const payload = {
      query: query,
      max_results: options.max_results || 10,
      allowed_domains: options.allowed_domains || []
    };
    
    return _makeRequest_("post", "/web/search", {payload: payload});
  }
  
  /**
   * Fetch URL with allowlist domains
   */
  function webFetch(url, options) {
    options = options || {};
    
    const payload = {
      url: url,
      method: options.method || "GET",
      headers: options.headers || {},
      max_size: options.max_size || 1048576 // 1MB default
    };
    
    return _makeRequest_("post", "/web/fetch", {payload: payload});
  }
  
  // ============================================================================
  // TERMINAL RUNNER ENDPOINT (CRITICAL - GOVERNED)
  // ============================================================================
  
  /**
   * Run command with strict allowlist (GOVERNED)
   * mode: READ_ONLY | WRITE
   * ⚠️ WRITE requires dry_run=false + explicit GO confirmation in UI
   */
  function terminalRun(command, options) {
    options = options || {};
    
    const payload = {
      command: command,
      mode: options.mode || "READ_ONLY",
      timeout_seconds: options.timeout_seconds || 30,
      dry_run: options.dry_run !== false // Default true
    };
    
    return _makeRequest_("post", "/terminal/run", {payload: payload});
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
