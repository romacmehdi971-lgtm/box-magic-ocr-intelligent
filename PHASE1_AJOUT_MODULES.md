# 🔹 PHASE 1 : AJOUT DES NOUVEAUX MODULES

**Durée** : 15 minutes  
**Objectif** : Ajouter les nouveaux modules **SANS toucher au code existant**

---

## 📋 ACTIONS

### Étape 1.1 : Ouvrir Apps Script BOX2026
**URL** : https://script.google.com/d/1AeIqlplLDtPUaXAHASHm91Q_wiXuXa7yNyV5sLOFfwjIKapyzwk3ha/edit

---

### Étape 1.2 : Créer 04_PARSERS.gs

**Actions** :
1. Dans Apps Script, cliquer le bouton **"+"** (Ajouter un fichier)
2. Sélectionner **"Script"**
3. Nommer le fichier : `04_PARSERS`
4. Copier le contenu depuis `/home/user/webapp/BOX2026_COMPLET/04_PARSERS.gs`
5. Coller dans l'éditeur Apps Script
6. Sauvegarder (Ctrl+S)

**Contenu à copier** : 
```javascript
/**
 * ============================================================================
 * BOX MAGIC 2026 — 04_PARSERS.gs
 * Rôle : parsers centralisés (dates, montants, numéros)
 * ============================================================================
 */

// 10 fonctions de parsing centralisées :
// - BM_PARSERS_parseDateFR()
// - BM_PARSERS_parseAmountFR()
// - BM_PARSERS_extractAmounts()
// - BM_PARSERS_extractInvoiceNumber()
// - BM_PARSERS_extractEmail()
// - BM_PARSERS_extractSupplierName()
// - BM_PARSERS_pickLongestText()
// - BM_PARSERS_isEmptyOrUnknown()
// - BM_PARSERS_safeSetField()
// - BM_PARSERS_normalizeDate()

// ... (contenu complet du fichier)
```

**Note** : Le fichier complet fait 14 KB (329 lignes). Copier l'intégralité depuis le fichier source.

---

### Étape 1.3 : Créer 03_OCR_ENGINE.gs

**Actions** :
1. Dans Apps Script, cliquer le bouton **"+"** (Ajouter un fichier)
2. Sélectionner **"Script"**
3. Nommer le fichier : `03_OCR_ENGINE`
4. Copier le contenu depuis `/home/user/webapp/BOX2026_COMPLET/03_OCR_ENGINE.gs`
5. Coller dans l'éditeur Apps Script
6. Sauvegarder (Ctrl+S)

**Contenu à copier** :
```javascript
/**
 * ============================================================================
 * BOX MAGIC 2026 — 03_OCR_ENGINE.gs
 * Rôle : OCR centralisé (4 niveaux : Fast, Contextual, Memory, Auto)
 * ============================================================================
 */

// 4 fonctions OCR :
// - BM_OCR_ENGINE_runFast()      // Niveau 1 : OCR rapide (PDF natif)
// - BM_OCR_ENGINE_runContextual() // Niveau 2 : OCR contextuel (images)
// - BM_OCR_ENGINE_runMemory()    // Niveau 3 : OCR avec mémoire fournisseurs
// - BM_OCR_ENGINE_runAuto()      // Niveau Auto : sélection intelligente

// ... (contenu complet du fichier)
```

**Note** : Le fichier complet fait 14 KB (350 lignes). Copier l'intégralité depuis le fichier source.

---

### Étape 1.4 : Vérifier la compilation

**Actions** :
1. Dans Apps Script, cliquer sur **"Exécuter"** (icône ▶️)
2. Sélectionner une fonction quelconque (ex: `BM_PARSERS_parseDateFR`)
3. Cliquer **"Exécuter"**
4. Vérifier : aucune erreur de syntaxe

**Erreur attendue** (normal) :
```
TypeError: Cannot read property 'parseDateFR' of undefined
```
→ C'est normal, la fonction attend un argument. L'important est qu'il n'y ait **pas d'erreur de syntaxe**.

**Si erreur de syntaxe** :
- Vérifier que le copier-coller est complet
- Vérifier qu'il n'y a pas de caractères parasites
- Corriger et sauvegarder

---

## 🧪 TEST 1.1 : VALIDATION TERRAIN

### Objectif
Vérifier que l'ajout des nouveaux modules **ne casse rien**.

### Actions

**1. Uploader une facture PDF dans INBOX**
- Utiliser une facture PDF classique (texte numérique)
- Exemple : `Facture_2025-01-15_ACME_Corp_FA2025001_1234.56.pdf`

**2. Attendre le traitement** (30-60 secondes)
- Le trigger automatique devrait se déclencher
- `traiterNouveauDocument()` devrait s'exécuter

**3. Ouvrir LOGS_SYSTEM**
- Dans la Google Sheet BOX2026, onglet `LOGS_SYSTEM`
- Filtrer par date/heure récente
- Chercher les lignes liées au traitement de la facture

**4. Vérifier l'absence d'erreurs nouvelles**
- ✅ Aucune ligne avec niveau `ERROR` liée aux nouveaux modules
- ✅ Aucune erreur `ReferenceError: BM_PARSERS_* is not defined`
- ✅ Aucune erreur `ReferenceError: BM_OCR_ENGINE_* is not defined`

**5. Ouvrir INDEX_FACTURES**
- Dans la Google Sheet BOX2026, onglet `INDEX_FACTURES`
- Chercher la ligne correspondant à la facture uploadée
- Vérifier que les champs sont remplis normalement :
  - ✅ Date facture extraite
  - ✅ Numéro facture extrait
  - ✅ Montant TTC extrait
  - ✅ Statut = "INDEXÉ" ou équivalent

---

## ✅ CRITÈRE DE SUCCÈS PHASE 1

**Tous les critères remplis** :
- ✅ Les 2 nouveaux modules sont ajoutés sans erreur de syntaxe
- ✅ Le traitement d'une facture PDF fonctionne normalement
- ✅ Aucune erreur nouvelle dans LOGS_SYSTEM
- ✅ INDEX_FACTURES mis à jour normalement

**Si au moins un critère échoue** :
- ❌ Analyser les logs (chercher les erreurs exactes)
- ❌ Vérifier que les fichiers ont été copiés en entier
- ❌ Corriger et retester

---

## 📊 TABLEAU DE VALIDATION

| Critère | Statut | Notes |
|---------|--------|-------|
| 04_PARSERS.gs créé sans erreur | ⏳ À valider | |
| 03_OCR_ENGINE.gs créé sans erreur | ⏳ À valider | |
| Facture PDF traitée normalement | ⏳ À valider | |
| Aucune erreur dans LOGS_SYSTEM | ⏳ À valider | |
| INDEX_FACTURES mis à jour | ⏳ À valider | |

**Remplir ce tableau après Test 1.1** (remplacer ⏳ par ✅ ou ❌)

---

## 🚀 PROCHAINE ÉTAPE

**Si Phase 1 validée** : ✅ Passer à **Phase 2.1** (brancher parsers de dates)

**Fichier suivant** : `/home/user/webapp/PHASE2_1_PATCH_DATES.md`

---

**Durée totale Phase 1** : 15 minutes
