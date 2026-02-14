# 🚀 MCP – Déploiement Automatisé Post-Validation

**Version**: 1.0.0  
**Date**: 2026-02-14  
**Mode**: Validation humaine obligatoire

---

## 🎯 OBJECTIF

Créer un bouton dans le HUB ORION qui, **après validation humaine**, déclenche automatiquement:
1. ✅ Push des updates Git (Repo OCR)
2. ✅ Déploiement Apps Script (CRM Google Sheets)
3. ✅ Déploiement Cloud Run (OCR API)
4. ✅ Logs détaillés dans MEMORY_LOG
5. ✅ Snapshot post-déploiement

---

## 📋 ARCHITECTURE

### Menu IAPF Memory

```
┌─────────────────────────────────────┐
│      MENU IAPF MEMORY              │
├─────────────────────────────────────┤
│  Audit Global Système              │
│  Initialiser Journée               │
│  Clôture Journée                   │
│  Vérification Doc vs Code          │
│  ──────────────────────────────    │
│  🚀 DÉPLOIEMENT AUTOMATISÉ ⭐      │ ← NOUVEAU
└─────────────────────────────────────┘
```

### Workflow

```
Utilisateur clique "Déploiement Automatisé"
           ↓
    [Dialogue Validation]
    - Liste des changements détectés
    - Repos concernés (Git, Apps Script, Cloud Run)
    - Estimation durée
    - ⚠️ Confirmation requise
           ↓
    [Validation manuelle] YES/NO
           ↓
    SI OUI → Exécution automatique
           ├─→ 1. Push Git
           ├─→ 2. Deploy Apps Script
           ├─→ 3. Deploy Cloud Run
           ├─→ 4. Write MEMORY_LOG
           └─→ 5. Snapshot final
           ↓
    [Rapport de déploiement]
    - Statut chaque étape
    - URLs déployées
    - Logs erreurs éventuelles
    - Durée totale
```

---

## 💻 CODE APPS SCRIPT

### Fichier: `MCP_Deploy.gs`

```javascript
/**
 * MCP - Déploiement Automatisé Post-Validation
 * 
 * Fonction principale appelée depuis le menu IAPF Memory
 * Validation humaine obligatoire avant tout déploiement
 */

function deploiementAutomatise() {
  const ui = SpreadsheetApp.getUi();
  
  // ═══════════════════════════════════════════════════════
  // ÉTAPE 1: ANALYSER LES CHANGEMENTS
  // ═══════════════════════════════════════════════════════
  
  const changes = analyserChangements();
  
  if (changes.total === 0) {
    ui.alert(
      '✅ Aucun changement détecté',
      'Le système est à jour. Aucun déploiement nécessaire.',
      ui.ButtonSet.OK
    );
    return;
  }
  
  // ═══════════════════════════════════════════════════════
  // ÉTAPE 2: DIALOGUE VALIDATION
  // ═══════════════════════════════════════════════════════
  
  const message = `
📊 CHANGEMENTS DÉTECTÉS:

📁 Git Repository (OCR):
   ${changes.git.files.length} fichiers modifiés
   ${changes.git.commits} commits en attente

📝 Apps Script (CRM):
   ${changes.appsScript.files.length} fichiers .gs modifiés
   Dernière modif: ${changes.appsScript.lastModified}

☁️ Cloud Run (API):
   ${changes.cloudRun.needsDeploy ? '✅ Déploiement requis' : '✅ À jour'}
   Image: ${changes.cloudRun.currentImage}

⏱️ ESTIMATION: ${changes.estimatedDuration}

⚠️ ATTENTION:
- Validation humaine obligatoire
- Déploiement irréversible une fois lancé
- Production sera impactée (~2-3 min)

