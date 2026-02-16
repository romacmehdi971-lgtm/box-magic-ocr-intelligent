# 🎯 PLAN D'EXECUTION COMPLET — ALIGNEMENT IAPF

**Date** : 2026-02-14 22:30  
**Mode** : PRODUCTION ALIGNMENT - GOUVERNANCE STRICTE  
**Branch** : main (commit 2a578fd)

---

## 📋 GOUVERNANCE LISEUSE (IAPF MEMORY HUB)

### ✅ RÈGLES FONDATRICES VALIDÉES

1. **VIDE > BRUIT** (règle fondatrice non négociable)
2. **OCR = MIROIR DU DOCUMENT** (aucune déduction, aucune invention)
3. **POST_VALIDATION_ONLY** (scan non destructif, validation humaine obligatoire)
4. **IA_MEMORY = apprentissage post-validation uniquement**
5. **Séparation stricte SCAN / POST-VALIDATION**
6. **Nom final visible avant validation**

### ✅ ARCHITECTURE OCR VALIDÉE (CR1/CR2/CR3)

**CR1 (Cloud Run OCR)** :
- Google Cloud Vision API (DOCUMENT_TEXT_DETECTION) UNIQUEMENT
- Tesseract INTERDIT en production
- Extraction factuelle uniquement
- Aucun enrichissement
- READ-ONLY strict

**CR2 (Apps Script - Structuration)** :
- Typage document
- Mapping champs
- Non destructif
- Normalisation préalable (éliminer faux PDF)

**CR3 (Apps Script - IA Memory)** :
- Apprentissage fournisseur/client (IA_SUPPLIERS)
- Règles réutilisables
- Auto-validation progressive (seuil confiance 99-100%)
- POST_VALIDATION_ONLY obligatoire

### ✅ CONSTATS BLOQUANTS MÉMORISÉS

1. **Regression Apps Script** : fallback Vision incorrect + logger _BM_log_ manquant
2. **Extraction montants/numéro KO** : texte OCR présent mais non exploité
3. **Pollution client_*** : champs client_* non vidés après extraction
4. **Date_Validation écrite trop tôt** : blocage rejouabilité R05

---

## 📂 STRUCTURE ACTUELLE BOX2026 (34 fichiers .gs)

```
00_Config_2026.gs               # Config centrale
01_SCAN_CANON.gs               # Routing scan
02_SCAN_WORKER.gs              # Orchestrateur (1794 lignes) ⚠️ TROP GROS
99_BACKUP_ALL_BOX2026.gs       # Backup
99_DIAGNOSTICS.gs              # Diagnostics
99_DIAG_JSONL.gs              # Logs JSONL
99_EXPORT_CODE_ZIP_AUDIT.gs   # Export audit
99_EXPORT_PROJECT_ZIP.gs      # Export projet
API_Classement.gs             # API classement
BM_COMPTABILITE.gs            # Comptabilité
BM_DRIVE.gs                   # Drive ops
BM_PIPELINE_NORMALIZE.gs      # Normalisation
CRM.gs                        # CRM principal
CRM_API_JSONP_ROUTER.gs       # API CRM
CRM_API_WEBAPP_COMPLET.gs     # WebApp CRM
CRM_COMPLETE.gs               # CRM complet
CRM_DEVIS_READ_WITH_JOIN.gs   # Devis read
CRM_DEVIS_VALIDATE_AND_RENDER.gs # Devis validation
CRM_DEVIS_VALIDATE_PDF.gs     # Devis PDF
Config_Manager.gs             # Config manager
Dashboard_LAUNCHER.gs         # Dashboard
GMAIL_COLLECT_TMP.gs          # Gmail collect
HTML_Render_AssetsInline.gs   # HTML render
OCR_PIPELINE_MAPPING_OPTION_B.gs # Pipeline mapping
OCR__CLOUDRUN_INTEGRATION11.gs # Cloud Run OCR ⚠️ PROTÉGÉ
P17_CLIENT_ID__INVENTORY.gs   # Inventory clients
R05_POST_OCR.gs               # Post OCR
R05_POST_VALIDATION_HANDLER.gs # Post validation
R06_IA_MEMORY_SUPPLIERS_APPLY.gs # IA Memory ⚠️ PROTÉGÉ
RENDER_Slides_PDF.gs          # Render slides
RenommageIntelligent.gs       # Renommage
Security.gs                   # Sécurité
Utils.gs                      # Utils
VALIDATION_GATE.gs            # Gate validation ⚠️ PROTÉGÉ
```

