# 🧪 TESTS MANDATAIRES - VALIDATION FINALE

**Date** : 2026-02-14  
**Version** : EXECUTION ONLY  
**Objectif** : Valider le bon fonctionnement post-refactoring

---

## 📋 CHECKLIST PRE-TEST

- [x] BM_Parsers.gs créé (251 lignes)
- [x] 02_SCAN_WORKER.gs refactorisé (1 776 lignes, -86)
- [x] 01_UI_MENU.gs modifié (+5 boutons MCP)
- [ ] BM_Parsers.gs déployé dans BOX2026
- [ ] 02_SCAN_WORKER.gs remplacé dans BOX2026
- [ ] 01_UI_MENU.gs remplacé dans HUB
- [ ] Onglets HUB mis à jour (7 onglets)

---

## 🧪 TEST 1 : FACTURE PDF CLASSIQUE

### 📄 Prérequis
- Type : Facture PDF avec texte natif
- Fournisseur : Enedis, EDF, ou autre
- Montant TTC visible
- Numéro de facture visible

### ⚙️ Procédure
1. Uploader le PDF dans Drive (dossier SCAN)
2. Lancer `traiterNouveauDocument(fichier)`
3. Vérifier dans les logs :
   - Extraction OCR réussie
   - `BM_PARSERS_extractInvoiceNumber()` appelé
   - `BM_PARSERS_extractAmounts()` appelé
   - `nom_final` généré correctement
   - `chemin_final` renseigné
   - Pas d'erreur `ReferenceError: _BM_*`

### ✅ Critères de validation
- ✅ OCR niveau détecté (1, 2 ou 3)
- ✅ Numéro de facture extrait
- ✅ Montant TTC extrait
- ✅ `nom_final` conforme au format
- ✅ Aucune erreur dans les logs
- ✅ Fichier classé dans Drive

### 📊 Résultat attendu
```javascript
{
  "invoice_number": "FA2024-12345",
  "montant_ttc": 1234.56,
  "nom_final": "2024-01-15_ENEDIS_FA2024-12345_1234-56.pdf",
  "chemin_final": "/Box Magique/2024/01/ENEDIS/",
  "ocr_level": "2_contextual",
  "status": "classified"
}
```

---

## 🧪 TEST 2 : IMAGE SCANNÉE (OCR NIVEAU 3)

### 📄 Prérequis
- Type : Image scannée (JPG, PNG)
- Qualité : Moyenne à faible
- Texte : Manuscrit ou imprimé flou
- Montant TTC visible

### ⚙️ Procédure
1. Uploader l'image dans Drive (dossier SCAN)
2. Lancer `traiterNouveauDocument(fichier)`
3. Vérifier dans les logs :
   - OCR niveau 3 (Cloud Run) détecté
   - Appel Cloud Run réussi
   - `BM_PARSERS_extractAmounts()` appliqué
   - Extraction montant TTC
   - `nom_final` généré

### ✅ Critères de validation
- ✅ OCR niveau 3 activé
- ✅ Cloud Run répond HTTP 200
- ✅ Texte OCR retourné
- ✅ Montant TTC extrait
- ✅ `nom_final` généré
- ✅ Pas d'erreur parser

### 📊 Résultat attendu
```javascript
{
  "ocr_level": "3_memory",
  "cloud_run_status": "success",
  "montant_ttc": 567.89,
  "nom_final": "2024-01-20_SOCIETE_567-89.jpg",
  "status": "classified"
}
```

---

## 🧪 TEST 3 : VERIFICATION CLOUD RUN

### 🌐 Endpoints à tester

#### Health Check
```bash
curl -s https://box-magic-ocr-intelligent-jxjjoyxhgq-uc.a.run.app/health
```
**Résultat attendu :**
```json
{
  "status": "healthy",
  "timestamp": "2026-02-14T22:30:00Z",
  "ocr_engine": "initialized"
}
```

