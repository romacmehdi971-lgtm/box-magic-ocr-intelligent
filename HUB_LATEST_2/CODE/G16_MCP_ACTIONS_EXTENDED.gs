// File: /CODE/G16_MCP_ACTIONS_EXTENDED.gs
// HUB IAPF Memory — Phase 2 Actions MCP (Extension contrôlée)

/**
 * PHASE 2 MCP ACTIONS - One-Shot Complete
 * 
 * Menu "Actions MCP" unifié avec 18 endpoints (6 domaines):
 * - Drive (4 endpoints READ_ONLY)
 * - Apps Script (4 endpoints READ_ONLY)
 * - Cloud Run (3 endpoints READ_ONLY)
 * - Secrets (4 endpoints: 2 READ + 2 WRITE gouverné)
 * - Web (2 endpoints READ_ONLY)
 * - Terminal (1 endpoint WRITE gouverné)
 * 
 * Principes:
 * - READ_ONLY par défaut
 * - Journalisation obligatoire (MEMORY_LOG + run_id)
 * - Pagination + limites
 * - Redaction systématique
 * - Mode DRY_RUN disponible (WRITE)
 * - Un seul GO pour WRITE_APPLY
 */

// ============================================================================
// DRIVE ACTIONS
// ============================================================================

function MCP_ACTION_driveListTree() {
  const ui = SpreadsheetApp.getUi();
  
  const folderIdResp = ui.prompt(
    "MCP Drive — List Tree",
    "Entrer l'ID du folder Drive:\n(ex: 1ABC...)",
    ui.ButtonSet.OK_CANCEL
  );
  
  if (folderIdResp.getSelectedButton() !== ui.Button.OK) return;
  
  const folderId = folderIdResp.getResponseText().trim();
  if (!folderId) {
    ui.alert("Error", "Folder ID requis", ui.ButtonSet.OK);
    return;
  }
  
  try {
    const response = MCP_HTTP.driveListTree(folderId, {
      max_depth: 2,
      limit: 100
    });
    
    if (response.ok) {
      ui.alert(
        "MCP Drive — List Tree OK",
        `run_id: ${response.run_id}\n` +
        `Folder: ${response.folder_name}\n` +
        `Items: ${response.total_items}\n\n` +
        `Voir MEMORY_LOG pour détails`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", response.error || "Unknown error", ui.ButtonSet.OK);
    }
  } catch (e) {
    ui.alert("Error", String(e), ui.ButtonSet.OK);
  }
}

function MCP_ACTION_driveFileMetadata() {
  const ui = SpreadsheetApp.getUi();
  
  const fileIdResp = ui.prompt(
    "MCP Drive — File Metadata",
    "Entrer l'ID du fichier Drive:",
    ui.ButtonSet.OK_CANCEL
  );
  
  if (fileIdResp.getSelectedButton() !== ui.Button.OK) return;
  
  const fileId = fileIdResp.getResponseText().trim();
  if (!fileId) {
    ui.alert("Error", "File ID requis", ui.ButtonSet.OK);
    return;
  }
  
  try {
    const response = MCP_HTTP.driveFileMetadata(fileId);
    
    if (response.ok) {
      const file = response.file;
      ui.alert(
        "MCP Drive — Metadata OK",
        `run_id: ${response.run_id}\n` +
        `Nom: ${file.name}\n` +
        `Type: ${file.mimeType}\n` +
        `Taille: ${file.size} bytes\n` +
        `Modifié: ${file.modifiedTime}\n\n` +
        `Voir MEMORY_LOG pour détails`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", response.error || "Unknown error", ui.ButtonSet.OK);
    }
  } catch (e) {
    ui.alert("Error", String(e), ui.ButtonSet.OK);
  }
}

function MCP_ACTION_driveSearch() {
  const ui = SpreadsheetApp.getUi();
  
  const queryResp = ui.prompt(
    "MCP Drive — Search",
    "Entrer la requête de recherche:",
    ui.ButtonSet.OK_CANCEL
  );
  
  if (queryResp.getSelectedButton() !== ui.Button.OK) return;
  
  const query = queryResp.getResponseText().trim();
  if (!query) {
    ui.alert("Error", "Query requis", ui.ButtonSet.OK);
    return;
  }
  
  try {
    const response = MCP_HTTP.driveSearch(query, {limit: 10});
    
    if (response.ok) {
      ui.alert(
        "MCP Drive — Search OK",
        `run_id: ${response.run_id}\n` +
        `Query: ${response.query}\n` +
        `Résultats: ${response.total_results}\n\n` +
        `Voir MEMORY_LOG pour détails`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", response.error || "Unknown error", ui.ButtonSet.OK);
    }
  } catch (e) {
    ui.alert("Error", String(e), ui.ButtonSet.OK);
  }
}

// ============================================================================
// APPS SCRIPT ACTIONS
// ============================================================================

function MCP_ACTION_appsScriptDeployments() {
  const ui = SpreadsheetApp.getUi();
  
  const scriptId = ScriptApp.getScriptId();
  
  try {
    const response = MCP_HTTP.appsScriptDeployments(scriptId, {limit: 10});
    
    if (response.ok) {
      ui.alert(
        "MCP Apps Script — Deployments OK",
        `run_id: ${response.run_id}\n` +
        `Script ID: ${scriptId}\n` +
        `Deployments: ${response.total_deployments}\n\n` +
        `Voir MEMORY_LOG pour détails`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", response.error || "Unknown error", ui.ButtonSet.OK);
    }
  } catch (e) {
    ui.alert("Error", String(e), ui.ButtonSet.OK);
  }
}

function MCP_ACTION_appsScriptStructure() {
  const ui = SpreadsheetApp.getUi();
  
  const scriptId = ScriptApp.getScriptId();
  
  try {
    const response = MCP_HTTP.appsScriptStructure(scriptId);
    
    if (response.ok) {
      ui.alert(
        "MCP Apps Script — Structure OK",
        `run_id: ${response.run_id}\n` +
        `Projet: ${response.project_name}\n` +
        `Fichiers: ${response.total_files}\n` +
        `Fonctions: ${response.total_functions}\n\n` +
        `Voir MEMORY_LOG pour détails`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", response.error || "Unknown error", ui.ButtonSet.OK);
    }
  } catch (e) {
    ui.alert("Error", String(e), ui.ButtonSet.OK);
  }
}

// ============================================================================
// CLOUD RUN ACTIONS
// ============================================================================

function MCP_ACTION_cloudRunServiceStatus() {
  const ui = SpreadsheetApp.getUi();
  
  const serviceNameResp = ui.prompt(
    "MCP Cloud Run — Service Status",
    "Entrer le nom du service:\n(ex: mcp-memory-proxy)",
    ui.ButtonSet.OK_CANCEL
  );
  
  if (serviceNameResp.getSelectedButton() !== ui.Button.OK) return;
  
  const serviceName = serviceNameResp.getResponseText().trim();
  if (!serviceName) {
    ui.alert("Error", "Service name requis", ui.ButtonSet.OK);
    return;
  }
  
  try {
    const response = MCP_HTTP.cloudRunServiceStatus(serviceName);
    
    if (response.ok) {
      const status = response.status;
      ui.alert(
        "MCP Cloud Run — Service Status OK",
        `run_id: ${response.run_id}\n` +
        `Service: ${serviceName}\n` +
        `Revision: ${status.latest_ready_revision}\n` +
        `Ready: ${status.ready_condition}\n` +
        `Env: ${status.environment}\n\n` +
        `Voir MEMORY_LOG pour détails`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", response.error || "Unknown error", ui.ButtonSet.OK);
    }
  } catch (e) {
    ui.alert("Error", String(e), ui.ButtonSet.OK);
  }
}

// ============================================================================
// SECRET MANAGER ACTIONS (GOVERNED)
// ============================================================================

function MCP_ACTION_secretsList() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    const response = MCP_HTTP.secretsList({limit: 20});
    
    if (response.ok) {
      ui.alert(
        "MCP Secret Manager — List OK",
        `run_id: ${response.run_id}\n` +
        `Projet: ${response.project_id}\n` +
        `Secrets: ${response.total_secrets}\n\n` +
        `⚠️ Valeurs JAMAIS retournées (seulement métadonnées)\n\n` +
        `Voir MEMORY_LOG pour détails`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", response.error || "Unknown error", ui.ButtonSet.OK);
    }
  } catch (e) {
    ui.alert("Error", String(e), ui.ButtonSet.OK);
  }
}

function MCP_ACTION_secretGetReference() {
  const ui = SpreadsheetApp.getUi();
  
  const secretIdResp = ui.prompt(
    "MCP Secret Manager — Get Reference",
    "Entrer l'ID du secret:\n(ex: mcp_api_key)",
    ui.ButtonSet.OK_CANCEL
  );
  
  if (secretIdResp.getSelectedButton() !== ui.Button.OK) return;
  
  const secretId = secretIdResp.getResponseText().trim();
  if (!secretId) {
    ui.alert("Error", "Secret ID requis", ui.ButtonSet.OK);
    return;
  }
  
  try {
    const response = MCP_HTTP.secretGetReference(secretId);
    
    if (response.ok) {
      ui.alert(
        "MCP Secret Manager — Reference OK",
        `run_id: ${response.run_id}\n` +
        `Secret ID: ${secretId}\n` +
        `Version: ${response.version}\n` +
        `Reference: ${response.reference}\n\n` +
        `⚠️ Valeur: [REDACTED] (jamais retournée)\n\n` +
        `Stocker cette référence dans SETTINGS`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", response.error || "Unknown error", ui.ButtonSet.OK);
    }
  } catch (e) {
    ui.alert("Error", String(e), ui.ButtonSet.OK);
  }
}

function MCP_ACTION_secretCreateDryRun() {
  const ui = SpreadsheetApp.getUi();
  
  const secretIdResp = ui.prompt(
    "MCP Secret Manager — Create (DRY_RUN)",
    "Entrer l'ID du nouveau secret:",
    ui.ButtonSet.OK_CANCEL
  );
  
  if (secretIdResp.getSelectedButton() !== ui.Button.OK) return;
  
  const secretId = secretIdResp.getResponseText().trim();
  if (!secretId) {
    ui.alert("Error", "Secret ID requis", ui.ButtonSet.OK);
    return;
  }
  
  try {
    const response = MCP_HTTP.secretCreate(secretId, "dummy_value_for_dryrun", {
      dry_run: true,
      labels: {env: "staging", service: "test"}
    });
    
    if (response.ok) {
      ui.alert(
        "MCP Secret Manager — Create DRY_RUN OK",
        `run_id: ${response.run_id}\n` +
        `Mode: ${response.dry_run ? "DRY_RUN" : "APPLIED"}\n` +
        `Secret ID: ${secretId}\n` +
        `Reference: ${response.reference}\n\n` +
        `⚠️ ${response.message}\n\n` +
        `Pour appliquer: utiliser MCP_ACTION_secretCreateApply()`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", response.error || "Unknown error", ui.ButtonSet.OK);
    }
  } catch (e) {
    ui.alert("Error", String(e), ui.ButtonSet.OK);
  }
}

function MCP_ACTION_secretCreateApply() {
  const ui = SpreadsheetApp.getUi();
  
  const secretIdResp = ui.prompt(
    "MCP Secret Manager — Create (APPLY)",
    "Entrer l'ID du nouveau secret:",
    ui.ButtonSet.OK_CANCEL
  );
  
  if (secretIdResp.getSelectedButton() !== ui.Button.OK) return;
  
  const secretId = secretIdResp.getResponseText().trim();
  if (!secretId) {
    ui.alert("Error", "Secret ID requis", ui.ButtonSet.OK);
    return;
  }
  
  const valueResp = ui.prompt(
    "MCP Secret Manager — Create (APPLY)",
    "Entrer la valeur du secret:\n(sera redactée dans tous les logs)",
    ui.ButtonSet.OK_CANCEL
  );
  
  if (valueResp.getSelectedButton() !== ui.Button.OK) return;
  
  const value = valueResp.getResponseText().trim();
  if (!value) {
    ui.alert("Error", "Valeur requise", ui.ButtonSet.OK);
    return;
  }
  
  // GO Confirmation
  const confirm = ui.alert(
    "MCP Secret Manager — Create (APPLY)",
    `⚠️ WRITE_APPLY\n\n` +
    `Domaine: Secret Manager\n` +
    `Action: Create secret "${secretId}"\n` +
    `Env: STAGING\n\n` +
    `Cette action créera le secret réellement.\n\n` +
    `Continuer avec WRITE_APPLY?`,
    ui.ButtonSet.YES_NO
  );
  
  if (confirm !== ui.Button.YES) {
    ui.alert("MCP", "Action annulée", ui.ButtonSet.OK);
    return;
  }
  
  try {
    const response = MCP_HTTP.secretCreate(secretId, value, {
      dry_run: false,
      labels: {env: "staging"}
    });
    
    if (response.ok) {
      ui.alert(
        "MCP Secret Manager — Create APPLIED ✅",
        `run_id: ${response.run_id}\n` +
        `Mode: APPLIED\n` +
        `Secret ID: ${secretId}\n` +
        `Reference: ${response.reference}\n\n` +
        `✅ ${response.message}\n\n` +
        `Stocker cette référence dans SETTINGS:\n` +
        `${response.reference}`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", response.error || "Unknown error", ui.ButtonSet.OK);
    }
  } catch (e) {
    ui.alert("Error", String(e), ui.ButtonSet.OK);
  }
}

// ============================================================================
// WEB ACCESS ACTIONS
// ============================================================================

function MCP_ACTION_webSearch() {
  const ui = SpreadsheetApp.getUi();
  
  const queryResp = ui.prompt(
    "MCP Web — Search",
    "Entrer la requête de recherche web:",
    ui.ButtonSet.OK_CANCEL
  );
  
  if (queryResp.getSelectedButton() !== ui.Button.OK) return;
  
  const query = queryResp.getResponseText().trim();
  if (!query) {
    ui.alert("Error", "Query requis", ui.ButtonSet.OK);
    return;
  }
  
  try {
    const response = MCP_HTTP.webSearch(query, {max_results: 5});
    
    if (response.ok) {
      ui.alert(
        "MCP Web — Search OK",
        `run_id: ${response.run_id}\n` +
        `Query: ${response.query}\n` +
        `Résultats: ${response.total_results}\n` +
        `Quota restant: ${response.quota_remaining}\n\n` +
        `Voir MEMORY_LOG pour détails`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", response.error || "Unknown error", ui.ButtonSet.OK);
    }
  } catch (e) {
    ui.alert("Error", String(e), ui.ButtonSet.OK);
  }
}

// ============================================================================
// TERMINAL RUNNER ACTION (GOVERNED)
// ============================================================================

function MCP_ACTION_terminalRunReadOnly() {
  const ui = SpreadsheetApp.getUi();
  
  const commandResp = ui.prompt(
    "MCP Terminal — Run (READ_ONLY)",
    "Entrer la commande (allowlist READ_ONLY):\nEx: gcloud run services describe mcp-memory-proxy --region=us-central1",
    ui.ButtonSet.OK_CANCEL
  );
  
  if (commandResp.getSelectedButton() !== ui.Button.OK) return;
  
  const command = commandResp.getResponseText().trim();
  if (!command) {
    ui.alert("Error", "Command requis", ui.ButtonSet.OK);
    return;
  }
  
  try {
    const response = MCP_HTTP.terminalRun(command, {
      mode: "READ_ONLY",
      dry_run: false
    });
    
    if (response.ok) {
      ui.alert(
        "MCP Terminal — Run OK",
        `run_id: ${response.run_id}\n` +
        `Command: ${command}\n` +
        `Exit code: ${response.exit_code}\n` +
        `Duration: ${response.duration_ms}ms\n\n` +
        `Voir MEMORY_LOG pour output complet`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", response.error || "Unknown error", ui.ButtonSet.OK);
    }
  } catch (e) {
    ui.alert("Error", String(e), ui.ButtonSet.OK);
  }
}
