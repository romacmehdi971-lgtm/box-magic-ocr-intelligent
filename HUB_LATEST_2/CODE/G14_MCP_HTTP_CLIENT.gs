/**
 * FILE: G09_MCP_HTTP_CLIENT.gs
 * PROJECT: IAPF MEMORY HUB V1
 * 
 * Objectif:
 * - Client HTTP pour appeler le backend MCP Memory Proxy (Cloud Run)
 * - Pass-through strict des query params (e.g., ?limit=)
 * - Remontée détaillée des erreurs (status_code + body + correlation_id)
 * - Support GET only (read-only audit mode)
 * 
 * Dépendances:
 * - SETTINGS: mcp_proxy_url, mcp_api_key
 */

var MCP_HTTP = (function() {

  /**
   * Get base URL from SETTINGS (mcp_proxy_url)
   * Example: "https://mcp-memory-proxy-522732657254.us-central1.run.app"
   */
  function _getBaseUrl_() {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName("SETTINGS");
    if (!sh) throw new Error("SETTINGS sheet not found");
    
    const values = sh.getDataRange().getValues();
    for (let i = 1; i < values.length; i++) {
      const key = String(values[i][0] || "").trim();
      if (key === "mcp_proxy_url") {
        const url = String(values[i][1] || "").trim();
        if (!url) throw new Error("SETTINGS: mcp_proxy_url is empty");
        return url;
      }
    }
    throw new Error("SETTINGS: mcp_proxy_url not found");
  }

  /**
   * Get API key from SETTINGS (mcp_api_key)
   * CRITICAL: This key is sensitive and should NEVER be logged
   */
  function _getApiKey_() {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName("SETTINGS");
    if (!sh) throw new Error("SETTINGS sheet not found");
    
    const values = sh.getDataRange().getValues();
    for (let i = 1; i < values.length; i++) {
      const key = String(values[i][0] || "").trim();
      if (key === "mcp_api_key") {
        const apiKey = String(values[i][1] || "").trim();
        if (!apiKey) throw new Error("SETTINGS: mcp_api_key is empty");
        return apiKey;
      }
    }
    throw new Error("SETTINGS: mcp_api_key not found");
  }

  /**
   * Build URL with query parameters
   * Ensures strict pass-through of all params
   */
  function _buildUrl_(path, queryParams) {
    let url = _getBaseUrl_() + path;
    if (queryParams && Object.keys(queryParams).length > 0) {
      const params = [];
      for (const key in queryParams) {
        if (queryParams.hasOwnProperty(key)) {
          const value = queryParams[key];
          if (value !== null && value !== undefined) {
            params.push(encodeURIComponent(key) + "=" + encodeURIComponent(value));
          }
        }
      }
      if (params.length > 0) {
        url += "?" + params.join("&");
      }
    }
    return url;
  }

  /**
   * Execute HTTP GET request
   * Returns: { ok: boolean, status: number, body: object|string, correlation_id: string|null, error: string|null }
   */
  function _httpGet_(path, queryParams, extraHeaders) {
    const url = _buildUrl_(path, queryParams);
    const apiKey = _getApiKey_();
    
    const headers = {
      "X-API-Key": apiKey,
      "Accept": "application/json"
    };
    
    if (extraHeaders) {
      for (const key in extraHeaders) {
        if (extraHeaders.hasOwnProperty(key)) {
          headers[key] = extraHeaders[key];
        }
      }
    }

    let response;
    try {
      response = UrlFetchApp.fetch(url, {
        method: "get",
        headers: headers,
        muteHttpExceptions: true
      });
    } catch (e) {
      return {
        ok: false,
        status: 0,
        body: null,
        correlation_id: null,
        error: "Network error: " + String(e.message || e)
      };
    }

    const statusCode = response.getResponseCode();
    const contentText = response.getContentText();
    
    let bodyObj = null;
    let correlationId = null;
    
    try {
      bodyObj = JSON.parse(contentText);
      if (bodyObj && bodyObj.correlation_id) {
        correlationId = bodyObj.correlation_id;
      }
    } catch (e) {
      // Not JSON, keep as string
      bodyObj = contentText;
    }

    return {
      ok: (statusCode >= 200 && statusCode < 300),
      status: statusCode,
      body: bodyObj,
      correlation_id: correlationId,
      error: (statusCode >= 200 && statusCode < 300) ? null : "HTTP " + statusCode
    };
  }

  /**
   * Public API: GET /infra/whoami
   * Returns full response including cloud_run_revision, version, config.read_only_mode, etc.
   */
  function getInfraWhoami() {
    return _httpGet_("/infra/whoami", null, null);
  }

  /**
   * Public API: GET /health
   */
  function getHealth() {
    return _httpGet_("/health", null, null);
  }

  /**
   * Public API: GET /docs-json
   */
  function getDocsJson() {
    return _httpGet_("/docs-json", null, null);
  }

  /**
   * Public API: GET /sheets/{sheet_name}
   * queryParams can include: limit, offset, cursor, reverse
   */
  function getSheet(sheetName, queryParams) {
    if (!sheetName) throw new Error("sheetName is required");
    return _httpGet_("/sheets/" + encodeURIComponent(sheetName), queryParams, null);
  }

  /**
   * Public API: GET /gpt/memory-log
   * queryParams can include: limit, offset, cursor, reverse
   */
  function getGptMemoryLog(queryParams) {
    return _httpGet_("/gpt/memory-log", queryParams, null);
  }

  return {
    getInfraWhoami: getInfraWhoami,
    getHealth: getHealth,
    getDocsJson: getDocsJson,
    getSheet: getSheet,
    getGptMemoryLog: getGptMemoryLog
  };

})();

