/**
 * FILE: G15_AUDIT_READ_EVERYWHERE.gs
 * PROJECT: IAPF MEMORY HUB V1
 * VERSION: v1.0.0
 * 
 * Objectif: "Élia doit pouvoir voir vraiment tout"
 * - Lecture partout (READ-ONLY) sans écriture
 * - Résultat OK/KO par brique + premier point bloquant
 * - Code + erreur + correlation_id
 * 
 * Briques testées:
 * 1. Cloud Run (proxy MCP) - /health, /docs-json, /infra/whoami, /sheets?limit
 * 2. Hub Sheets - SETTINGS, MEMORY_LOG, DRIVE_INVENTORY
 * 3. Drive - accès réel aux dossiers (snapshots, archives, root mémoire)
 * 4. GitHub - lecture repo/commits
 * 5. Apps Script - introspection (projet/version/deployments)
 * 6. Logs Cloud Run - lecture logs mcp-memory-proxy
 * 
 * Dépendances:
 * - G14_MCP_HTTP_CLIENT.gs (module MCP_HTTP)
 * - SETTINGS: mcp_proxy_url, mcp_api_key, github_token, etc.
 */

var MCP_AUDIT = (function() {

  /**
   * Get setting value from SETTINGS sheet
   */
  function _getSetting_(key) {
    try {
      const ss = SpreadsheetApp.getActiveSpreadsheet();
      const sh = ss.getSheetByName("SETTINGS");
      if (!sh) return "";
      
      const values = sh.getDataRange().getValues();
      for (let i = 1; i < values.length; i++) {
        const k = String(values[i][0] || "").trim();
        if (k === key) {
          return String(values[i][1] || "").trim();
        }
      }
      return "";
    } catch (e) {
      return "";
    }
  }

  /**
   * Audit Cloud Run Proxy (MCP Memory Proxy)
   */
  function _auditCloudRunProxy_() {
    const results = [];
    
    try {
      // Test 1: GET /health
      const health = MCP_HTTP.getHealth();
      results.push({
        test: "Proxy /health",
        ok: health.ok,
        status: health.status,
        body_excerpt: health.ok ? "version=" + (health.body.version || "N/A") : String(health.error),
        correlation_id: health.correlation_id || "N/A",
        error: health.error
      });
      
      // Test 2: GET /infra/whoami
      const whoami = MCP_HTTP.getInfraWhoami();
      results.push({
        test: "Proxy /infra/whoami",
        ok: whoami.ok,
        status: whoami.status,
        body_excerpt: whoami.ok ? "revision=" + ((whoami.body && whoami.body.cloud_run_revision) || "N/A") : String(whoami.error),
        correlation_id: whoami.correlation_id || "N/A",
        error: whoami.error
      });
      
      // Test 3: GET /docs-json
      const docs = MCP_HTTP.getDocsJson();
      results.push({
        test: "Proxy /docs-json",
        ok: docs.ok,
        status: docs.status,
        body_excerpt: docs.ok ? "endpoints=" + ((docs.body && docs.body.endpoints && docs.body.endpoints.length) || 0) : String(docs.error),
        correlation_id: docs.correlation_id || "N/A",
        error: docs.error
      });
      
      // Test 4: GET /sheets/SETTINGS?limit=1
      const settings = MCP_HTTP.getSheet("SETTINGS", {limit: 1});
      results.push({
        test: "Proxy /sheets/SETTINGS?limit=1",
        ok: settings.ok,
        status: settings.status,
        body_excerpt: settings.ok ? "row_count=" + ((settings.body && settings.body.row_count) || 0) : String(settings.error),
        correlation_id: settings.correlation_id || "N/A",
        error: settings.error
      });
      
    } catch (e) {
      results.push({
        test: "Proxy (exception)",
        ok: false,
        status: 0,
        body_excerpt: "N/A",
        correlation_id: "N/A",
        error: "Exception: " + String(e.message || e)
      });
    }
    
    return results;
  }

  /**
   * Audit Hub Sheets (direct read)
   */
  function _auditHubSheets_() {
    const results = [];
    
    try {
      const ss = SpreadsheetApp.getActiveSpreadsheet();
      const sheetsToTest = ["SETTINGS", "MEMORY_LOG", "DRIVE_INVENTORY"];
      
      for (let i = 0; i < sheetsToTest.length; i++) {
        const sheetName = sheetsToTest[i];
        const sh = ss.getSheetByName(sheetName);
        
        if (sh) {
          const rowCount = sh.getLastRow();
          results.push({
            test: "Hub Sheets " + sheetName,
            ok: true,
            status: 200,
            body_excerpt: "rows=" + rowCount,
            correlation_id: "N/A",
            error: null
          });
        } else {
          results.push({
            test: "Hub Sheets " + sheetName,
            ok: false,
            status: 404,
            body_excerpt: "N/A",
            correlation_id: "N/A",
            error: "Sheet not found"
          });
        }
      }
      
    } catch (e) {
      results.push({
        test: "Hub Sheets (exception)",
        ok: false,
        status: 0,
        body_excerpt: "N/A",
        correlation_id: "N/A",
        error: "Exception: " + String(e.message || e)
      });
    }
    
    return results;
  }

  /**
   * Audit Drive (accès réel aux dossiers)
   */
  function _auditDrive_() {
    const results = [];
    
    try {
      const folderKeys = [
        {key: "snapshots_folder_id", label: "Snapshots"},
        {key: "archives_folder_id", label: "Archives"},
        {key: "memory_root_folder_id", label: "Memory Root"}
      ];
      
      for (let i = 0; i < folderKeys.length; i++) {
        const item = folderKeys[i];
        const folderId = _getSetting_(item.key);
        
        if (!folderId) {
          results.push({
            test: "Drive " + item.label,
            ok: false,
            status: 404,
            body_excerpt: "N/A",
            correlation_id: "N/A",
            error: "SETTINGS: " + item.key + " not found"
          });
          continue;
        }
        
        try {
          const folder = DriveApp.getFolderById(folderId);
          const files = folder.getFiles();
          let fileCount = 0;
          while (files.hasNext() && fileCount < 10) {
            files.next();
            fileCount++;
          }
          
          results.push({
            test: "Drive " + item.label,
            ok: true,
            status: 200,
            body_excerpt: "id=" + folderId + ", files(sample)=" + fileCount,
            correlation_id: "N/A",
            error: null
          });
        } catch (e) {
          results.push({
            test: "Drive " + item.label,
            ok: false,
            status: 403,
            body_excerpt: "N/A",
            correlation_id: "N/A",
            error: "Access denied: " + String(e.message || e)
          });
        }
      }
      
    } catch (e) {
      results.push({
        test: "Drive (exception)",
        ok: false,
        status: 0,
        body_excerpt: "N/A",
        correlation_id: "N/A",
        error: "Exception: " + String(e.message || e)
      });
    }
    
    return results;
  }

  /**
   * Audit GitHub (lecture repo/commits)
   */
  function _auditGitHub_() {
    const results = [];
    
    try {
      const githubToken = _getSetting_("github_token");
      const githubRepo = _getSetting_("github_repo"); // format: "owner/repo"
      
      if (!githubToken) {
        results.push({
          test: "GitHub Auth",
          ok: false,
          status: 401,
          body_excerpt: "N/A",
          correlation_id: "N/A",
          error: "SETTINGS: github_token not found"
        });
        return results;
      }
      
      if (!githubRepo) {
        results.push({
          test: "GitHub Repo",
          ok: false,
          status: 404,
          body_excerpt: "N/A",
          correlation_id: "N/A",
          error: "SETTINGS: github_repo not found (format: owner/repo)"
        });
        return results;
      }
      
      // Test 1: GET /repos/{owner}/{repo}
      const repoUrl = "https://api.github.com/repos/" + githubRepo;
      const repoResp = UrlFetchApp.fetch(repoUrl, {
        method: "get",
        headers: {
          "Authorization": "token " + githubToken,
          "Accept": "application/vnd.github.v3+json"
        },
        muteHttpExceptions: true
      });
      
      const repoStatus = repoResp.getResponseCode();
      if (repoStatus === 200) {
        const repoData = JSON.parse(repoResp.getContentText());
        results.push({
          test: "GitHub Repo Info",
          ok: true,
          status: 200,
          body_excerpt: "default_branch=" + (repoData.default_branch || "N/A"),
          correlation_id: "N/A",
          error: null
        });
        
        // Test 2: GET /repos/{owner}/{repo}/commits?per_page=5
        const commitsUrl = "https://api.github.com/repos/" + githubRepo + "/commits?per_page=5";
        const commitsResp = UrlFetchApp.fetch(commitsUrl, {
          method: "get",
          headers: {
            "Authorization": "token " + githubToken,
            "Accept": "application/vnd.github.v3+json"
          },
          muteHttpExceptions: true
        });
        
        const commitsStatus = commitsResp.getResponseCode();
        if (commitsStatus === 200) {
          const commitsData = JSON.parse(commitsResp.getContentText());
          const lastSha = (commitsData.length > 0 && commitsData[0].sha) ? commitsData[0].sha.slice(0, 7) : "N/A";
          results.push({
            test: "GitHub Commits (last 5)",
            ok: true,
            status: 200,
            body_excerpt: "count=" + commitsData.length + ", last_sha=" + lastSha,
            correlation_id: "N/A",
            error: null
          });
        } else {
          results.push({
            test: "GitHub Commits",
            ok: false,
            status: commitsStatus,
            body_excerpt: "N/A",
            correlation_id: "N/A",
            error: "HTTP " + commitsStatus
          });
        }
        
      } else {
        results.push({
          test: "GitHub Repo Info",
          ok: false,
          status: repoStatus,
          body_excerpt: "N/A",
          correlation_id: "N/A",
          error: "HTTP " + repoStatus
        });
      }
      
    } catch (e) {
      results.push({
        test: "GitHub (exception)",
        ok: false,
        status: 0,
        body_excerpt: "N/A",
        correlation_id: "N/A",
        error: "Exception: " + String(e.message || e)
      });
    }
    
    return results;
  }

  /**
   * Audit Apps Script (introspection projet/version/deployments)
   */
  function _auditAppsScript_() {
    const results = [];
    
    try {
      const scriptId = ScriptApp.getScriptId();
      const token = ScriptApp.getOAuthToken();
      
      // Test 1: GET /v1/projects/{scriptId}
      const projectUrl = "https://script.googleapis.com/v1/projects/" + scriptId;
      const projectResp = UrlFetchApp.fetch(projectUrl, {
        method: "get",
        headers: {
          "Authorization": "Bearer " + token
        },
        muteHttpExceptions: true
      });
      
      const projectStatus = projectResp.getResponseCode();
      if (projectStatus === 200) {
        const projectData = JSON.parse(projectResp.getContentText());
        results.push({
          test: "Apps Script Project",
          ok: true,
          status: 200,
          body_excerpt: "title=" + (projectData.title || "N/A"),
          correlation_id: "N/A",
          error: null
        });
      } else {
        results.push({
          test: "Apps Script Project",
          ok: false,
          status: projectStatus,
          body_excerpt: "N/A",
          correlation_id: "N/A",
          error: "HTTP " + projectStatus + " (OAuth scope may be missing)"
        });
      }
      
      // Test 2: GET /v1/projects/{scriptId}/deployments
      const deploymentsUrl = "https://script.googleapis.com/v1/projects/" + scriptId + "/deployments";
      const deploymentsResp = UrlFetchApp.fetch(deploymentsUrl, {
        method: "get",
        headers: {
          "Authorization": "Bearer " + token
        },
        muteHttpExceptions: true
      });
      
      const deploymentsStatus = deploymentsResp.getResponseCode();
      if (deploymentsStatus === 200) {
        const deploymentsData = JSON.parse(deploymentsResp.getContentText());
        const deploymentCount = (deploymentsData.deployments && deploymentsData.deployments.length) || 0;
        results.push({
          test: "Apps Script Deployments",
          ok: true,
          status: 200,
          body_excerpt: "count=" + deploymentCount,
          correlation_id: "N/A",
          error: null
        });
      } else {
        results.push({
          test: "Apps Script Deployments",
          ok: false,
          status: deploymentsStatus,
          body_excerpt: "N/A",
          correlation_id: "N/A",
          error: "HTTP " + deploymentsStatus + " (OAuth scope may be missing)"
        });
      }
      
    } catch (e) {
      results.push({
        test: "Apps Script (exception)",
        ok: false,
        status: 0,
        body_excerpt: "N/A",
        correlation_id: "N/A",
        error: "Exception: " + String(e.message || e)
      });
    }
    
    return results;
  }

  /**
   * Audit Logs Cloud Run (lecture logs mcp-memory-proxy)
   */
  function _auditCloudRunLogs_() {
    const results = [];
    
    try {
      const proxyUrl = _getSetting_("mcp_proxy_url");
      const apiKey = _getSetting_("mcp_api_key");
      
      if (!proxyUrl || !apiKey) {
        results.push({
          test: "Cloud Run Logs",
          ok: false,
          status: 401,
          body_excerpt: "N/A",
          correlation_id: "N/A",
          error: "SETTINGS: mcp_proxy_url or mcp_api_key not found"
        });
        return results;
      }
      
      // Test: POST /infra/logs/query
      const logsUrl = proxyUrl + "/infra/logs/query";
      const logsPayload = {
        resource_type: "cloud_run_revision",
        name: "mcp-memory-proxy",
        time_range_minutes: 60,
        limit: 10
      };
      
      const logsResp = UrlFetchApp.fetch(logsUrl, {
        method: "post",
        contentType: "application/json",
        payload: JSON.stringify(logsPayload),
        headers: {
          "X-API-Key": apiKey
        },
        muteHttpExceptions: true
      });
      
      const logsStatus = logsResp.getResponseCode();
      if (logsStatus === 200) {
        const logsData = JSON.parse(logsResp.getContentText());
        const entryCount = (logsData.entries && logsData.entries.length) || 0;
        results.push({
          test: "Cloud Run Logs Query",
          ok: true,
          status: 200,
          body_excerpt: "entries=" + entryCount,
          correlation_id: logsData.correlation_id || "N/A",
          error: null
        });
      } else if (logsStatus === 403) {
        results.push({
          test: "Cloud Run Logs Query",
          ok: false,
          status: 403,
          body_excerpt: "N/A",
          correlation_id: "N/A",
          error: "POST blocked (READ_ONLY_MODE=true)"
        });
      } else {
        results.push({
          test: "Cloud Run Logs Query",
          ok: false,
          status: logsStatus,
          body_excerpt: "N/A",
          correlation_id: "N/A",
          error: "HTTP " + logsStatus
        });
      }
      
    } catch (e) {
      results.push({
        test: "Cloud Run Logs (exception)",
        ok: false,
        status: 0,
        body_excerpt: "N/A",
        correlation_id: "N/A",
        error: "Exception: " + String(e.message || e)
      });
    }
    
    return results;
  }

  /**
   * Public API: Run full audit (all briques)
   * Returns array of all results
   */
  function runFullAudit() {
    const allResults = [];
    
    // Brique 1: Cloud Run Proxy
    const proxyResults = _auditCloudRunProxy_();
    allResults.push({
      brique: "1. Cloud Run Proxy (MCP)",
      tests: proxyResults
    });
    
    // Brique 2: Hub Sheets
    const sheetsResults = _auditHubSheets_();
    allResults.push({
      brique: "2. Hub Sheets (direct)",
      tests: sheetsResults
    });
    
    // Brique 3: Drive
    const driveResults = _auditDrive_();
    allResults.push({
      brique: "3. Drive (folders)",
      tests: driveResults
    });
    
    // Brique 4: GitHub
    const githubResults = _auditGitHub_();
    allResults.push({
      brique: "4. GitHub (repo/commits)",
      tests: githubResults
    });
    
    // Brique 5: Apps Script
    const appsScriptResults = _auditAppsScript_();
    allResults.push({
      brique: "5. Apps Script (project)",
      tests: appsScriptResults
    });
    
    // Brique 6: Cloud Run Logs
    const logsResults = _auditCloudRunLogs_();
    allResults.push({
      brique: "6. Cloud Run Logs",
      tests: logsResults
    });
    
    return allResults;
  }

  return {
    runFullAudit: runFullAudit
  };

})();

