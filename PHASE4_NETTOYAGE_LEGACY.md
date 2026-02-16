# 🔹 PHASE 4 : NETTOYAGE DU LEGACY (OPTIONNEL)

## ⚠️ ATTENTION : Ne faire que si Phase 3 validée à 100%

**Prérequis** :
- ✅ Phase 1 terminée (modules ajoutés)
- ✅ Phase 2 terminée (parsers branchés)
- ✅ Phase 3 terminée (tests terrain OK)

**Si au moins un test Phase 3 échoue** : ❌ NE PAS exécuter Phase 4

---

## 📋 Actions de nettoyage

### 4.1 : Supprimer les anciens parsers internes dans 02_SCAN_WORKER.gs

**Ancien code à supprimer** (dans 02_SCAN_WORKER.gs) :
```javascript
// Lignes ~750-1000 environ (à confirmer par lecture du fichier)
function _BM_parseDateFR_(text) {
  // ... ancienne logique ...
}

function _BM_parseAmountFR_(text) {
  // ... ancienne logique ...
}

function _BM_extractAmounts_(ocrText) {
  // ... ancienne logique ...
}

function _BM_extractInvoiceNumber_(ocrText) {
  // ... ancienne logique ...
}
```

**Action** :
1. Chercher ces fonctions dans 02_SCAN_WORKER.gs
2. Les supprimer complètement
3. Sauvegarder (Ctrl+S)

**Test 4.1** :
- Uploader une facture PDF
- Vérifier : tout fonctionne toujours (appels délégués à 04_PARSERS.gs)

---

### 4.2 : Créer 99_LEGACY_BACKUP.gs (archive de sécurité)

**Objectif** : Garder une copie de l'ancien code pour référence future

**Actions** :
1. Créer un nouveau fichier : `99_LEGACY_BACKUP.gs`
2. Copier l'ancien code supprimé (fonctions _BM_parseDateFR_, etc.)
3. Ajouter un commentaire en haut :
```javascript
/**
 * 99_LEGACY_BACKUP.gs
 * Archive de sécurité — ancien code de 02_SCAN_WORKER.gs
 * Date archivage : 2026-02-14
 * 
 * ⚠️ NE PAS UTILISER CES FONCTIONS
 * Remplacées par 04_PARSERS.gs
 * 
 * Conservé uniquement pour référence historique.
 */

// Ancienne fonction _BM_parseDateFR_ (remplacée par BM_PARSERS_parseDateFR)
function _LEGACY_BM_parseDateFR_(text) {
  // ... ancien code ...
}

// Ancienne fonction _BM_parseAmountFR_ (remplacée par BM_PARSERS_parseAmountFR)
function _LEGACY_BM_parseAmountFR_(text) {
  // ... ancien code ...
}

// ... etc ...
```

4. Sauvegarder (Ctrl+S)

---

### 4.3 : Déployer une nouvelle version Apps Script

**Actions** :
1. Dans Apps Script, cliquer "Déployer" → "Nouvelle version"
2. Description : "Nettoyage legacy — parsers centralisés dans 04_PARSERS.gs"
3. Déployer

**Test 4.3** :
- Uploader une facture PDF
- Vérifier : tout fonctionne toujours

---

### 4.4 : (Optionnel) Supprimer Utils.gs et 01_SCAN_CANON.gs

**⚠️ À faire uniquement si ces fichiers ne sont plus utilisés**

**Vérification préalable** :
1. Chercher dans tout le projet Apps Script les appels à :
   - Fonctions de `Utils.gs`
   - Fonctions de `01_SCAN_CANON.gs`
2. Si aucun appel trouvé : ces fichiers peuvent être supprimés
3. Sinon : les garder

**Actions** (si aucun appel trouvé) :
1. Créer `99_LEGACY_UTILS.gs` (copier Utils.gs dedans)
2. Créer `99_LEGACY_SCAN_CANON.gs` (copier 01_SCAN_CANON.gs dedans)
3. Supprimer `Utils.gs`
4. Supprimer `01_SCAN_CANON.gs`
5. Sauvegarder (Ctrl+S)

**Test 4.4** :
- Uploader une facture PDF
- Vérifier : aucune erreur "fonction introuvable"

---

## ✅ Critère de validation Phase 4

**Tous les tests passent** : ✅ Nettoyage réussi

**Au moins un test échoue** : ❌ Restaurer depuis 99_LEGACY_BACKUP.gs

---

## 📊 État final après Phase 4

**Fichiers Apps Script BOX2026** :
- ✅ `00_CONFIG_2026.gs` (existant, inchangé)
- ✅ `02_SCAN_WORKER.gs` (refactorisé, appelle 04_PARSERS.gs)
- ✅ `03_OCR_ENGINE.gs` (nouveau)
- ✅ `04_PARSERS.gs` (nouveau)
- ✅ `99_LEGACY_BACKUP.gs` (archive)
- ✅ (autres fichiers inchangés)

**Fichiers supprimés** :
- ❌ `Utils.gs` (si inutilisé) → archivé dans `99_LEGACY_UTILS.gs`
- ❌ `01_SCAN_CANON.gs` (si inutilisé) → archivé dans `99_LEGACY_SCAN_CANON.gs`

---

## Durée estimée : 15 minutes