/**
 * ===== COCKPIT UI ACTIONS =====
 * These functions are called from the menu (G01_UI_MENU.gs)
 */

function MCP_COCKPIT_testConnection() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    const result = MCP_HTTP.getHealth();
    
    if (result.ok) {
      const version = result.body && result.body.version ? result.body.version : "unknown";
      ui.alert(
        "MCP Proxy — Connection OK",
        "✅ Backend health check passed\n\nVersion: " + version + "\nStatus: " + result.status,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert(
        "MCP Proxy — Connection Error",
        "❌ Health check failed\n\n" +
        "Status: " + result.status + "\n" +
        "Error: " + (result.error || "unknown") + "\n\n" +
        "Response:\n" + JSON.stringify(result.body, null, 2).slice(0, 500),
        ui.ButtonSet.OK
      );
    }
  } catch (e) {
    ui.alert(
      "MCP Proxy — Error",
      "Exception: " + String(e.message || e) + "\n\n" +
      "Check SETTINGS: mcp_proxy_url and mcp_api_key must be set.",
      ui.ButtonSet.OK
    );
  }
}

function MCP_COCKPIT_getWhoami() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    const result = MCP_HTTP.getInfraWhoami();
    
    if (result.ok) {
      const data = result.body;
      const config = data.config || {};
      
      const msg = 
        "✅ GET /infra/whoami succeeded\n\n" +
        "Project: " + (data.project_id || "N/A") + "\n" +
        "Region: " + (data.region || "N/A") + "\n" +
        "Service: " + (data.cloud_run_service || "N/A") + "\n" +
        "Revision: " + (data.cloud_run_revision || "N/A") + "\n" +
        "Version: " + (data.version || "N/A") + "\n\n" +
        "Config:\n" +
        "  read_only_mode: " + (config.read_only_mode || "N/A") + "\n" +
        "  enable_actions: " + (config.enable_actions || "N/A") + "\n" +
        "  dry_run_mode: " + (config.dry_run_mode || "N/A") + "\n" +
        "  log_level: " + (config.log_level || "N/A");
      
      ui.alert("MCP Proxy — Infrastructure Info", msg, ui.ButtonSet.OK);
    } else {
      ui.alert(
        "MCP Proxy — Error",
        "❌ GET /infra/whoami failed\n\n" +
        "Status: " + result.status + "\n" +
        "Error: " + (result.error || "unknown") + "\n" +
        "Correlation ID: " + (result.correlation_id || "N/A") + "\n\n" +
        "Response:\n" + JSON.stringify(result.body, null, 2).slice(0, 500),
        ui.ButtonSet.OK
      );
    }
  } catch (e) {
    ui.alert(
      "MCP Proxy — Error",
      "Exception: " + String(e.message || e),
      ui.ButtonSet.OK
    );
  }
}