---

## 🎯 ARCHITECTURE CIBLE (conforme IAPF)

### 📦 STRUCTURE REFACTORISÉE BOX2026

```
# === CONFIGURATION ===
00_CONFIG_2026.gs              # Config centrale (INCHANGÉ)

# === ROUTING ===
01_SCAN_ROUTING_GUARD.gs       # NEW: Guard + routing intelligent

# === ORCHESTRATION ===
02_SCAN_ORCHESTRATOR.gs        # NEW: Orchestrateur léger (remplace 02_SCAN_WORKER.gs)

# === OCR ENGINES ===
03_OCR_ENGINE_FAST.gs          # NEW: OCR Level 1 (texte natif)
03_OCR_ENGINE_CONTEXTUAL.gs    # NEW: OCR Level 2 (Cloud Run standard)
03_OCR_ENGINE_MEMORY.gs        # NEW: OCR Level 3 (Cloud Run + IA Memory)

# === PARSERS ===
04_PARSERS_CORE.gs             # NEW: Parsers centralisés (date/amount/invoice)
04_PARSERS_SUPPLIERS.gs        # NEW: Parsers fournisseurs (IA_SUPPLIERS)

# === PIPELINE ===
05_PIPELINE_MAPPER.gs          # NEW: Mapping OCR → fields
05_PIPELINE_VALIDATOR.gs       # NEW: Validation avant injection

# === INJECTION ===
06_OCR_INJECTION.gs            # NEW: Injection payload validé

# === POST-VALIDATION ===
07_POST_VALIDATION.gs          # NEW: Validation finale + écritures

# === IA MEMORY (PROTÉGÉ) ===
R06_IA_MEMORY_SUPPLIERS_APPLY.gs # INCHANGÉ - PROTÉGÉ

# === VALIDATION GATE (PROTÉGÉ) ===
VALIDATION_GATE.gs             # INCHANGÉ - PROTÉGÉ

# === CLOUD RUN (PROTÉGÉ) ===
OCR__CLOUDRUN_INTEGRATION11.gs # INCHANGÉ - PROTÉGÉ

# === LEGACY (à garder pour compatibilité) ===
01_SCAN_CANON.gs               # INCHANGÉ (legacy)
BM_PIPELINE_NORMALIZE.gs       # INCHANGÉ (normalisation)
API_Classement.gs              # INCHANGÉ (API)
BM_COMPTABILITE.gs             # INCHANGÉ (compta)
BM_DRIVE.gs                    # INCHANGÉ (Drive)
Security.gs                    # INCHANGÉ (sécurité)
Utils.gs                       # INCHANGÉ (utils)
Config_Manager.gs              # INCHANGÉ (config)

# === CRM (PROTÉGÉ) ===
CRM.gs                         # INCHANGÉ - PROTÉGÉ
CRM_API_JSONP_ROUTER.gs        # INCHANGÉ - PROTÉGÉ
CRM_API_WEBAPP_COMPLET.gs      # INCHANGÉ - PROTÉGÉ
CRM_COMPLETE.gs                # INCHANGÉ - PROTÉGÉ
CRM_DEVIS_READ_WITH_JOIN.gs    # INCHANGÉ - PROTÉGÉ
CRM_DEVIS_VALIDATE_AND_RENDER.gs # INCHANGÉ - PROTÉGÉ
CRM_DEVIS_VALIDATE_PDF.gs      # INCHANGÉ - PROTÉGÉ

# === POST-VALIDATION (PROTÉGÉ) ===
R05_POST_OCR.gs                # INCHANGÉ - PROTÉGÉ
R05_POST_VALIDATION_HANDLER.gs # INCHANGÉ - PROTÉGÉ

# === DIAGNOSTICS / BACKUP ===
99_BACKUP_ALL_BOX2026.gs       # INCHANGÉ
99_DIAGNOSTICS.gs              # INCHANGÉ
99_DIAG_JSONL.gs               # INCHANGÉ
99_EXPORT_CODE_ZIP_AUDIT.gs    # INCHANGÉ
99_EXPORT_PROJECT_ZIP.gs       # INCHANGÉ

# === AUTRES (à conserver) ===
Dashboard_LAUNCHER.gs          # INCHANGÉ
GMAIL_COLLECT_TMP.gs           # INCHANGÉ
HTML_Render_AssetsInline.gs    # INCHANGÉ
OCR_PIPELINE_MAPPING_OPTION_B.gs # INCHANGÉ
P17_CLIENT_ID__INVENTORY.gs    # INCHANGÉ
RENDER_Slides_PDF.gs           # INCHANGÉ
RenommageIntelligent.gs        # INCHANGÉ
```

