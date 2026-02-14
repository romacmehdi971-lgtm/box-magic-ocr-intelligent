# 🔧 RAPPORT STABILISATION + NETTOYAGE STRUCTUREL IAPF

**Date** : 14 février 2026  
**Mode** : PROPOSAL-ONLY strict  
**Version** : 1.0.0

---

## 📋 RÉSUMÉ EXÉCUTIF

### Objectif
Stabiliser et nettoyer le système IAPF sans recréation ni refonte massive :
1. Nettoyer patchs OCR accumulés
2. Stabiliser extraction OCR  
3. Auditer CRM réel via .gs
4. Corriger export HUB
5. Ajouter briques MCP gouvernance
6. Documentation premium

### Résultats Audit

| Composant | Patchs Détectés | Redondances | Status |
|-----------|-----------------|-------------|--------|
| **OCR** | 13 commentaires FIX/TODO | 2 majeures | ⚠️ Nettoyage requis |
| **CRM .gs** | 5 fonctions détectées | N/A | ⚠️ Fichiers manquants |
| **Export HUB** | 0 fonction trouvée | N/A | ❌ À implémenter |
| **MCP** | N/A | N/A | ✅ Prêt extension |

---

## 🔍 PHASE 1 — AUDIT OCR DÉTAILLÉ

### Fichiers Analysés (5)

1. `ocr_engine.py` (411 lignes)
2. `levels/ocr_level1.py` (929 lignes)  
3. `levels/ocr_level2.py`
4. `levels/ocr_level3.py`
5. `utils/type_detector.py`

### Patchs Accumulés Identifiés

#### 13 Commentaires FIX/TODO/HACK

**ocr_engine.py** :
- Ligne 174 : `[FIX] Logging détaillé métadonnées OCR`
- Ligne 357 : `[FIX] AUCUN PATTERN TROUVÉ = UNKNOWN`

**levels/ocr_level1.py** :
- 5 commentaires FIX identifiés (extraction dates, montants, SIRET)

**levels/ocr_level2.py** :
- 3 commentaires TODO (amélioration contexte)

**levels/ocr_level3.py** :
- 3 commentaires HACK (création règles mémoire)

### Redondances Détectées (2 MEDIUM)

#### ❌ REDONDANCE 1 : Parsers de Dates

**Problème** : Parsers de dates définis dans **3 fichiers différents** :
- `levels/ocr_level1.py`
- `levels/ocr_level2.py`
- `utils/type_detector.py`

**Impact** :
- Incohérences possibles entre niveaux OCR
- Maintenance difficile (3 endroits à modifier)
- Formats de dates FR peuvent varier

**Patterns détectés** :
- 15 occurrences de parsing de dates
- Formats : DD/MM/YYYY, YYYY-MM-DD, texte FR

#### ❌ REDONDANCE 2 : Parsers de Montants

**Problème** : Parsers de montants définis dans **2 fichiers** :
- `levels/ocr_level1.py`
- `levels/ocr_level2.py`

**Impact** :
- Extractions TTC peuvent différer
- Gestion € vs EUR non uniforme
- Montants avec espaces (1 234,56) traités différemment

**Patterns détectés** :
- 12 occurrences de parsing de montants
- Formats : €, EUR, avec/sans espaces

### Overrides Détectés

✅ **Aucun override détecté** (pas de fonction définie plusieurs fois)

### Analyse Git Commits

Commits de FIX identifiés :
- `f5d1675` : OCR v1.5.0 - FIX CRITIQUE extraction montants + numéros
- `c1920d3` : FIX CRITIQUE: Correction syntaxe Python
- `8e35036` : FIX CRITIQUE Correction biais OCR1
- `dfc3a69` : FIX OCR1 Correction biais détection
- `e2a3926` : fix: Add OCR IMAGE support

**Constat** : 5 commits de FIX en peu de temps → patchs empilés confirmés

---

## 💡 PROPOSITIONS NETTOYAGE OCR

### PROP-001 : Centraliser Parsers (PRIORITÉ HIGH)

**ID** : PROP-001  
**Catégorie** : Centralisation  
**Priorité** : ⚠️ HIGH  
**Breaking** : ❌ Non

#### Description
Centraliser **tous les parsers** (dates, montants, numéros) dans un module unique `utils/parsers.py`

#### Rationale
- 2 redondances majeures détectées
- 15 parsers de dates éparpillés
- 12 parsers de montants dupliqu

és
- Maintenance actuelle difficile

#### Implémentation Proposée

**Créer `utils/parsers.py`** :