#### Root Endpoint
```bash
curl -s https://box-magic-ocr-intelligent-jxjjoyxhgq-uc.a.run.app/
```
**Résultat attendu :**
```json
{
  "service": "BOX MAGIC OCR INTELLIGENT",
  "version": "1.0.1",
  "status": "running",
  "features": [
    "OCR 3 niveaux (fast/contextual/memory)",
    "Extraction texte PDF natif",
    "OCR image PDF (Tesseract)",
    "Détection type document",
    "Support multi-sociétés"
  ]
}
```

#### OCR Test (image)
```bash
# Test avec une image base64 (à adapter)
curl -X POST https://box-magic-ocr-intelligent-jxjjoyxhgq-uc.a.run.app/ocr \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "...",
    "level": "3_memory"
  }'
```

### ✅ Critères de validation
- ✅ Health check : HTTP 200
- ✅ Root endpoint : HTTP 200, version 1.0.1
- ✅ OCR endpoint : HTTP 200, texte retourné
- ✅ Temps de réponse < 10s
- ✅ Pas d'erreur 500/502

---

## 🧪 TEST 4 : BOUTONS MCP HUB

### 🔘 Test 1 : Initialiser Journée

**Procédure :**
1. Ouvrir le spreadsheet HUB
2. Menu "IAPF Memory" → "🎛️ MCP Cockpit" → "🟢 Initialiser Journée"
3. Confirmer l'action

**Résultat attendu :**
- ✅ Nouvelle ligne dans `MEMORY_LOG`
- ✅ Format : `YYYY-MM-DD HH:MM:SS\tSYSTEM\tINIT_DAY\tInitialisation journée\tJournée initialisée avec succès\t[DETAILS]\tOK`
- ✅ Toast de confirmation
- ✅ Pas d'erreur script

---

### 🔘 Test 2 : Clôture Journée

**Procédure :**
1. Menu "IAPF Memory" → "🎛️ MCP Cockpit" → "🔴 Clôture Journée"
2. Confirmer l'action

**Résultat attendu :**
- ✅ Nouvelle ligne dans `MEMORY_LOG`
- ✅ Format : `YYYY-MM-DD HH:MM:SS\tSYSTEM\tCLOSE_DAY\tClôture journée\tJournée clôturée\t[STATS]\tOK`
- ✅ Toast de confirmation
- ✅ Snapshot automatique créé

---

### 🔘 Test 3 : Audit Global

**Procédure :**
1. Menu "IAPF Memory" → "🎛️ MCP Cockpit" → "🔍 Audit Global"
2. Attendre la fin de l'audit

**Résultat attendu :**
- ✅ Nouvelle ligne dans `MEMORY_LOG`
- ✅ Format : `YYYY-MM-DD HH:MM:SS\tSYSTEM\tAUDIT\tAudit global\tAudit terminé\t[RÉSULTATS]\tOK`
- ✅ Onglets `RISKS` et `CONFLITS_DETECTES` mis à jour
- ✅ Toast de confirmation

---

### 🔘 Test 4 : Vérification Doc vs Code

**Procédure :**
1. Menu "IAPF Memory" → "🎛️ MCP Cockpit" → "✅ Vérification Doc vs Code"
2. Attendre la fin de la vérification

**Résultat attendu :**
- ✅ Nouvelle ligne dans `MEMORY_LOG`
- ✅ Format : `YYYY-MM-DD HH:MM:SS\tSYSTEM\tVERIFY_DOC\tVérification cohérence\tVérification terminée\t[ÉCARTS]\tOK`
- ✅ Onglet `CONFLITS_DETECTES` mis à jour
- ✅ Toast de confirmation

---

### 🔘 Test 5 : Déploiement Automatisé

**Procédure :**
1. Menu "IAPF Memory" → "🎛️ MCP Cockpit" → "🚀 Déploiement Automatisé"
2. **ATTENTION : NE PAS CONFIRMER EN PRODUCTION**
3. Annuler l'action