---

## 🎯 STRUCTURE REFACTORISÉE HUB (conforme IAPF)

```
# === BOOTSTRAP ===
G00_BOOTSTRAP.gs               # NEW: Renommé (anciennement 00_BOOTSTRAP.gs)

# === UI MENU ===
G01_UI_MENU.gs                 # NEW: Renommé + 5 boutons MCP ajoutés

# === SNAPSHOT ===
G02_SNAPSHOT_ENGINE.gs         # NEW: Renommé (anciennement 02_SNAPSHOT_ENGINE.gs)

# === MEMORY ===
G03_MEMORY_WRITE.gs            # NEW: Renommé (anciennement 03_MEMORY_WRITE.gs)

# === EXPORT ===
G04_EXPORT_ENGINE.gs           # NEW: Renommé (anciennement 04_DRIVE_IO.gs)

# === LOGGER ===
G05_LOGGER.gs                  # NEW: Renommé (anciennement 05_LOGGER.gs)

# === BOX2026 TOOLS ===
G06_BOX2026_TOOLS.gs           # NEW: Renommé (anciennement 06_BOX2026_TOOLS.gs)

# === MCP COCKPIT ===
G07_MCP_COCKPIT.gs             # NEW: Consolidation 06 + 07_MCP_COCKPIT.gs + 5 nouvelles fonctions MCP

# === README ===
G99_README.gs                  # NEW: Renommé (anciennement 99_README.gs)
```

---

## 📝 ACTIONS À RÉALISER

### 🔴 PHASE 1 : BOX2026 - REFACTORING MODULAIRE

#### 1.1 Créer les nouveaux modules OCR

**Fichier** : `03_OCR_ENGINE_FAST.gs`
- Extraction texte natif PDF
- Pas d'appel Cloud Run
- Rapide (< 1s)

**Fichier** : `03_OCR_ENGINE_CONTEXTUAL.gs`
- Appel Cloud Run standard
- Google Cloud Vision API
- Confidence tracking

**Fichier** : `03_OCR_ENGINE_MEMORY.gs`
- Appel Cloud Run + IA Memory
- Apprentissage progressif
- Seuil confiance 99-100%

#### 1.2 Créer les parsers centralisés

**Fichier** : `04_PARSERS_CORE.gs`
- `_BM_PARSERS_pickLongestText()`
- `_BM_PARSERS_extractInvoiceNumber()`
- `_BM_PARSERS_parseAmountFR()`
- `_BM_PARSERS_extractAmounts()`
- `_BM_PARSERS_extractDate()`
- `_BM_PARSERS_normalizeInvoiceNumber()`
- `_BM_PARSERS_validateAmount()`

**Fichier** : `04_PARSERS_SUPPLIERS.gs`
- `_BM_PARSERS_detectSupplier()`
- `_BM_PARSERS_enrichSupplierData()`
- Intégration IA_SUPPLIERS

#### 1.3 Refactoriser 02_SCAN_WORKER.gs

**Nouveau nom** : `02_SCAN_ORCHESTRATOR.gs`
- Suppression des parsers internes (déplacés vers 04_PARSERS_*.gs)
- Suppression des appels OCR directs (délégués vers 03_OCR_ENGINE_*.gs)
- Orchestration pure (workflow)
- Appels aux modules spécialisés

#### 1.4 Créer les pipelines

**Fichier** : `05_PIPELINE_MAPPER.gs`
- Mapping OCR → fields standardisés
- Transformation payload

**Fichier** : `05_PIPELINE_VALIDATOR.gs`
- Validation payload avant injection
- Règles métier
- Seuils confiance

**Fichier** : `06_OCR_INJECTION.gs`
- Injection payload validé
- Écriture INDEX_FACTURES
- Tracking état