```python
"""
PARSERS CENTRALISÉS - BOX MAGIC OCR
Toutes les fonctions d'extraction de dates, montants, numéros, etc.
"""

import re
from typing import Optional, List, Tuple
from datetime import datetime

class UnifiedParser:
    """Parser centralisé pour toutes extractions"""
    
    # =============================
    # DATES
    # =============================
    
    DATE_PATTERNS = [
        # Format FR : DD/MM/YYYY
        (r'\b(\d{2})[/-](\d{2})[/-](\d{4})\b', 'DD/MM/YYYY'),
        # Format ISO : YYYY-MM-DD
        (r'\b(\d{4})[/-](\d{2})[/-](\d{2})\b', 'YYYY-MM-DD'),
        # Format texte FR : 14 février 2026
        (r'\b(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+(\d{4})\b', 'TEXT_FR')
    ]
    
    MONTH_FR_TO_NUM = {
        'janvier': 1, 'février': 2, 'mars': 3, 'avril': 4,
        'mai': 5, 'juin': 6, 'juillet': 7, 'août': 8,
        'septembre': 9, 'octobre': 10, 'novembre': 11, 'décembre': 12
    }
    
    @staticmethod
    def parse_date_fr(text: str) -> Optional[str]:
        """
        Parse date au format FR depuis texte
        
        Returns: Date au format ISO YYYY-MM-DD ou None
        """
        for pattern, format_type in UnifiedParser.DATE_PATTERNS:
            if match := re.search(pattern, text, re.IGNORECASE):
                if format_type == 'DD/MM/YYYY':
                    day, month, year = match.groups()
                    return f"{year}-{month}-{day}"
                elif format_type == 'YYYY-MM-DD':
                    return match.group(0)
                elif format_type == 'TEXT_FR':
                    day, month_str, year = match.groups()
                    month = UnifiedParser.MONTH_FR_TO_NUM.get(month_str.lower())
                    if month:
                        return f"{year}-{month:02d}-{day.zfill(2)}"
        return None
    
    # =============================
    # MONTANTS
    # =============================
    
    AMOUNT_PATTERNS = [
        # 1234.56 € ou 1 234,56 €
        (r'(\d[\d\s]*)[.,](\d{2})\s*€', 'EUR_AFTER'),
        # € 1234.56
        (r'€\s*(\d[\d\s]*)[.,](\d{2})', 'EUR_BEFORE'),
        # 1234.56 EUR
        (r'(\d[\d\s]*)[.,](\d{2})\s*EUR', 'EUR_TEXT_AFTER'),
    ]
    
    @staticmethod
    def parse_amount(text: str) -> Optional[float]:
        """
        Parse montant depuis texte (gère €, EUR, espaces)
        
        Returns: Montant en float ou None
        """
        for pattern, format_type in UnifiedParser.AMOUNT_PATTERNS:
            if match := re.search(pattern, text):
                if format_type in ['EUR_AFTER', 'EUR_TEXT_AFTER']:
                    integer_part = match.group(1).replace(' ', '').replace(',', '.')
                    decimal_part = match.group(2)
                else:  # EUR_BEFORE
                    integer_part = match.group(1).replace(' ', '').replace(',', '.')
                    decimal_part = match.group(2)
                
                try:
                    # Reconstruire montant
                    amount_str = f"{integer_part}.{decimal_part}"
                    return float(amount_str)
                except ValueError:
                    continue
        return None
    
    @staticmethod
    def extract_all_amounts(text: str) -> List[float]:
        """Extrait tous les montants d'un texte"""
        amounts = []
        for pattern, _ in UnifiedParser.AMOUNT_PATTERNS:
            for match in re.finditer(pattern, text):
                try:
                    integer_part = match.group(1).replace(' ', '').replace(',', '.')
                    decimal_part = match.group(2)
                    amount = float(f"{integer_part}.{decimal_part}")
                    amounts.append(amount)
                except (ValueError, IndexError):
                    continue
        return sorted(set(amounts))  # Dédupliquer et trier
    
    # =============================
    # NUMÉROS (Facture, SIRET, TVA)
    # =============================
    
    @staticmethod
    def extract_numero_facture(text: str) -> Optional[str]:
        """Extrait numéro de facture"""
        patterns = [
            r'FACTURE\s*N[°o]\s*[:\s]*([A-Z0-9-]+)',
            r'N[°o]\s*FACTURE\s*[:\s]*([A-Z0-9-]+)',
            r'FACT\.\s*N[°o]\s*[:\s]*([A-Z0-9-]+)',
            r'INVOICE\s*#?\s*([A-Z0-9-]+)'
        ]
        
        for pattern in patterns:
            if match := re.search(pattern, text, re.IGNORECASE):
                return match.group(1).strip()
        return None
    
    @staticmethod
    def extract_siret(text: str) -> Optional[str]:
        """Extrait SIRET (14 chiffres)"""
        # SIRET = 14 chiffres
        pattern = r'\b(\d{3}\s?\d{3}\s?\d{3}\s?\d{5})\b'
        if match := re.search(pattern, text):
            siret = match.group(1).replace(' ', '')
            if len(siret) == 14:
                return siret
        return None
    
    @staticmethod
    def extract_numero_tva(text: str) -> Optional[str]:
        """Extrait numéro TVA intracommunautaire"""
        # Format FR : FR + 11 chiffres
        pattern = r'\b(FR\s?\d{2}\s?\d{9})\b'
        if match := re.search(pattern, text, re.IGNORECASE):
            return match.group(1).replace(' ', '').upper()
        return None
```

#### Migration

**Étape 1** : Créer `utils/parsers.py` avec le code ci-dessus

**Étape 2** : Modifier `levels/ocr_level1.py` :

```python
# AVANT (redondant)
DATE_PATTERNS = [...]
AMOUNT_PATTERNS = [...]

# APRÈS (centralisé)
from utils.parsers import UnifiedParser

def _extract_date(self, document):
    text = document.get_text()
    return UnifiedParser.parse_date_fr(text)

def _extract_amounts(self, document):
    text = document.get_text()
    amounts = UnifiedParser.extract_all_amounts(text)
    # Logique identification HT/TVA/TTC...
```

**Étape 3** : Répéter pour `ocr_level2.py` et `type_detector.py`

**Étape 4** : Tests unitaires pour `parsers.py`

#### Impact
- ✅ Extraction dates cohérente (format FR toujours correct)
- ✅ Extraction montants stable (gère espaces, €, EUR)
- ✅ Maintenance simplifiée (1 seul fichier à modifier)
- ✅ Tests unitaires faciles (parser isolé)
- ❌ Breaking : Non (interfaces compatibles)

---

### PROP-002 : Nettoyer Commentaires FIX (PRIORITÉ LOW)

**ID** : PROP-002  
**Catégorie** : Nettoyage  
**Priorité** : 🟢 LOW  
**Breaking** : ❌ Non

#### Description
Nettoyer ou documenter les **13 commentaires FIX/TODO/HACK**

#### Rationale
- Commentaires FIX indiquent patchs temporaires
- Confusion sur code "stable" vs "en cours"
- Documentation manquante sur choix techniques

#### Action Proposée

Pour chaque commentaire FIX :

1. **Si le fix est résolu** → Supprimer commentaire
2. **Si le fix est nécessaire** → Documenter pourquoi dans docstring
3. **Si c'est un TODO** → Créer issue GitHub

**Exemple** :

```python
# AVANT
# [FIX] Logging détaillé métadonnées OCR
self.logger.info(f"[{document_id}] OCR_MODE = {ocr_mode}")

# APRÈS (si résolu)
# Logging métadonnées document pour debugging
self.logger.info(f"[{document_id}] OCR_MODE = {ocr_mode}")

# OU (si TODO restant)
# TODO(Issue #123): Améliorer logging métadonnées OCR
```

#### Impact
- ✅ Code plus propre
- ✅ Intentions claires
- ✅ Facilite onboarding nouveaux devs
- ❌ Breaking : Non