function MCP_COCKPIT_testPagination() {
  const ui = SpreadsheetApp.getUi();
  
  const response = ui.alert(
    "MCP Proxy — Test Pagination",
    "This will test query params pass-through:\n\n" +
    "• GET /sheets/SETTINGS?limit=1\n" +
    "• GET /sheets/MEMORY_LOG?limit=5\n" +
    "• GET /sheets/DRIVE_INVENTORY?limit=10\n\n" +
    "Continue?",
    ui.ButtonSet.YES_NO
  );
  
  if (response !== ui.Button.YES) {
    ui.alert("MCP Proxy", "Test cancelled.", ui.ButtonSet.OK);
    return;
  }
  
  try {
    const tests = [
      { sheet: "SETTINGS", limit: 1 },
      { sheet: "MEMORY_LOG", limit: 5 },
      { sheet: "DRIVE_INVENTORY", limit: 10 }
    ];
    
    const results = [];
    
    for (let i = 0; i < tests.length; i++) {
      const test = tests[i];
      const result = MCP_HTTP.getSheet(test.sheet, { limit: test.limit });
      
      if (result.ok) {
        const rowCount = result.body && result.body.row_count ? result.body.row_count : 0;
        results.push("✅ " + test.sheet + "?limit=" + test.limit + " → " + rowCount + " rows");
      } else {
        results.push("❌ " + test.sheet + "?limit=" + test.limit + " → HTTP " + result.status);
      }
    }
    
    ui.alert(
      "MCP Proxy — Pagination Tests",
      results.join("\n"),
      ui.ButtonSet.OK
    );
    
  } catch (e) {
    ui.alert(
      "MCP Proxy — Error",
      "Exception: " + String(e.message || e),
      ui.ButtonSet.OK
    );
  }
}

function MCP_COCKPIT_httpGetTool() {
  const ui = SpreadsheetApp.getUi();
  
  // Prompt for path
  const pathResponse = ui.prompt(
    "MCP Proxy — HTTP GET Tool",
    "Enter the endpoint path (e.g., /infra/whoami, /sheets/SETTINGS):",
    ui.ButtonSet.OK_CANCEL
  );
  
  if (pathResponse.getSelectedButton() !== ui.Button.OK) {
    return;
  }
  
  const path = pathResponse.getResponseText().trim();
  if (!path) {
    ui.alert("MCP Proxy", "Path cannot be empty.", ui.ButtonSet.OK);
    return;
  }
  
  // Prompt for query params (optional)
  const paramsResponse = ui.prompt(
    "MCP Proxy — HTTP GET Tool",
    "Enter query params (optional, format: key=value&key2=value2):",
    ui.ButtonSet.OK_CANCEL
  );
  
  let queryParams = {};
  if (paramsResponse.getSelectedButton() === ui.Button.OK) {
    const paramsText = paramsResponse.getResponseText().trim();
    if (paramsText) {
      const pairs = paramsText.split("&");
      for (let i = 0; i < pairs.length; i++) {
        const pair = pairs[i].split("=");
        if (pair.length === 2) {
          queryParams[pair[0].trim()] = pair[1].trim();
        }
      }
    }
  }
  
  try {
    // Build URL manually using MCP_HTTP private functions pattern
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName("SETTINGS");
    if (!sh) throw new Error("SETTINGS sheet not found");
    
    let baseUrl = "";
    let apiKey = "";
    const values = sh.getDataRange().getValues();
    for (let i = 1; i < values.length; i++) {
      const key = String(values[i][0] || "").trim();
      if (key === "mcp_proxy_url") {
        baseUrl = String(values[i][1] || "").trim();
      } else if (key === "mcp_api_key") {
        apiKey = String(values[i][1] || "").trim();
      }
    }
    
    if (!baseUrl) throw new Error("SETTINGS: mcp_proxy_url not found");
    if (!apiKey) throw new Error("SETTINGS: mcp_api_key not found");
    
    let url = baseUrl + path;
    if (Object.keys(queryParams).length > 0) {
      const params = [];
      for (const key in queryParams) {
        if (queryParams.hasOwnProperty(key)) {
          params.push(encodeURIComponent(key) + "=" + encodeURIComponent(queryParams[key]));
        }
      }
      if (params.length > 0) {
        url += "?" + params.join("&");
      }
    }
    
    const result = UrlFetchApp.fetch(url, {
      method: "get",
      headers: {
        "X-API-Key": apiKey,
        "Accept": "application/json"
      },
      muteHttpExceptions: true
    });
    
    const statusCode = result.getResponseCode();
    const contentText = result.getContentText();
    
    ui.alert(
      "MCP Proxy — HTTP GET Result",
      "Status: " + statusCode + "\n\n" +
      "Response:\n" + contentText.slice(0, 1500),
      ui.ButtonSet.OK
    );
    
  } catch (e) {
    ui.alert(
      "MCP Proxy — Error",
      "Exception: " + String(e.message || e),
      ui.ButtonSet.OK
    );
  }
}