#### 1.5 Créer post-validation

**Fichier** : `07_POST_VALIDATION.gs`
- Validation finale
- Renommage fichiers
- Classement Drive
- Écritures CRM/compta

---

### 🔴 PHASE 2 : HUB - RENOMMAGE + MCP

#### 2.1 Renommer tous les fichiers HUB

```
00_BOOTSTRAP.gs       → G00_BOOTSTRAP.gs
01_UI_MENU.gs         → G01_UI_MENU.gs
02_SNAPSHOT_ENGINE.gs → G02_SNAPSHOT_ENGINE.gs
03_MEMORY_WRITE.gs    → G03_MEMORY_WRITE.gs
04_DRIVE_IO.gs        → G04_EXPORT_ENGINE.gs
05_LOGGER.gs          → G05_LOGGER.gs
06_BOX2026_TOOLS.gs   → G06_BOX2026_TOOLS.gs
06_MCP_COCKPIT.gs     → (fusionné dans G07)
07_MCP_COCKPIT.gs     → G07_MCP_COCKPIT.gs
99_README.gs          → G99_README.gs
```

#### 2.2 Ajouter les 5 boutons MCP dans G01_UI_MENU.gs

1. **🟢 Initialiser Journée** → `MCP_initializeDay()`
2. **🔴 Clôture Journée** → `MCP_closeDay()`
3. **🔍 Audit Global** → `MCP_globalAudit()`
4. **✅ Vérification Doc vs Code** → `MCP_verifyDocVsCode()`
5. **🚀 Déploiement Automatisé** → `MCP_autoDeploy()`

#### 2.3 Implémenter les fonctions MCP dans G07_MCP_COCKPIT.gs

**Fonction** : `MCP_initializeDay()`
- Écriture MEMORY_LOG (type=INIT_DAY)
- Snapshot automatique
- Vérification état HUB
- Vérification état BOX2026

**Fonction** : `MCP_closeDay()`
- Écriture MEMORY_LOG (type=CLOSE_DAY)
- Snapshot automatique
- Stats journée
- Archivage si nécessaire

**Fonction** : `MCP_globalAudit()`
- Lecture MEMORY_LOG (30 dernières entrées)
- Vérification CONFLITS_DETECTES
- Mise à jour RISKS
- Rapport audit

**Fonction** : `MCP_verifyDocVsCode()`
- Vérification cohérence CARTOGRAPHIE_APPELS
- Vérification DEPENDANCES_SCRIPTS
- Détection écarts
- Mise à jour CONFLITS_DETECTES

**Fonction** : `MCP_autoDeploy()`
- Confirmation humaine obligatoire
- Appel Cloud Run health-check
- Trigger GitHub Actions
- Écriture MEMORY_LOG

---

### 🔴 PHASE 3 : MISE À JOUR ONGLETS HUB

#### 3.1 MEMORY_LOG (format TSV 7 colonnes strict)

```
ts_iso | type | title | details | author | source | tags
```

**Nouvelles entrées à ajouter** :
- Refactoring BOX2026 (date, type=DECISION, title=Refactoring modulaire complet, details=...)
- Création modules OCR (type=CONSTAT)
- Création parsers centralisés (type=CONSTAT)
- Renommage HUB (type=DECISION)
- Ajout boutons MCP (type=DECISION)

#### 3.2 SNAPSHOT_ACTIVE

Génération automatique via `G02_SNAPSHOT_ENGINE.gs`

#### 3.3 DEPENDANCES_SCRIPTS

```
script_source | script_target | fonction_appelée | type_dépendance | notes
BOX2026       | HUB           | MCP_globalAudit | API_CALL       | Audit automatique
HUB           | BOX2026       | 02_SCAN_ORCHESTRATOR | MONITORING | Suivi état BOX
```

#### 3.4 CARTOGRAPHIE_APPELS

```
projet | fichier_gs | fonction | appelle | notes
BOX2026 | 02_SCAN_ORCHESTRATOR | traiterNouveauDocument | 03_OCR_ENGINE_FAST | OCR Level 1
BOX2026 | 02_SCAN_ORCHESTRATOR | traiterNouveauDocument | 03_OCR_ENGINE_CONTEXTUAL | OCR Level 2
BOX2026 | 02_SCAN_ORCHESTRATOR | traiterNouveauDocument | 03_OCR_ENGINE_MEMORY | OCR Level 3
BOX2026 | 02_SCAN_ORCHESTRATOR | traiterNouveauDocument | 04_PARSERS_CORE | Parsers centralisés
```