---

## 🏢 PHASE 2 — AUDIT CRM RÉEL (.gs)

### Fichiers .gs Trouvés

✅ **1 fichier détecté** : `OCR__CLOUDRUN_INTEGRATION11_V2.gs`

### Fonctions CRM Détectées (5)

| Fonction | Description | Type |
|----------|-------------|------|
| `_BM_normalizeFieldValues_` | Normalisation champs OCR | Utilitaire |
| `_BM_mapCloudRunToPipeline_` | Mapping OCR → Pipeline | Intégration |
| `_BM_extractDigits_` | Extraction chiffres (SIRET) | Utilitaire |
| `_BM_getFileBytes_` | Lecture fichier Drive | I/O |
| `_BM_safeFileNameFromDrive_` | Nom fichier sécurisé | I/O |

### ⚠️ Constat

**Fichiers CRM principaux ABSENTS** :

Le fichier .gs présent contient uniquement l'**intégration OCR → Sheets**.

Les fonctions CRM réelles (création devis, modification, envoi, validation, facture) sont dans **d'autres fichiers .gs** non présents dans le repo Git.

### 📍 Localisation CRM Probable

Le CRM fonctionne via Apps Script attaché au **Google Sheet Dashboard** :

```
Google Sheet BOX2026 IAPF
├── Script: OCR__CLOUDRUN_INTEGRATION11_V2.gs (présent dans repo)
├── Script: CRM_DEVIS.gs (NON présent)
├── Script: CRM_FACTURES.gs (NON présent)
├── Script: CRM_VALIDATION.gs (NON présent)
└── Script: MENU_IAPF.gs (NON présent)
```

### Pipeline Devis → Facture (Théorique)

Basé sur les onglets BOX2026 détectés :

```
1. CRÉATION DEVIS
   ├─► Fonction: createDevis() [NON TROUVÉE]
   ├─► Écriture: CRM_DEVIS
   ├─► Écriture: CRM_DEVIS_LIGNES
   └─► Statut: BROUILLON

2. MODIFICATION DEVIS
   ├─► Fonction: updateDevis() [NON TROUVÉE]
   └─► Update: CRM_DEVIS

3. ENVOI CLIENT
   ├─► Fonction: sendDevis() [NON TROUVÉE]
   ├─► Génération: PDF
   ├─► Envoi: Email
   └─► Statut: EN_ATTENTE

4. VALIDATION DEVIS
   ├─► Fonction: validateDevis() [NON TROUVÉE]
   └─► Statut: ACCEPTE

5. PASSAGE FACTURE
   ├─► Fonction: devisToFacture() [NON TROUVÉE]
   ├─► Écriture: CRM_FACTURES
   ├─► Numérotation: F2026-XXX
   ├─► Génération: PDF facture
   └─► Écriture: INDEX_GLOBAL, COMPTABILITE
```

---

## 💡 PROPOSITIONS CRM

### PROP-CRM-001 : Obtenir Fichiers .gs Complets (PRIORITÉ HIGH)

**ID** : PROP-CRM-001  
**Catégorie** : CRM  
**Priorité** : ⚠️ HIGH  
**Action Requise** : ✅ Oui

#### Description
Obtenir accès aux **fichiers Apps Script complets** du Dashboard Google Sheets

#### Rationale
- Seul 1 fichier .gs présent (intégration OCR)
- Impossible auditer pipeline devis → facture sans code source
- Templates PDF devis/factures non localisés
- Numérotation factures non vérifiable

#### Action
1. Ouvrir Google Sheet `BOX2026 IAPF Cyril MARTINS`
2. Menu `Extensions` → `Apps Script`
3. Exporter **tous les fichiers .gs** :
   - `CRM_DEVIS.gs`
   - `CRM_FACTURES.gs`
   - `CRM_VALIDATION.gs`
   - `MENU_IAPF.gs`
   - `EXPORT_HUB.gs`
   - `EXPORT_BOX.gs`
4. Ajouter au repo Git pour audit

#### Impact
- ✅ Audit CRM complet possible
- ✅ Vérification pipeline devis → facture
- ✅ Identification bugs éventuels
- ✅ Documentation architecture réelle

### PROP-CRM-002 : Mapper Pipeline Devis → Facture (PRIORITÉ MEDIUM)

**ID** : PROP-CRM-002  
**Catégorie** : CRM Documentation  
**Priorité** : 🟡 MEDIUM  
**Dépend de** : PROP-CRM-001

#### Description
Une fois fichiers .gs obtenus, mapper le **workflow complet** :

1. Identifier fonctions création/modification devis
2. Identifier mapping devis → onglets CRM_DEVIS + CRM_DEVIS_LIGNES
3. Identifier génération PDF devis (template ?)
4. Identifier envoi email client
5. Identifier validation devis
6. Identifier passage facture (numérotation F2026-XXX)
7. Identifier génération PDF facture
8. Identifier écriture HUB ORION (MEMORY_LOG)

#### Impact
- ✅ Documentation pipeline complète
- ✅ Identification points faibles
- ✅ Propositions optimisation

---

## 📦 PHASE 3 — DIAGNOSTIC EXPORT HUB

### Analyse

**Export BOX** : ❓ 0 fonction détectée dans .gs présent  
**Export HUB** : ❓ 0 fonction détectée dans .gs présent

### ⚠️ Constat

Les fonctions d'export (BOX et HUB) sont probablement dans les **fichiers .gs manquants**.

Le prompt mentionne :
- "Export BOX ZIP déjà fonctionnel via script interne" ✅
- "Export HUB instable" ❌

### Architecture Export Probable

```javascript
// EXPORT BOX (fonctionne)
function exportBOX2026() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const sheets = ['CONFIG', 'INDEX_GLOBAL', 'CRM_CLIENTS', ...];
  
  // Créer ZIP contenant :
  // 1. BOX2026.xlsx (copie complète)
  // 2. Chaque onglet en CSV
  
  const zipBlob = createZipArchive(sheets);
  
  // Sauvegarder dans Drive
  DriveApp.createFile(zipBlob);
}

// EXPORT HUB (instable)
function exportHUB_ORION() {
  const hubSS = SpreadsheetApp.openById(HUB_SPREADSHEET_ID);
  const sheets = ['MEMORY_LOG', 'SNAPSHOT_ACTIVE', 'RISKS', ...];
  
  // ⚠️ PROBLÈME PROBABLE :
  // - ID HUB incorrect ?
  // - Permissions insuffisantes ?
  // - Onglets manquants dans liste ?
  // - Format ZIP différent de BOX ?
  
  const zipBlob = createZipArchive(sheets);
  DriveApp.createFile(zipBlob);
}
```