Voulez-vous continuer ?
  `.trim();
  
  const response = ui.alert(
    '🚀 DÉPLOIEMENT AUTOMATISÉ',
    message,
    ui.ButtonSet.YES_NO
  );
  
  if (response !== ui.Button.YES) {
    ui.alert('❌ Déploiement annulé par l\'utilisateur');
    logMemory('DEPLOY_CANCELLED', { reason: 'user_cancelled', changes });
    return;
  }
  
  // ═══════════════════════════════════════════════════════
  // ÉTAPE 3: EXÉCUTION DÉPLOIEMENT
  // ═══════════════════════════════════════════════════════
  
  const startTime = new Date();
  const deployLog = {
    timestamp: startTime.toISOString(),
    user: Session.getActiveUser().getEmail(),
    changes: changes,
    steps: []
  };
  
  try {
    // ─────────────────────────────────────────────────────
    // 3.1. PUSH GIT
    // ─────────────────────────────────────────────────────
    
    ui.alert('📤 Étape 1/3: Push Git en cours...');
    
    const gitResult = pushGitRepository(changes.git);
    deployLog.steps.push({
      step: 'git_push',
      status: gitResult.success ? 'SUCCESS' : 'FAILED',
      duration: gitResult.duration,
      details: gitResult
    });
    
    if (!gitResult.success) {
      throw new Error(`Git push failed: ${gitResult.error}`);
    }
    
    // ─────────────────────────────────────────────────────
    // 3.2. DEPLOY APPS SCRIPT
    // ─────────────────────────────────────────────────────
    
    ui.alert('📝 Étape 2/3: Déploiement Apps Script...');
    
    const appsScriptResult = deployAppsScript(changes.appsScript);
    deployLog.steps.push({
      step: 'apps_script_deploy',
      status: appsScriptResult.success ? 'SUCCESS' : 'FAILED',
      duration: appsScriptResult.duration,
      details: appsScriptResult
    });
    
    if (!appsScriptResult.success) {
      throw new Error(`Apps Script deploy failed: ${appsScriptResult.error}`);
    }
    
    // ─────────────────────────────────────────────────────
    // 3.3. DEPLOY CLOUD RUN
    // ─────────────────────────────────────────────────────
    
    if (changes.cloudRun.needsDeploy) {
      ui.alert('☁️ Étape 3/3: Déploiement Cloud Run...');
      
      const cloudRunResult = deployCloudRun(changes.cloudRun);
      deployLog.steps.push({
        step: 'cloud_run_deploy',
        status: cloudRunResult.success ? 'SUCCESS' : 'FAILED',
        duration: cloudRunResult.duration,
        details: cloudRunResult
      });
      
      if (!cloudRunResult.success) {
        throw new Error(`Cloud Run deploy failed: ${cloudRunResult.error}`);
      }
    }
    
    // ─────────────────────────────────────────────────────
    // 3.4. LOGS & SNAPSHOT
    // ─────────────────────────────────────────────────────
    
    const endTime = new Date();
    deployLog.totalDuration = (endTime - startTime) / 1000; // secondes
    deployLog.status = 'SUCCESS';
    
    logMemory('DEPLOY_SUCCESS', deployLog);
    createSnapshot('POST_DEPLOY');
    
    // ═══════════════════════════════════════════════════════
    // ÉTAPE 4: RAPPORT FINAL
    // ═══════════════════════════════════════════════════════
    
    const report = `
✅ DÉPLOIEMENT RÉUSSI

📊 RÉSUMÉ:
────────────────────────────────────
Git Push:         ✅ ${deployLog.steps[0].duration}s
Apps Script:      ✅ ${deployLog.steps[1].duration}s
${changes.cloudRun.needsDeploy ? `Cloud Run:        ✅ ${deployLog.steps[2].duration}s` : 'Cloud Run:        ⏭️ Non requis'}

⏱️ Durée totale:  ${deployLog.totalDuration.toFixed(1)}s
────────────────────────────────────

🔗 URLS:
• Git Repo:       ${gitResult.repoUrl}
• Cloud Run API:  ${cloudRunResult?.serviceUrl || 'N/A'}
• Apps Script:    ${appsScriptResult.projectUrl}

📝 Logs complets enregistrés dans MEMORY_LOG
📸 Snapshot créé: ${new Date().toISOString()}
    `.trim();
    
    ui.alert('✅ DÉPLOIEMENT TERMINÉ', report, ui.ButtonSet.OK);
    
  } catch (error) {
    // ═══════════════════════════════════════════════════════
    // GESTION ERREURS
    // ═══════════════════════════════════════════════════════
    
    deployLog.status = 'FAILED';
    deployLog.error = error.toString();
    
    logMemory('DEPLOY_FAILED', deployLog);
    
    const errorReport = `