#### 3.5 REGLES_DE_GOUVERNANCE

```
id | type | règle | justification | date_ajout
IAPF-001 | FONDATRICE | VIDE > BRUIT | Aucune invention autorisée | 2026-02-07
IAPF-002 | GOUVERNANCE | OCR = MIROIR | Extraction factuelle uniquement | 2026-02-07
IAPF-003 | GOUVERNANCE | POST_VALIDATION_ONLY | Validation humaine obligatoire | 2026-02-07
IAPF-004 | ARCHITECTURE | Séparation modules | Responsabilités séparées | 2026-02-14
IAPF-005 | NOMMAGE | Préfixe G* pour HUB | Différenciation HUB/BOX | 2026-02-14
```

#### 3.6 RISKS

```
id | titre | probabilité | impact | mitigation | statut
RISK-001 | Régression CRM | FAIBLE | CRITIQUE | Tests complets avant déploiement | ACTIF
RISK-002 | Perte mémoire IA | MOYEN | MOYEN | Snapshot quotidien | ACTIF
RISK-003 | Divergence branche GitHub | FAIBLE | MOYEN | Alignement strict main | RÉSOLU
```

#### 3.7 CONFLITS_DETECTES

```
id | source | type | description | résolution | statut
CONF-001 | BOX2026 | ARCHITECTURE | Parsers dupliqués dans 02_SCAN_WORKER | Centralisation dans 04_PARSERS_CORE | RÉSOLU
CONF-002 | BOX2026 | ARCHITECTURE | Responsabilités mélangées | Séparation modules OCR | RÉSOLU
CONF-003 | HUB | NOMMAGE | Confusion HUB/BOX | Préfixe G* ajouté | RÉSOLU
```

---

### 🔴 PHASE 4 : TESTS OBLIGATOIRES

#### 4.1 Test facture PDF classique

**Fichier test** : Facture PROMOCASH SIRET 43765996400021

**Tests** :
1. Extraction texte natif (Level 1)
2. Appel Cloud Run (Level 2)
3. Application IA_SUPPLIERS (Level 3)
4. Extraction numéro facture
5. Extraction montants HT/TVA/TTC
6. Génération nom_final
7. Génération chemin_final
8. Écriture INDEX_FACTURES

**Critères de réussite** :
- ✅ OCR Level détecté correctement
- ✅ Numéro facture extrait
- ✅ Montants extraits
- ✅ Nom_final conforme : `YYYY-MM-DD_PROMOCASH_TTC_<montant>EUR_FACTURE_<numero>.pdf`
- ✅ Chemin_final conforme : `/Box Magique/YYYY/MM/PROMOCASH/`
- ✅ Aucune erreur Apps Script

#### 4.2 Test image scannée

**Fichier test** : Image scannée (JPG/PNG)

**Tests** :
1. Appel Cloud Run Level 3
2. Google Cloud Vision API
3. Extraction texte
4. Parsers appliqués
5. Génération nom_final

**Critères de réussite** :
- ✅ OCR Level 3 détecté
- ✅ Cloud Run HTTP 200
- ✅ Texte OCR retourné
- ✅ Montants extraits
- ✅ Nom_final généré

#### 4.3 Test devis CRM

**Actions** :
1. Créer devis CRM
2. Générer PDF
3. Envoyer email

**Critères de réussite** :
- ✅ Devis créé
- ✅ PDF généré
- ✅ Email envoyé
- ✅ Aucune régression CRM

#### 4.4 Test boutons MCP

**Actions** :
1. Cliquer sur "🟢 Initialiser Journée"
2. Cliquer sur "🔴 Clôture Journée"
3. Cliquer sur "🔍 Audit Global"
4. Cliquer sur "✅ Vérification Doc vs Code"
5. Cliquer sur "🚀 Déploiement" (annuler)

**Critères de réussite** :
- ✅ Nouvelles lignes dans MEMORY_LOG
- ✅ Format TSV 7 colonnes respecté
- ✅ Snapshots générés
- ✅ RISKS mis à jour
- ✅ CONFLITS_DETECTES mis à jour