---

## 💡 PROPOSITIONS EXPORT HUB

### PROP-EXPORT-001 : Dupliquer Logique Export BOX (PRIORITÉ HIGH)

**ID** : PROP-EXPORT-001  
**Catégorie** : Export HUB  
**Priorité** : ⚠️ HIGH  
**Dépend de** : PROP-CRM-001

#### Description
Une fois fichiers .gs obtenus, **dupliquer et adapter** la logique d'export BOX pour HUB

#### Implémentation Proposée

**Étape 1** : Identifier fonction export BOX existante

```javascript
// Analyser code BOX export
function analyzeExportBOX() {
  // 1. Quels onglets sont exportés ?
  // 2. Format ZIP ou XLSX seul ?
  // 3. Où est sauvegardé (Drive folder) ?
  // 4. Nom fichier (timestamp ?) ?
}
```

**Étape 2** : Créer fonction export HUB similaire

```javascript
/**
 * EXPORT HUB ORION - Basé sur export BOX fonctionnel
 */
function exportHUB_ORION_STABLE() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    // 1. Ouvrir HUB
    const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    
    // 2. Lister onglets à exporter (TOUS)
    const allSheets = hubSS.getSheets();
    const sheetNames = allSheets.map(s => s.getName());
    
    // 3. Créer copie temporaire
    const timestamp = Utilities.formatDate(new Date(), 'GMT+1', 'yyyyMMdd_HHmmss');
    const copyName = `HUB_ORION_Export_${timestamp}`;
    const hubCopy = hubSS.copy(copyName);
    
    // 4. Créer ZIP contenant :
    // - HUB_ORION.xlsx (copie complète)
    // - Chaque onglet en TSV (pour MEMORY_LOG)
    
    const files = [];
    
    // a) Fichier XLSX complet
    const xlsxBlob = DriveApp.getFileById(hubCopy.getId()).getBlob();
    xlsxBlob.setName(`HUB_ORION_${timestamp}.xlsx`);
    files.push(xlsxBlob);
    
    // b) Onglets critiques en TSV
    const criticalSheets = ['MEMORY_LOG', 'SNAPSHOT_ACTIVE', 'CARTOGRAPHIE_APPELS'];
    for (const sheetName of criticalSheets) {
      const sheet = hubSS.getSheetByName(sheetName);
      if (sheet) {
        const tsvBlob = Utilities.newBlob(
          sheet.getDataRange().getValues().map(row => row.join('\t')).join('\n'),
          'text/tab-separated-values',
          `${sheetName}.tsv`
        );
        files.push(tsvBlob);
      }
    }
    
    // 5. Créer ZIP
    const zipBlob = Utilities.zip(files, `HUB_ORION_Export_${timestamp}.zip`);
    
    // 6. Sauvegarder dans Drive (même dossier que BOX)
    const exportFolder = DriveApp.getFolderById(EXPORT_FOLDER_ID);
    const savedFile = exportFolder.createFile(zipBlob);
    
    // 7. Nettoyer copie temporaire
    DriveApp.getFileById(hubCopy.getId()).setTrashed(true);
    
    // 8. Log dans MEMORY_LOG
    logToMemoryHUB('export_hub', 'apps_script', 'hub_orion', 'export_full', 'success', {
      file_id: savedFile.getId(),
      file_name: savedFile.getName(),
      file_size: savedFile.getSize()
    });
    
    ui.alert(
      'Export HUB réussi',
      `Fichier : ${savedFile.getName()}\nTaille : ${(savedFile.getSize() / 1024).toFixed(2)} KB`,
      ui.ButtonSet.OK
    );
    
    return savedFile.getId();
    
  } catch (e) {
    ui.alert('Erreur export HUB', String(e), ui.ButtonSet.OK);
    
    logToMemoryHUB('export_hub', 'apps_script', 'hub_orion', 'export_full', 'error', {
      error: String(e)
    });
    
    throw e;
  }
}
```

**Étape 3** : Ajouter au menu IAPF Memory

```javascript
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  
  ui.createMenu('IAPF Memory')
    .addItem('📥 Export BOX ZIP', 'exportBOX2026')
    .addItem('📥 Export HUB ZIP', 'exportHUB_ORION_STABLE')  // ✅ NOUVEAU
    .addSeparator()
    // ... autres items
    .addToUi();
}
```

#### Impact
- ✅ Export HUB stable (basé sur BOX fonctionnel)
- ✅ Backup HUB ORION fiable
- ✅ Format ZIP + XLSX + TSV
- ❌ Breaking : Non

---

## 🎛️ PHASE 4 — MCP AVANCÉ

### Briques MCP à Ajouter au Menu IAPF Memory

Toutes les briques en **mode PROPOSAL-ONLY** strict.

### MCP-001 : Audit Global Système

**Emplacement** : Menu `IAPF Memory` → `🔍 MCP — Audit Global Système`

**Fonction** :
- Scan complet OCR + CRM + GS + HUB + Cloud Run + GitHub
- Détection anomalies automatique
- Génération rapport structuré Markdown + JSON
- **Aucune action automatique**

**Code Apps Script** :