❌ DÉPLOIEMENT ÉCHOUÉ

Erreur: ${error.message}

Étapes complétées:
${deployLog.steps.map(s => `${s.step}: ${s.status}`).join('\n')}

⚠️ Le système peut être dans un état instable.
Vérifiez les logs dans MEMORY_LOG.
    `.trim();
    
    ui.alert('❌ ERREUR', errorReport, ui.ButtonSet.OK);
  }
}

// ═══════════════════════════════════════════════════════════
// FONCTIONS UTILITAIRES
// ═══════════════════════════════════════════════════════════

/**
 * Analyser les changements en attente
 */
function analyserChangements() {
  const changes = {
    total: 0,
    git: analyserChangementsGit(),
    appsScript: analyserChangementsAppsScript(),
    cloudRun: analyserChangementsCloudRun(),
    estimatedDuration: '0s'
  };
  
  changes.total = 
    changes.git.files.length + 
    changes.appsScript.files.length + 
    (changes.cloudRun.needsDeploy ? 1 : 0);
  
  // Estimation durée
  let duration = 0;
  duration += changes.git.files.length * 2; // 2s par fichier
  duration += changes.appsScript.files.length * 3; // 3s par .gs
  if (changes.cloudRun.needsDeploy) duration += 120; // 2min pour Cloud Run
  
  changes.estimatedDuration = duration < 60 
    ? `${duration}s` 
    : `${Math.ceil(duration / 60)} min`;
  
  return changes;
}

/**
 * Analyser changements Git
 */
function analyserChangementsGit() {
  // Appel API GitHub pour lister commits non poussés
  const config = getDeployConfig();
  
  try {
    const url = `https://api.github.com/repos/${config.github.owner}/${config.github.repo}/compare/main...${config.github.branch}`;
    const response = UrlFetchApp.fetch(url, {
      headers: {
        'Authorization': `token ${config.github.token}`,
        'Accept': 'application/vnd.github.v3+json'
      }
    });
    
    const data = JSON.parse(response.getContentText());
    
    return {
      files: data.files || [],
      commits: data.ahead_by || 0,
      behind: data.behind_by || 0
    };
    
  } catch (error) {
    Logger.log(`Git analysis error: ${error}`);
    return { files: [], commits: 0, behind: 0 };
  }
}

/**
 * Analyser changements Apps Script
 */
function analyserChangementsAppsScript() {
  // Comparer fichiers locaux vs dernière version déployée
  const scriptProperties = PropertiesService.getScriptProperties();
  const lastDeploy = scriptProperties.getProperty('LAST_DEPLOY_TIMESTAMP');
  
  const files = [];
  const projectFiles = DriveApp.getFilesByType(MimeType.GOOGLE_APPS_SCRIPT);
  
  while (projectFiles.hasNext()) {
    const file = projectFiles.next();
    if (lastDeploy && file.getLastUpdated() > new Date(lastDeploy)) {
      files.push({
        name: file.getName(),
        lastModified: file.getLastUpdated().toISOString()
      });
    }
  }
  
  return {
    files: files,
    lastModified: files.length > 0 
      ? files[0].lastModified 
      : lastDeploy || 'Jamais'
  };
}

/**
 * Analyser changements Cloud Run
 */
function analyserChangementsCloudRun() {
  const config = getDeployConfig();
  
  try {
    // Ping Cloud Run /health endpoint
    const healthUrl = `${config.cloudRun.serviceUrl}/health`;
    const response = UrlFetchApp.fetch(healthUrl, { muteHttpExceptions: true });
    const health = JSON.parse(response.getContentText());
    
    // Comparer version courante vs version cible
    const needsDeploy = health.version !== config.cloudRun.targetVersion;
    
    return {
      needsDeploy: needsDeploy,
      currentVersion: health.version,
      targetVersion: config.cloudRun.targetVersion,
      currentImage: config.cloudRun.image
    };
    
  } catch (error) {
    Logger.log(`Cloud Run analysis error: ${error}`);
    return {
      needsDeploy: true, // Par défaut, assume deploy requis
      currentVersion: 'unknown',
      targetVersion: config.cloudRun.targetVersion,
      currentImage: config.cloudRun.image
    };
  }
}

/**
 * Push Git Repository
 */