/**
 * Menu action: Audit Lecture Partout
 * Called from G01_UI_MENU.gs
 */
function MCP_AUDIT_readEverywhere() {
  const ui = SpreadsheetApp.getUi();
  
  const response = ui.alert(
    "MCP — Audit Lecture Partout",
    "This audit will test READ access to all briques:\n\n" +
    "1. Cloud Run Proxy (/health, /infra/whoami, /sheets)\n" +
    "2. Hub Sheets (SETTINGS, MEMORY_LOG, DRIVE_INVENTORY)\n" +
    "3. Drive (snapshots, archives, memory root)\n" +
    "4. GitHub (repo info, last 5 commits)\n" +
    "5. Apps Script (project, deployments)\n" +
    "6. Cloud Run Logs (query mcp-memory-proxy)\n\n" +
    "Continue?",
    ui.ButtonSet.YES_NO
  );
  
  if (response !== ui.Button.YES) {
    ui.alert("MCP Audit", "Audit cancelled.", ui.ButtonSet.OK);
    return;
  }
  
  try {
    const results = MCP_AUDIT.runFullAudit();
    
    // Format results for display
    const lines = [];
    lines.push("=== AUDIT LECTURE PARTOUT ===");
    lines.push("");
    
    let totalTests = 0;
    let passedTests = 0;
    
    for (let i = 0; i < results.length; i++) {
      const brique = results[i];
      lines.push(brique.brique);
      lines.push("");
      
      for (let j = 0; j < brique.tests.length; j++) {
        const test = brique.tests[j];
        totalTests++;
        if (test.ok) passedTests++;
        
        const icon = test.ok ? "✅" : "❌";
        lines.push(icon + " " + test.test);
        lines.push("   Status: " + test.status);
        lines.push("   Body: " + test.body_excerpt);
        if (!test.ok && test.error) {
          lines.push("   ⚠️ Error: " + test.error);
        }
        if (test.correlation_id && test.correlation_id !== "N/A") {
          lines.push("   Correlation: " + test.correlation_id);
        }
        lines.push("");
      }
    }
    
    lines.push("=== SUMMARY ===");
    lines.push("Total tests: " + totalTests);
    lines.push("Passed: " + passedTests);
    lines.push("Failed: " + (totalTests - passedTests));
    lines.push("");
    lines.push("Timestamp: " + new Date().toISOString());
    
    // Show results in alert (truncated if too long)
    const message = lines.join("\n");
    const maxLen = 2000;
    const displayMessage = message.length > maxLen ? message.slice(0, maxLen) + "\n\n... (truncated)" : message;
    
    ui.alert(
      "MCP — Audit Results",
      displayMessage,
      ui.ButtonSet.OK
    );
    
    // Also log to Logger for full details
    Logger.log("=== FULL AUDIT RESULTS ===");
    Logger.log(JSON.stringify(results, null, 2));
    
  } catch (e) {
    ui.alert(
      "MCP Audit — Error",
      "Exception: " + String(e.message || e) + "\n\n" +
      "Check Logger (Ctrl+Enter) for details.",
      ui.ButtonSet.OK
    );
    Logger.log("Audit exception: " + String(e.stack || e));
  }
}