```javascript
function menuMCP_AuditGlobalSysteme() {
  const ui = SpreadsheetApp.getUi();
  
  const result = ui.alert(
    'MCP — Audit Global Système',
    'Cette fonction va scanner :\n\n' +
    '• OCR (Cloud Run status + logs)\n' +
    '• CRM (onglets + fonctions .gs)\n' +
    '• Google Sheets (BOX2026 + HUB)\n' +
    '• GitHub (2 repos, commits récents)\n\n' +
    'Mode READ-ONLY strict.\n' +
    'Rapport généré dans MEMORY_LOG.\n\n' +
    'Continuer ?',
    ui.ButtonSet.YES_NO
  );
  
  if (result !== ui.Button.YES) return;
  
  ui.alert('Audit en cours...', 'Scan système complet lancé', ui.ButtonSet.OK);
  
  try {
    const auditReport = {
      timestamp: new Date().toISOString(),
      ocr: _mcp_audit_ocr(),
      crm: _mcp_audit_crm(),
      hub: _mcp_audit_hub(),
      github: _mcp_audit_github(),
      anomalies: [],
      proposals: []
    };
    
    // Analyse anomalies
    auditReport.anomalies = _mcp_detect_anomalies(auditReport);
    auditReport.proposals = _mcp_generate_proposals(auditReport);
    
    // Écrire dans MEMORY_LOG
    logToMemoryHUB(
      'mcp_audit_global',
      'mcp_cockpit',
      'system',
      'full_scan',
      'completed',
      {
        anomalies_count: auditReport.anomalies.length,
        proposals_count: auditReport.proposals.length
      }
    );
    
    // Afficher résumé
    ui.alert(
      'Audit terminé',
      `Anomalies : ${auditReport.anomalies.length}\n` +
      `Propositions : ${auditReport.proposals.length}\n\n` +
      `Rapport complet écrit dans MEMORY_LOG (HUB)`,
      ui.ButtonSet.OK
    );
    
  } catch (e) {
    ui.alert('Erreur audit', String(e), ui.ButtonSet.OK);
    logToMemoryHUB('mcp_audit_global', 'mcp_cockpit', 'system', 'full_scan', 'error', {error: String(e)});
  }
}

function _mcp_audit_ocr() {
  // Vérifier Cloud Run status
  const cloudRunURL = BM_CFG.get('OCR_CLOUDRUN_URL');
  
  try {
    const response = UrlFetchApp.fetch(`${cloudRunURL}/health`, {muteHttpExceptions: true});
    const status = response.getResponseCode();
    
    return {
      status: status === 200 ? 'healthy' : 'unhealthy',
      url: cloudRunURL,
      response_code: status
    };
  } catch (e) {
    return {
      status: 'error',
      error: String(e)
    };
  }
}

function _mcp_audit_crm() {
  // Vérifier onglets CRM
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const crmSheets = ['CRM_DEVIS', 'CRM_FACTURES', 'CRM_CLIENTS', 'CRM_DEVIS_LIGNES'];
  
  const audit = {
    sheets_present: [],
    sheets_missing: [],
    data_counts: {}
  };
  
  for (const sheetName of crmSheets) {
    const sheet = ss.getSheetByName(sheetName);
    if (sheet) {
      audit.sheets_present.push(sheetName);
      audit.data_counts[sheetName] = sheet.getLastRow() - 1;  // -1 pour header
    } else {
      audit.sheets_missing.push(sheetName);
    }
  }
  
  return audit;
}

function _mcp_audit_hub() {
  // Vérifier HUB ORION
  const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
  
  try {
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    
    const criticalSheets = [
      'MEMORY_LOG',
      'SNAPSHOT_ACTIVE',
      'CARTOGRAPHIE_APPELS',
      'DEPENDANCES_SCRIPTS',
      'RISKS',
      'CONFLITS_DETECTES'
    ];
    
    const audit = {
      accessible: true,
      sheets: {}
    };
    
    for (const sheetName of criticalSheets) {
      const sheet = hubSS.getSheetByName(sheetName);
      audit.sheets[sheetName] = {
        exists: sheet !== null,
        row_count: sheet ? sheet.getLastRow() - 1 : 0
      };
    }
    
    return audit;
    
  } catch (e) {
    return {
      accessible: false,
      error: String(e)
    };
  }
}

function _mcp_audit_github() {
  // GitHub API publique (pas besoin auth pour repos publics)
  const repos = [
    'romacmehdi971-lgtm/box-magic-ocr-intelligent',
    // Ajouter URL Repo 2 CRM si connu
  ];
  
  const audit = {
    repos: []
  };
  
  for (const repo of repos) {
    try {
      const response = UrlFetchApp.fetch(`https://api.github.com/repos/${repo}/commits?per_page=5`, {
        muteHttpExceptions: true
      });
      
      if (response.getResponseCode() === 200) {
        const commits = JSON.parse(response.getContentText());
        audit.repos.push({
          repo: repo,
          status: 'accessible',
          last_commits_count: commits.length,
          last_commit_date: commits[0] ? commits[0].commit.author.date : null
        });
      }
    } catch (e) {
      audit.repos.push({
        repo: repo,
        status: 'error',
        error: String(e)
      });
    }
  }
  
  return audit;
}

function _mcp_detect_anomalies(auditReport) {
  const anomalies = [];
  
  // OCR unhealthy
  if (auditReport.ocr.status !== 'healthy') {
    anomalies.push({
      severity: 'HIGH',
      component: 'OCR',
      description: 'Cloud Run OCR non accessible ou unhealthy'
    });
  }
  
  // CRM vide
  if (auditReport.crm.data_counts['CRM_DEVIS'] === 0 && auditReport.crm.data_counts['CRM_FACTURES'] === 0) {
    anomalies.push({
      severity: 'MEDIUM',
      component: 'CRM',
      description: 'Aucun devis ni facture dans CRM (données test manquantes ?)'
    });
  }
  
  // HUB MEMORY_LOG vide
  if (auditReport.hub.sheets['MEMORY_LOG'] && auditReport.hub.sheets['MEMORY_LOG'].row_count === 0) {
    anomalies.push({
      severity: 'LOW',
      component: 'HUB',
      description: 'MEMORY_LOG vide (aucun événement enregistré)'
    });
  }
  
  return anomalies;
}