**Résultat attendu :**
- ✅ Popup de confirmation s'affiche
- ✅ Message de sécurité visible
- ✅ Si annulé : pas de ligne dans `MEMORY_LOG`
- ✅ Si confirmé : nouvelle ligne dans `MEMORY_LOG` + appel Cloud Run

---

## 🧪 TEST 5 : INDEX GLOBAL

### 📊 Vérification onglet INDEX_FACTURES

**Procédure :**
1. Ouvrir le spreadsheet BOX2026
2. Aller dans l'onglet `INDEX_FACTURES`
3. Vérifier les dernières lignes

**Critères de validation :**
- ✅ Colonne `nom_final` renseignée
- ✅ Colonne `chemin_final` renseignée
- ✅ Colonne `invoice_number` renseignée
- ✅ Colonne `montant_ttc` renseignée
- ✅ Colonne `ocr_level` renseignée (1, 2 ou 3)
- ✅ Colonne `status` = "classified"
- ✅ Pas de colonne vide (sauf optionnelles)

---

## 📊 RAPPORT DE TESTS

### ✅ Résumé

| Test | Status | Temps | Erreurs |
|------|--------|-------|---------|
| Facture PDF classique | ⏳ PENDING | - | - |
| Image scannée OCR 3 | ⏳ PENDING | - | - |
| Cloud Run health | ⏳ PENDING | - | - |
| Bouton Init Journée | ⏳ PENDING | - | - |
| Bouton Clôture Journée | ⏳ PENDING | - | - |
| Bouton Audit Global | ⏳ PENDING | - | - |
| Bouton Vérif Doc | ⏳ PENDING | - | - |
| Bouton Déploiement | ⏳ PENDING | - | - |
| Index global | ⏳ PENDING | - | - |

### 🎯 Score de validation
- **0/9** tests passés (0%)
- **Statut** : EN ATTENTE DE DÉPLOIEMENT

---

## 🚨 ERREURS CONNUES À SURVEILLER

### ⚠️ BOX2026
```javascript
// Erreur potentielle
ReferenceError: _BM_extractInvoiceNumber is not defined
// Solution : Vérifier que BM_Parsers.gs est bien déployé

// Erreur potentielle
TypeError: BM_PARSERS_extractInvoiceNumber is not a function
// Solution : Vérifier l'ordre de chargement des scripts
```

### ⚠️ HUB
```javascript
// Erreur potentielle
ReferenceError: MCP_initializeDay is not defined
// Solution : Vérifier que 06_MCP_COCKPIT.gs contient la fonction

// Erreur potentielle
TypeError: Cannot read property 'getSheetByName' of null
// Solution : Vérifier que le SpreadsheetApp.getActiveSpreadsheet() fonctionne
```

---

## 📝 NOTES IMPORTANTES

### 🔒 Scripts protégés (NE PAS MODIFIER)
- `R06_IA_MEMORY_SUPPLIERS_APPLY.gs`
- `VALIDATION_GATE.gs`
- `OCR__CLOUDRUN_INTEGRATION11.gs`

### 🔄 Migration en douceur
1. Déployer `BM_Parsers.gs` en premier
2. Tester les fonctions parsers individuellement
3. Déployer `02_SCAN_WORKER.gs` refactorisé
4. Tester une facture PDF simple
5. Tester une image scannée
6. Valider l'index global

### 📊 Monitoring
- Surveiller les logs Apps Script
- Vérifier les logs Cloud Run
- Surveiller l'onglet `MEMORY_LOG`
- Vérifier l'absence d'erreurs dans `CONFLITS_DETECTES`

---

## ✅ VALIDATION FINALE

**Condition de réussite :**
- ✅ 9/9 tests passés (100%)
- ✅ Aucune erreur Apps Script
- ✅ Cloud Run répond correctement
- ✅ Boutons MCP fonctionnels
- ✅ Index global à jour
- ✅ Aucune régression détectée

**Date de validation** : ___________  
**Validé par** : ___________  
**Commentaires** : ___________

---

**STATUT ACTUEL** : ⏳ **EN ATTENTE DE DÉPLOIEMENT APPS SCRIPT**