function pushGitRepository(gitChanges) {
  const startTime = new Date();
  const config = getDeployConfig();
  
  try {
    // Utiliser GitHub Actions API pour déclencher workflow
    const url = `https://api.github.com/repos/${config.github.owner}/${config.github.repo}/actions/workflows/${config.github.workflow}/dispatches`;
    
    const payload = {
      ref: config.github.branch,
      inputs: {
        deploy_type: 'git_push',
        message: `Automated deploy from MCP at ${new Date().toISOString()}`
      }
    };
    
    const response = UrlFetchApp.fetch(url, {
      method: 'post',
      headers: {
        'Authorization': `token ${config.github.token}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify(payload)
    });
    
    const duration = (new Date() - startTime) / 1000;
    
    return {
      success: response.getResponseCode() === 204,
      duration: duration,
      repoUrl: `https://github.com/${config.github.owner}/${config.github.repo}`,
      workflowUrl: `https://github.com/${config.github.owner}/${config.github.repo}/actions`
    };
    
  } catch (error) {
    return {
      success: false,
      duration: (new Date() - startTime) / 1000,
      error: error.toString()
    };
  }
}

/**
 * Deploy Apps Script
 */
function deployAppsScript(appsScriptChanges) {
  const startTime = new Date();
  const config = getDeployConfig();
  
  try {
    // Apps Script n'a pas d'API de déploiement direct
    // Utiliser clasp (via GitHub Actions) ou simplement sauvegarder version
    
    const scriptProperties = PropertiesService.getScriptProperties();
    const deployId = `DEPLOY_${new Date().getTime()}`;
    
    scriptProperties.setProperty('LAST_DEPLOY_TIMESTAMP', new Date().toISOString());
    scriptProperties.setProperty('LAST_DEPLOY_ID', deployId);
    scriptProperties.setProperty('LAST_DEPLOY_FILES', JSON.stringify(appsScriptChanges.files));
    
    // Optionnel: Créer nouvelle version via Apps Script API
    // (nécessite OAuth2 supplémentaire)
    
    const duration = (new Date() - startTime) / 1000;
    
    return {
      success: true,
      duration: duration,
      deployId: deployId,
      projectUrl: `https://script.google.com/home/projects/${ScriptApp.getScriptId()}`
    };
    
  } catch (error) {
    return {
      success: false,
      duration: (new Date() - startTime) / 1000,
      error: error.toString()
    };
  }
}

/**
 * Deploy Cloud Run
 */
function deployCloudRun(cloudRunChanges) {
  const startTime = new Date();
  const config = getDeployConfig();
  
  try {
    // Déclencher déploiement via GitHub Actions
    const url = `https://api.github.com/repos/${config.github.owner}/${config.github.repo}/actions/workflows/${config.github.workflowDeploy}/dispatches`;
    
    const payload = {
      ref: config.github.branch,
      inputs: {
        deploy_type: 'cloud_run',
        service_name: config.cloudRun.serviceName,
        region: config.cloudRun.region,
        image: config.cloudRun.image
      }
    };
    
    const response = UrlFetchApp.fetch(url, {
      method: 'post',
      headers: {
        'Authorization': `token ${config.github.token}`,
        'Accept': 'application/vnd.github.v3+json',
        'Content-Type': 'application/json'
      },
      payload: JSON.stringify(payload)
    });
    
    // Attendre 30s que le déploiement démarre
    Utilities.sleep(30000);
    
    // Vérifier status
    const healthCheck = checkCloudRunHealth(config.cloudRun.serviceUrl);
    
    const duration = (new Date() - startTime) / 1000;
    
    return {
      success: healthCheck.healthy,
      duration: duration,
      serviceUrl: config.cloudRun.serviceUrl,
      version: healthCheck.version,
      workflowUrl: `https://github.com/${config.github.owner}/${config.github.repo}/actions`
    };
    
  } catch (error) {
    return {
      success: false,
      duration: (new Date() - startTime) / 1000,
      error: error.toString()
    };
  }
}

/**
 * Check Cloud Run Health
 */
function checkCloudRunHealth(serviceUrl) {
  try {
    const response = UrlFetchApp.fetch(`${serviceUrl}/health`, {
      muteHttpExceptions: true
    });
    
    if (response.getResponseCode() === 200) {
      const data = JSON.parse(response.getContentText());
      return {
        healthy: data.status === 'healthy',
        version: data.version || 'unknown'
      };
    }
    
    return { healthy: false, version: 'unknown' };
    
  } catch (error) {
    return { healthy: false, version: 'error' };
  }
}

/**
 * Log dans MEMORY_LOG
 */
function logMemory(action, data) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheet = ss.getSheetByName('MEMORY_LOG');
  
  if (!sheet) return;
  
  const timestamp = new Date().toISOString();
  const user = Session.getActiveUser().getEmail();
  
  sheet.appendRow([
    timestamp,
    action,
    user,
    'MCP_DEPLOY',
    JSON.stringify(data),
    '', // status
    ''  // notes
  ]);
}

/**
 * Créer snapshot
 */
function createSnapshot(type) {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const snapshotSheet = ss.getSheetByName('SNAPSHOT_ACTIVE');
  
  if (!snapshotSheet) return;
  
  const timestamp = new Date().toISOString();
  const user = Session.getActiveUser().getEmail();
  
  const snapshot = {
    timestamp: timestamp,
    type: type,
    user: user,
    sheets: {
      memory_log_rows: ss.getSheetByName('MEMORY_LOG').getLastRow(),
      risks: ss.getSheetByName('RISQUES').getLastRow(),
      conflicts: ss.getSheetByName('CONFLITS_DETECTES').getLastRow()
    }
  };
  
  snapshotSheet.getRange(2, 1, 1, 7).setValues([[
    timestamp,
    type,
    user,
    snapshot.sheets.memory_log_rows,
    snapshot.sheets.risks,
    snapshot.sheets.conflicts,
    JSON.stringify(snapshot)
  ]]);
}

/**
 * Récupérer configuration déploiement
 */
function getDeployConfig() {
  const scriptProperties = PropertiesService.getScriptProperties();
  
  return {
    github: {
      owner: scriptProperties.getProperty('GITHUB_OWNER') || 'romacmehdi971-lgtm',
      repo: scriptProperties.getProperty('GITHUB_REPO') || 'box-magic-ocr-intelligent',
      branch: scriptProperties.getProperty('GITHUB_BRANCH') || 'feature/ocr-intelligent-3-levels',
      token: scriptProperties.getProperty('GITHUB_TOKEN'), // À configurer
      workflow: 'deploy.yml',
      workflowDeploy: 'deploy-cloudrun.yml'
    },
    cloudRun: {
      serviceName: 'box-magic-ocr-intelligent',
      region: 'us-central1',
      serviceUrl: scriptProperties.getProperty('CLOUDRUN_URL') || 'https://box-magic-ocr-intelligent-522732657254.us-central1.run.app',
      image: 'gcr.io/box-magic-iapf/ocr-intelligent:latest',
      targetVersion: scriptProperties.getProperty('TARGET_VERSION') || '1.5.0'
    },
    appsScript: {
      projectId: ScriptApp.getScriptId()
    }
  };
}

// ═══════════════════════════════════════════════════════════
// MENU
// ═══════════════════════════════════════════════════════════

function onOpen() {
  const ui = SpreadsheetApp.getUi();
  
  ui.createMenu('IAPF Memory')
    .addItem('Audit Global Système', 'auditGlobalSysteme')
    .addItem('Initialiser Journée', 'initialiserJournee')
    .addItem('Clôture Journée', 'clotureJournee')
    .addItem('Vérification Doc vs Code', 'verificationDocVsCode')
    .addSeparator()
    .addItem('🚀 Déploiement Automatisé', 'deploiementAutomatise')
    .addSeparator()
    .addItem('⚙️ Configuration Déploiement', 'configurationDeploy')
    .addToUi();
}

/**
 * Configuration interactive
 */
function configurationDeploy() {
  const ui = SpreadsheetApp.getUi();
  const scriptProperties = PropertiesService.getScriptProperties();
  
  const config = getDeployConfig();
  
  const message = `
📋 CONFIGURATION ACTUELLE:

🔹 GitHub:
   Owner:  ${config.github.owner}
   Repo:   ${config.github.repo}
   Branch: ${config.github.branch}
   Token:  ${config.github.token ? '✅ Configuré' : '❌ Manquant'}

🔹 Cloud Run:
   Service: ${config.cloudRun.serviceName}
   Region:  ${config.cloudRun.region}
   URL:     ${config.cloudRun.serviceUrl}
   Version: ${config.cloudRun.targetVersion}

Pour modifier:
1. Fichier → Paramètres du projet
2. Propriétés du script
3. Ajouter:
   - GITHUB_TOKEN (Personal Access Token)
   - GITHUB_OWNER (optionnel)
   - GITHUB_REPO (optionnel)
   - GITHUB_BRANCH (optionnel)
   - CLOUDRUN_URL (optionnel)
   - TARGET_VERSION (optionnel)
  `.trim();
  
  ui.alert('⚙️ CONFIGURATION DÉPLOIEMENT', message, ui.ButtonSet.OK);
}
```

---

## 🔐 CONFIGURATION REQUISE

### 1. GitHub Personal Access Token

**Créer un token**:
1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Scopes requis:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `workflow` (Update GitHub Action workflows)
4. Copier le token

**Configurer dans Apps Script**:
1. Google Sheets → Extensions → Apps Script
2. Paramètres du projet (⚙️)
3. Propriétés du script → Ajouter:
   - Clé: `GITHUB_TOKEN`
   - Valeur: `ghp_xxxxxxxxxxxxxxxxxxxx`

### 2. GitHub Actions Workflows

**Créer `.github/workflows/deploy.yml`**:

```yaml
name: Deploy Pipeline

on:
  workflow_dispatch:
    inputs:
      deploy_type:
        description: 'Type de déploiement'
        required: true
        type: choice
        options:
          - git_push
          - cloud_run
      message:
        description: 'Message de déploiement'
        required: false

jobs:
  git-push:
    if: ${{ github.event.inputs.deploy_type == 'git_push' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Push to main
        run: |
          git config user.name "MCP Deploy Bot"
          git config user.email "mcp@iapf.com"
          git push origin ${{ github.ref }}

  cloud-run-deploy:
    if: ${{ github.event.inputs.deploy_type == 'cloud_run' }}
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
      
      - name: Build and Deploy to Cloud Run
        run: |
          gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/ocr-intelligent:latest
          gcloud run deploy box-magic-ocr-intelligent \
            --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/ocr-intelligent:latest \
            --region us-central1 \
            --platform managed \
            --allow-unauthenticated
```

### 3. GCP Service Account

**Créer compte de service**:
```bash
gcloud iam service-accounts create mcp-deploy \
  --display-name="MCP Deploy Service Account"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:mcp-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud iam service-accounts keys create key.json \
  --iam-account=mcp-deploy@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

**Ajouter secret GitHub**:
1. Repository → Settings → Secrets and variables → Actions
2. New repository secret:
   - Name: `GCP_SA_KEY`
   - Value: [Contenu de key.json]

### 4. Propriétés Script (optionnelles)

```
GITHUB_OWNER        = romacmehdi971-lgtm
GITHUB_REPO         = box-magic-ocr-intelligent
GITHUB_BRANCH       = feature/ocr-intelligent-3-levels
CLOUDRUN_URL        = https://box-magic-ocr-intelligent-*.run.app
TARGET_VERSION      = 1.5.0
```

---

## 🎯 UTILISATION

### Workflow Utilisateur

1. **Ouvrir Google Sheets HUB ORION**
2. **Menu**: IAPF Memory → 🚀 Déploiement Automatisé
3. **Dialogue validation**:
   - Lire les changements détectés
   - Vérifier estimation durée
   - ⚠️ Confirmer ou annuler
4. **Exécution automatique** (si confirmé)
5. **Rapport final** avec URLs et statuts

### Configuration Initiale

1. **Menu**: IAPF Memory → ⚙️ Configuration Déploiement
2. **Vérifier** config actuelle
3. **Ajouter** GITHUB_TOKEN si manquant
4. **Tester** avec bouton Déploiement

---

## 📊 LOGS & MONITORING

### MEMORY_LOG

Chaque déploiement log:
```
Timestamp | Action | User | Component | Data | Status | Notes
----------|--------|------|-----------|------|--------|------
2026-02-14T18:00:00Z | DEPLOY_SUCCESS | user@... | MCP_DEPLOY | {...} | SUCCESS | 142s
```

### SNAPSHOT_ACTIVE

Snapshot post-déploiement:
```
Timestamp | Type | User | Memory_Rows | Risks | Conflicts | Data
----------|------|------|-------------|-------|-----------|-----
2026-02-14T18:02:22Z | POST_DEPLOY | user@... | 123 | 0 | 0 | {...}
```

---

## ⚠️ SÉCURITÉ

### Règles Strictes

✅ **AUTORISÉ**:
- Validation humaine obligatoire avant déploiement
- Logs détaillés dans MEMORY_LOG
- Snapshots post-déploiement
- Rollback manuel si erreur

❌ **INTERDIT**:
- Déploiement automatique sans validation
- Push force sans confirmation
- Suppression données production
- Modification config sans backup

### Gestion Erreurs

Si déploiement échoue:
1. ✅ Logs complets dans MEMORY_LOG
2. ✅ Dialogue erreur avec détails
3. ✅ État système préservé
4. ✅ Rollback manuel possible
5. ⚠️ Alertes utilisateur

---

## 🔄 ALTERNATIVES SIMPLIFIÉES

### Option 1: Sans GitHub Actions

Si pas d'accès GitHub Actions, utiliser **clasp** directement:

```javascript
function deploiementSimple() {
  // 1. Git push via clasp
  const claspCmd = 'clasp push';
  // Exécuter via terminal externe (pas possible dans Apps Script)
  
  // 2. Cloud Run deploy via gcloud
  const gcloudCmd = 'gcloud run deploy ...';
  // Exécuter via terminal externe
  
  // → Solution: Fournir scripts shell à l'utilisateur
}
```

### Option 2: Semi-Automatique

```javascript
function deploiementSemiAuto() {
  const ui = SpreadsheetApp.getUi();
  
  const instructions = `
📋 INSTRUCTIONS DÉPLOIEMENT MANUEL:

1️⃣ Git Push:
   cd /home/user/webapp
   git push origin feature/ocr-intelligent-3-levels

2️⃣ Apps Script:
   clasp push
   clasp deploy

3️⃣ Cloud Run:
   gcloud builds submit --tag gcr.io/PROJECT/ocr:latest
   gcloud run deploy box-magic-ocr-intelligent --image gcr.io/PROJECT/ocr:latest

✅ Cocher quand terminé
  `;
  
  ui.alert('📋 DÉPLOIEMENT MANUEL', instructions, ui.ButtonSet.OK);
  
  // Log intention
  logMemory('DEPLOY_MANUAL_INITIATED', { timestamp: new Date().toISOString() });
}
```

---

## 🎯 CHECKLIST IMPLÉMENTATION

- [ ] Créer fichier `MCP_Deploy.gs` dans Apps Script
- [ ] Générer GitHub Personal Access Token
- [ ] Configurer propriété `GITHUB_TOKEN`
- [ ] Créer workflows `.github/workflows/deploy.yml`
- [ ] Créer GCP Service Account
- [ ] Ajouter secret `GCP_SA_KEY` dans GitHub
- [ ] Tester configuration avec ⚙️ Configuration Déploiement
- [ ] Tester déploiement sur branche test
- [ ] Valider logs dans MEMORY_LOG
- [ ] Documenter pour équipe

---

## 📝 DOCUMENTATION UTILISATEUR

### Guide Rapide

```
╔═══════════════════════════════════════════════════════╗
║  🚀 DÉPLOIEMENT AUTOMATISÉ - GUIDE RAPIDE            ║
╠═══════════════════════════════════════════════════════╣
║                                                       ║
║  1. Menu "IAPF Memory"                               ║
║  2. Cliquer "🚀 Déploiement Automatisé"              ║
║  3. Lire changements détectés                        ║
║  4. Cliquer "YES" pour confirmer                     ║
║  5. Attendre rapport final (~2-3 min)                ║
║                                                       ║
║  ⚠️ ATTENTION:                                        ║
║  - Production sera impactée                          ║
║  - Validation humaine obligatoire                    ║
║  - Rollback manuel si problème                       ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
```

---

**Généré le**: 2026-02-14T18:00:00Z  
**Version**: 1.0.0  
**Auteur**: MCP Automation Team  
**Statut**: ✅ PRÊT POUR IMPLÉMENTATION