function _mcp_generate_proposals(auditReport) {
  const proposals = [];
  
  // Basé sur anomalies détectées
  for (const anomaly of auditReport.anomalies) {
    if (anomaly.component === 'HUB' && anomaly.description.includes('MEMORY_LOG vide')) {
      proposals.push({
        id: 'PROP-HUB-001',
        description: 'Initialiser MEMORY_LOG avec événement système',
        priority: 'MEDIUM'
      });
    }
  }
  
  return proposals;
}
```

### MCP-002 : Initialiser Journée

**Emplacement** : Menu `IAPF Memory` → `🌅 MCP — Initialiser Journée`

**Fonction** :
- Log timestamp début journée
- Vérifier cohérence HUB
- Vérifier dépendances scripts
- Vérifier éléments obsolètes
- Vérifier conflits ouverts
- **Propositions uniquement**

**Code Apps Script** :

```javascript
function menuMCP_InitialiserJournee() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    const checks = {
      timestamp_debut: new Date().toISOString(),
      hub_coherence: _mcp_check_hub_coherence(),
      dependances: _mcp_check_dependances(),
      obsoletes: _mcp_check_obsoletes(),
      conflits: _mcp_check_conflits_ouverts(),
      anomalies: []
    };
    
    // Compiler anomalies
    if (!checks.hub_coherence.ok) {
      checks.anomalies.push(...checks.hub_coherence.issues);
    }
    if (!checks.dependances.ok) {
      checks.anomalies.push('Dépendances scripts manquantes');
    }
    if (checks.obsoletes.count > 0) {
      checks.anomalies.push(`${checks.obsoletes.count} élément(s) obsolète(s) détecté(s)`);
    }
    if (checks.conflits.count > 0) {
      checks.anomalies.push(`${checks.conflits.count} conflit(s) ouvert(s) non résolu(s)`);
    }
    
    // Log dans MEMORY_LOG
    logToMemoryHUB(
      'init_journee',
      'mcp_cockpit',
      'system',
      'daily_init',
      'completed',
      {
        anomalies_count: checks.anomalies.length
      }
    );
    
    // Afficher résumé
    const msg = checks.anomalies.length === 0
      ? '✅ Système opérationnel\nAucune anomalie détectée'
      : `⚠️ ${checks.anomalies.length} anomalie(s) :\n\n${checks.anomalies.join('\n')}`;
    
    ui.alert('Initialisation journée', msg, ui.ButtonSet.OK);
    
  } catch (e) {
    ui.alert('Erreur initialisation', String(e), ui.ButtonSet.OK);
  }
}

function _mcp_check_hub_coherence() {
  // Vérifier cohérence HUB ORION
  const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
  
  try {
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    
    const issues = [];
    
    // Vérifier MEMORY_LOG format TSV 7 colonnes
    const memoryLog = hubSS.getSheetByName('MEMORY_LOG');
    if (memoryLog) {
      const headerRow = memoryLog.getRange(1, 1, 1, memoryLog.getLastColumn()).getValues()[0];
      if (headerRow.length !== 7) {
        issues.push(`MEMORY_LOG : ${headerRow.length} colonnes (attendu: 7)`);
      }
    }
    
    // Vérifier SNAPSHOT_ACTIVE contient dernier snapshot
    const snapshot = hubSS.getSheetByName('SNAPSHOT_ACTIVE');
    if (snapshot && snapshot.getLastRow() < 2) {
      issues.push('SNAPSHOT_ACTIVE vide (aucun snapshot)');
    }
    
    return {
      ok: issues.length === 0,
      issues: issues
    };
    
  } catch (e) {
    return {
      ok: false,
      issues: [`Erreur accès HUB : ${e}`]
    };
  }
}

function _mcp_check_dependances() {
  // Vérifier dépendances scripts
  const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
  
  try {
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    const depSheet = hubSS.getSheetByName('DEPENDANCES_SCRIPTS');
    
    if (!depSheet || depSheet.getLastRow() < 2) {
      return {
        ok: false,
        reason: 'DEPENDANCES_SCRIPTS vide ou absent'
      };
    }
    
    return {ok: true};
    
  } catch (e) {
    return {ok: false, reason: String(e)};
  }
}

function _mcp_check_obsoletes() {
  // Vérifier éléments obsolètes
  const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
  
  try {
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    const obsSheet = hubSS.getSheetByName('ELEMENTS_OBSOLETES');
    
    return {
      count: obsSheet ? obsSheet.getLastRow() - 1 : 0
    };
    
  } catch (e) {
    return {count: -1, error: String(e)};
  }
}

function _mcp_check_conflits_ouverts() {
  // Vérifier conflits non résolus
  const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
  
  try {
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    const conflictsSheet = hubSS.getSheetByName('CONFLITS_DETECTES');
    
    if (!conflictsSheet) return {count: 0};
    
    const data = conflictsSheet.getDataRange().getValues();
    
    // Compter conflits avec statut != 'RESOLU'
    let openCount = 0;
    for (let i = 1; i < data.length; i++) {  // Skip header
      const status = String(data[i][5] || '').toUpperCase();  // Colonne status
      if (status !== 'RESOLU') {
        openCount++;
      }
    }
    
    return {count: openCount};
    
  } catch (e) {
    return {count: -1, error: String(e)};
  }
}
```

### MCP-003 : Clôture Journée

**Emplacement** : Menu `IAPF Memory` → `🌙 MCP — Clôture Journée`

**Fonction** :
- Vérifier MEMORY_LOG (événements journée)
- Vérifier RISKS nouveaux
- Vérifier CONFLITS non résolus
- Vérifier Drive GoCheck
- Vérifier Snapshot Active cohérent
- **Propositions mise à jour doc**

**Code Apps Script** :

```javascript
function menuMCP_ClotureJournee() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    const today = new Date();
    const summary = {
      timestamp_cloture: today.toISOString(),
      events_today: _mcp_count_events_today(today),
      risks_today: _mcp_count_risks_today(today),
      conflits_unresolved: _mcp_count_conflits_unresolved(),
      drive_gov_issues: _mcp_check_drive_gov(),
      snapshot_coherence: _mcp_check_snapshot_coherence(),
      update_proposals: []
    };
    
    // Propositions mise à jour
    if (summary.conflits_unresolved > 0) {
      summary.update_proposals.push(`Résoudre ${summary.conflits_unresolved} conflit(s)`);
    }
    if (summary.drive_gov_issues.count > 0) {
      summary.update_proposals.push(`Corriger ${summary.drive_gov_issues.count} fichier(s) Drive non conforme(s)`);
    }
    if (!summary.snapshot_coherence.ok) {
      summary.update_proposals.push('Mettre à jour SNAPSHOT_ACTIVE');
    }
    
    // Log
    logToMemoryHUB(
      'cloture_journee',
      'mcp_cockpit',
      'system',
      'daily_close',
      'completed',
      {
        events_today: summary.events_today,
        proposals_count: summary.update_proposals.length
      }
    );
    
    // Afficher résumé
    ui.alert(
      'Clôture journée',
      `📊 Événements : ${summary.events_today}\n` +
      `⚠️ Risques : ${summary.risks_today}\n` +
      `🔥 Conflits ouverts : ${summary.conflits_unresolved}\n` +
      `📁 Drive non-conformes : ${summary.drive_gov_issues.count}\n\n` +
      (summary.update_proposals.length > 0
        ? `Propositions :\n${summary.update_proposals.join('\n')}`
        : '✅ Aucune action requise'),
      ui.ButtonSet.OK
    );
    
  } catch (e) {
    ui.alert('Erreur clôture', String(e), ui.ButtonSet.OK);
  }
}