#### 4.5 Test Cloud Run health-check

**Commandes** :
```bash
curl https://box-magic-ocr-intelligent-jxjjoyxhgq-uc.a.run.app/health
curl https://box-magic-ocr-intelligent-jxjjoyxhgq-uc.a.run.app/
```

**Critères de réussite** :
- ✅ HTTP 200
- ✅ Version 1.0.1
- ✅ OCR engine initialized

---

## 📦 LIVRAISON FINALE ATTENDUE

### 📄 Fichiers modifiés (BOX2026)

**Nouveaux fichiers** :
1. `01_SCAN_ROUTING_GUARD.gs` (NEW)
2. `02_SCAN_ORCHESTRATOR.gs` (refactorisé depuis 02_SCAN_WORKER.gs)
3. `03_OCR_ENGINE_FAST.gs` (NEW)
4. `03_OCR_ENGINE_CONTEXTUAL.gs` (NEW)
5. `03_OCR_ENGINE_MEMORY.gs` (NEW)
6. `04_PARSERS_CORE.gs` (NEW)
7. `04_PARSERS_SUPPLIERS.gs` (NEW)
8. `05_PIPELINE_MAPPER.gs` (NEW)
9. `05_PIPELINE_VALIDATOR.gs` (NEW)
10. `06_OCR_INJECTION.gs` (NEW)
11. `07_POST_VALIDATION.gs` (NEW)

**Fichiers protégés (INCHANGÉS)** :
- `R06_IA_MEMORY_SUPPLIERS_APPLY.gs`
- `VALIDATION_GATE.gs`
- `OCR__CLOUDRUN_INTEGRATION11.gs`
- Tous les fichiers CRM
- R05_POST_OCR.gs
- R05_POST_VALIDATION_HANDLER.gs

### 📄 Fichiers modifiés (HUB)

**Renommages** :
1. `00_BOOTSTRAP.gs` → `G00_BOOTSTRAP.gs`
2. `01_UI_MENU.gs` → `G01_UI_MENU.gs` (+5 boutons MCP)
3. `02_SNAPSHOT_ENGINE.gs` → `G02_SNAPSHOT_ENGINE.gs`
4. `03_MEMORY_WRITE.gs` → `G03_MEMORY_WRITE.gs`
5. `04_DRIVE_IO.gs` → `G04_EXPORT_ENGINE.gs`
6. `05_LOGGER.gs` → `G05_LOGGER.gs`
7. `06_BOX2026_TOOLS.gs` → `G06_BOX2026_TOOLS.gs`
8. `06_MCP_COCKPIT.gs` + `07_MCP_COCKPIT.gs` → `G07_MCP_COCKPIT.gs` (+5 fonctions MCP)
9. `99_README.gs` → `G99_README.gs`

### 📊 Onglets HUB mis à jour

1. MEMORY_LOG (nouvelles entrées)
2. SNAPSHOT_ACTIVE (généré automatiquement)
3. DEPENDANCES_SCRIPTS (nouvelles dépendances)
4. CARTOGRAPHIE_APPELS (nouvelle cartographie)
5. REGLES_DE_GOUVERNANCE (5 nouvelles règles)
6. RISKS (3 risques ajoutés)
7. CONFLITS_DETECTES (3 conflits résolus)

### 📝 Rapport final

**Contenu** :
- Branche utilisée : main (commit 2a578fd)
- Révision Cloud Run : box-magic-ocr-intelligent-00091-gw7
- Image Docker : gcr.io/box-magique-gp-prod/box-magic-ocr-intelligent:0ba4a18
- Fichiers .gs modifiés : 20 (11 nouveaux BOX2026, 9 renommés HUB)
- Modules créés : 11
- Modules supprimés : 0 (legacy conservé)
- Tests exécutés : 5
- Résultat : ✅ ZÉRO RÉGRESSION

---

## 🚀 EXÉCUTION

**Durée estimée** : 3-4 heures

**Priorité** :
1. BOX2026 refactoring (2h)
2. HUB renommage + MCP (1h)
3. Tests (30 min)
4. Rapport final (30 min)

**Mode** : EXECUTION ONLY - ZÉRO COMPROMIS

---

**EST-CE QUE VOUS VALIDEZ CE PLAN AVANT EXÉCUTION ?**

---