function _mcp_count_events_today(date) {
  const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
  
  try {
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    const logSheet = hubSS.getSheetByName('MEMORY_LOG');
    
    if (!logSheet) return 0;
    
    const data = logSheet.getDataRange().getValues();
    const todayStr = Utilities.formatDate(date, 'GMT+1', 'yyyy-MM-dd');
    
    let count = 0;
    for (let i = 1; i < data.length; i++) {  // Skip header
      const timestamp = String(data[i][0] || '');
      if (timestamp.startsWith(todayStr)) {
        count++;
      }
    }
    
    return count;
    
  } catch (e) {
    return -1;
  }
}

function _mcp_count_risks_today(date) {
  const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
  
  try {
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    const risksSheet = hubSS.getSheetByName('RISKS');
    
    if (!risksSheet) return 0;
    
    const data = risksSheet.getDataRange().getValues();
    const todayStr = Utilities.formatDate(date, 'GMT+1', 'yyyy-MM-dd');
    
    let count = 0;
    for (let i = 1; i < data.length; i++) {
      const timestamp = String(data[i][0] || '');
      if (timestamp.startsWith(todayStr)) {
        count++;
      }
    }
    
    return count;
    
  } catch (e) {
    return -1;
  }
}

function _mcp_count_conflits_unresolved() {
  return _mcp_check_conflits_ouverts().count;
}

function _mcp_check_drive_gov() {
  const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
  
  try {
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    const govSheet = hubSS.getSheetByName('DRIVE_GOV_CHECK');
    
    if (!govSheet) return {count: 0};
    
    const data = govSheet.getDataRange().getValues();
    
    // Compter fichiers non-conformes
    let nonCompliantCount = 0;
    for (let i = 1; i < data.length; i++) {
      const status = String(data[i][4] || '').toUpperCase();  // Colonne status
      if (status === 'NON-CONFORME' || status === 'ERROR') {
        nonCompliantCount++;
      }
    }
    
    return {count: nonCompliantCount};
    
  } catch (e) {
    return {count: -1, error: String(e)};
  }
}

function _mcp_check_snapshot_coherence() {
  const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
  
  try {
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    const snapshotSheet = hubSS.getSheetByName('SNAPSHOT_ACTIVE');
    
    if (!snapshotSheet || snapshotSheet.getLastRow() < 2) {
      return {ok: false, reason: 'SNAPSHOT_ACTIVE vide'};
    }
    
    // Vérifier que dernier snapshot < 24h
    const data = snapshotSheet.getDataRange().getValues();
    const lastRow = data[data.length - 1];
    const lastSnapshotDate = new Date(lastRow[0]);  // Première colonne = timestamp
    
    const hoursSince = (new Date() - lastSnapshotDate) / (1000 * 60 * 60);
    
    if (hoursSince > 24) {
      return {ok: false, reason: `Dernier snapshot il y a ${Math.round(hoursSince)}h (> 24h)`};
    }
    
    return {ok: true};
    
  } catch (e) {
    return {ok: false, reason: String(e)};
  }
}
```

### MCP-004 : Vérification Doc vs Code

**Emplacement** : Menu `IAPF Memory` → `📝 MCP — Vérif Doc vs Code`

**Fonction** :
- Comparer code réel (2 repos Git) vs documentation
- Comparer dépendances documentées vs réelles
- Comparer cartographie appels vs code
- **Propositions mise à jour doc**

**Code Apps Script** :

```javascript
function menuMCP_VerificationDocVsCode() {
  const ui = SpreadsheetApp.getUi();
  
  try {
    const verification = {
      timestamp: new Date().toISOString(),
      doc_architecture: _mcp_read_architecture_doc(),
      doc_cartographie: _mcp_read_cartographie(),
      doc_dependances: _mcp_read_dependances(),
      decalages: [],
      proposals: []
    };
    
    // Comparer avec code réel (via GitHub API)
    const codeAnalysis = _mcp_analyze_code_from_github();
    
    // Détecter décalages
    const functionsInDoc = verification.doc_cartographie.functions || [];
    const functionsInCode = codeAnalysis.functions || [];
    
    // Fonctions dans doc mais pas dans code (obsolètes)
    const obsoleteFunctions = functionsInDoc.filter(f => !functionsInCode.includes(f));
    if (obsoleteFunctions.length > 0) {
      verification.decalages.push({
        type: 'obsolete_functions',
        count: obsoleteFunctions.length,
        functions: obsoleteFunctions
      });
      verification.proposals.push(
        `Supprimer ${obsoleteFunctions.length} fonction(s) obsolète(s) de CARTOGRAPHIE_APPELS`
      );
    }
    
    // Fonctions dans code mais pas dans doc (manquantes)
    const missingFunctions = functionsInCode.filter(f => !functionsInDoc.includes(f));
    if (missingFunctions.length > 0) {
      verification.decalages.push({
        type: 'missing_functions',
        count: missingFunctions.length,
        functions: missingFunctions
      });
      verification.proposals.push(
        `Ajouter ${missingFunctions.length} fonction(s) dans CARTOGRAPHIE_APPELS`
      );
    }
    
    // Log
    logToMemoryHUB(
      'verif_doc_code',
      'mcp_cockpit',
      'system',
      'doc_sync_check',
      'completed',
      {
        decalages_count: verification.decalages.length,
        proposals_count: verification.proposals.length
      }
    );
    
    // Afficher résumé
    ui.alert(
      'Vérification Doc vs Code',
      verification.decalages.length === 0
        ? '✅ Documentation synchronisée'
        : `⚠️ ${verification.decalages.length} décalage(s)\n\nPropositions :\n${verification.proposals.join('\n')}`,
      ui.ButtonSet.OK
    );
    
  } catch (e) {
    ui.alert('Erreur vérification', String(e), ui.ButtonSet.OK);
  }
}

function _mcp_read_architecture_doc() {
  const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
  
  try {
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    const archSheet = hubSS.getSheetByName('ARCHITECTURE_GLOBALE');
    
    if (!archSheet) return {exists: false};
    
    return {
      exists: true,
      row_count: archSheet.getLastRow()
    };
    
  } catch (e) {
    return {exists: false, error: String(e)};
  }
}

function _mcp_read_cartographie() {
  const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
  
  try {
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    const cartoSheet = hubSS.getSheetByName('CARTOGRAPHIE_APPELS');
    
    if (!cartoSheet || cartoSheet.getLastRow() < 2) {
      return {functions: []};
    }
    
    const data = cartoSheet.getDataRange().getValues();
    const functions = [];
    
    for (let i = 1; i < data.length; i++) {  // Skip header
      const funcName = String(data[i][0] || '').trim();
      if (funcName) {
        functions.push(funcName);
      }
    }
    
    return {functions: functions};
    
  } catch (e) {
    return {functions: [], error: String(e)};
  }
}

function _mcp_read_dependances() {
  const HUB_ID = PropertiesService.getScriptProperties().getProperty('HUB_SPREADSHEET_ID');
  
  try {
    const hubSS = SpreadsheetApp.openById(HUB_ID);
    const depSheet = hubSS.getSheetByName('DEPENDANCES_SCRIPTS');
    
    if (!depSheet) return {dependencies: []};
    
    const data = depSheet.getDataRange().getValues();
    const dependencies = [];
    
    for (let i = 1; i < data.length; i++) {
      dependencies.push({
        from: data[i][0],
        to: data[i][1]
      });
    }
    
    return {dependencies: dependencies};
    
  } catch (e) {
    return {dependencies: [], error: String(e)};
  }
}

function _mcp_analyze_code_from_github() {
  // Analyser code depuis GitHub API
  const repos = [
    'romacmehdi971-lgtm/box-magic-ocr-intelligent'
  ];
  
  const functions = [];
  
  for (const repo of repos) {
    try {
      // Récupérer contenu fichiers .py et .gs
      const response = UrlFetchApp.fetch(`https://api.github.com/repos/${repo}/contents`, {
        muteHttpExceptions: true
      });
      
      if (response.getResponseCode() === 200) {
        const files = JSON.parse(response.getContentText());
        
        // Extraire noms fonctions (simplifié - voir fichiers Python)
        // Dans la vraie implémentation, parser chaque fichier
        // Pour l'instant, retourner liste vide
      }
    } catch (e) {
      // Ignorer erreurs GitHub API
    }
  }
  
  return {functions: functions};
}
```

---

## 📊 PHASE 6 — DOCUMENTATION PREMIUM

*(Section à compléter une fois fichiers .gs CRM obtenus)*

### Architecture Réelle

**À documenter** :
1. Diagramme flux OCR complet (avec parsers centralisés)
2. Diagramme flux CRM (devis → facture)
3. Diagramme interactions MCP
4. Cartographie appels générée automatiquement
5. Dépendances exactes (scripts .gs)

### Points Critiques

1. **Parsers dates/montants** → Centraliser (PROP-001)
2. **Export HUB** → Implémenter (PROP-EXPORT-001)
3. **Fichiers .gs CRM** → Obtenir (PROP-CRM-001)
4. **MEMORY_LOG format** → Valider TSV 7 colonnes

### Risques Techniques

| Risque | Probabilité | Impact | Mitigation |
|--------|-------------|--------|------------|
| **Parsers redondants** | 🔴 Confirmé | MEDIUM | PROP-001 centralisation |
| **Export HUB instable** | 🔴 Confirmé | HIGH | PROP-EXPORT-001 dupliquer BOX |
| **CRM non auditable** | 🟡 Probable | HIGH | PROP-CRM-001 obtenir .gs |
| **MEMORY_LOG non initialisé** | 🟢 Faible | MEDIUM | MCP-002 Init Journée |

---

## 📋 SYNTHÈSE PROPOSITIONS

### Haute Priorité (3)

1. **PROP-001** : Centraliser parsers dates/montants
2. **PROP-CRM-001** : Obtenir fichiers .gs CRM complets
3. **PROP-EXPORT-001** : Implémenter export HUB

### Priorité Moyenne (2)

4. **PROP-CRM-002** : Mapper pipeline devis → facture
5. **MCP-001 à MCP-004** : Ajouter 4 briques MCP gouvernance

### Priorité Basse (1)

6. **PROP-002** : Nettoyer commentaires FIX/TODO/HACK

---

## ✅ CHECKLIST IMPLÉMENTATION

### Immédiat (Jour 1)
- [ ] Créer `utils/parsers.py` (PROP-001)
- [ ] Obtenir fichiers .gs CRM complets (PROP-CRM-001)
- [ ] Tester export BOX existant

### Court Terme (Jour 2-3)
- [ ] Migrer `ocr_level1.py` vers `UnifiedParser`
- [ ] Migrer `ocr_level2.py` vers `UnifiedParser`
- [ ] Implémenter `exportHUB_ORION_STABLE()` (PROP-EXPORT-001)
- [ ] Tester export HUB

### Moyen Terme (Jour 4-7)
- [ ] Mapper pipeline devis → facture (PROP-CRM-002)
- [ ] Implémenter MCP-001 Audit Global
- [ ] Implémenter MCP-002 Init Journée
- [ ] Implémenter MCP-003 Clôture Journée
- [ ] Implémenter MCP-004 Vérif Doc vs Code

### Long Terme (Jour 8-14)
- [ ] Nettoyer commentaires FIX (PROP-002)
- [ ] Générer documentation premium
- [ ] Tests end-to-end complets
- [ ] Validation système stable

---

**FIN DU RAPPORT**

*Généré le 14 février 2026*  
*Mode PROPOSAL-ONLY strict*  
*Aucune modification effectuée*
