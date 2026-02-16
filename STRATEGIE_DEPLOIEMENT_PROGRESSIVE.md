# 🎯 STRATÉGIE DE DÉPLOIEMENT PROGRESSIVE — RÉSUMÉ EXÉCUTIF

**Date** : 2026-02-15 00:00  
**Principe** : **Zéro casse, zéro régression, validation terrain continue**

---

## 📋 VUE D'ENSEMBLE

| Phase | Durée | Actions | Tests | Critère de succès |
|-------|-------|---------|-------|-------------------|
| **Phase 1** | 15 min | Ajouter 04_PARSERS.gs + 03_OCR_ENGINE.gs | 1 test (facture PDF) | Aucune régression |
| **Phase 2** | 30 min | Brancher 02_SCAN_WORKER vers nouveaux modules | 3 tests (après chaque branchement) | Extraction identique ou meilleure |
| **Phase 3** | 20 min | Tests terrain complets (3 documents) | 3 tests (PDF + image + devis) | Tous les tests passent |
| **Phase 4** | 15 min | Nettoyage legacy (optionnel) | 4 tests (après chaque suppression) | Aucune erreur "fonction introuvable" |
| **TOTAL** | **80 min** | 4 phases | 11 tests | Zéro régression |

---

## 🔹 PHASE 1 : AJOUT DES NOUVEAUX MODULES (15 min)

### Actions
1. ✅ Créer `04_PARSERS.gs` (copier depuis `/home/user/webapp/BOX2026_COMPLET/04_PARSERS.gs`)
2. ✅ Créer `03_OCR_ENGINE.gs` (copier depuis `/home/user/webapp/BOX2026_COMPLET/03_OCR_ENGINE.gs`)
3. ✅ Sauvegarder (Ctrl+S)

### Test 1.1
- Uploader une facture PDF
- Vérifier : traitement normal, aucune erreur nouvelle

### Critère de succès
✅ Aucune régression (tout fonctionne comme avant)

**Fichier détaillé** : `/home/user/webapp/PHASE1_AJOUT_MODULES.md`

---

## 🔹 PHASE 2 : BRANCHEMENT PROGRESSIF (30 min)

### Phase 2.1 : Parsers de dates (10 min)
- Modifier `02_SCAN_WORKER.gs` : remplacer `_BM_parseDateFR_()` par appel à `BM_PARSERS_parseDateFR()`
- Test : date facture extraite correctement
- **Fichier détaillé** : `/home/user/webapp/PHASE2_1_PATCH_DATES.md`

### Phase 2.2 : Parsers de montants (10 min)
- Modifier `02_SCAN_WORKER.gs` : remplacer `_BM_parseAmountFR_()` et `_BM_extractAmounts_()` par appels à `BM_PARSERS_*`
- Test : montants HT/TTC/TVA extraits correctement
- **Fichier détaillé** : `/home/user/webapp/PHASE2_2_PATCH_MONTANTS.md`

### Phase 2.3 : Parsers de numéros (10 min)
- Modifier `02_SCAN_WORKER.gs` : remplacer `_BM_extractInvoiceNumber_()` par appel à `BM_PARSERS_extractInvoiceNumber()`
- Test : numéro facture extrait correctement
- **Fichier détaillé** : `/home/user/webapp/PHASE2_3_PATCH_NUMEROS.md`

### Critère de succès Phase 2
✅ Tous les parsers branchés, extraction identique ou meilleure

---

## 🔹 PHASE 3 : TESTS TERRAIN COMPLETS (20 min)

### Test 3.1 : PDF classique
- Document : facture PDF standard
- Vérifier : date, numéro, montants, aucune erreur

### Test 3.2 : Image scannée
- Document : photo facture smartphone
- Vérifier : extraction acceptable malgré qualité variable

### Test 3.3 : Devis CRM
- Document : devis PDF généré depuis CRM
- Vérifier : zéro régression sur index global

**Fichier détaillé** : `/home/user/webapp/PHASE3_TESTS_TERRAIN.md`

### Critère de succès Phase 3
✅ Tous les tests passent

---

## 🔹 PHASE 4 : NETTOYAGE LEGACY (15 min, OPTIONNEL)

⚠️ **À faire uniquement si Phase 3 validée à 100%**

### Actions
1. Supprimer anciennes fonctions parsers dans `02_SCAN_WORKER.gs`
2. Créer `99_LEGACY_BACKUP.gs` (archive ancien code)
3. (Optionnel) Supprimer `Utils.gs` et `01_SCAN_CANON.gs` si inutilisés
4. Déployer nouvelle version Apps Script

**Fichier détaillé** : `/home/user/webapp/PHASE4_NETTOYAGE_LEGACY.md`

### Critère de succès Phase 4
✅ Aucune erreur "fonction introuvable"

---

## ✅ GARANTIES

### Zéro casse
- ✅ Ancien code conservé jusqu'à validation complète
- ✅ Tests après chaque modification
- ✅ Rollback possible à tout moment (Ctrl+Z dans Apps Script)

### Zéro régression
- ✅ 11 tests terrain (validation continue)
- ✅ Extraction identique ou meilleure
- ✅ LOGS_SYSTEM surveillés à chaque étape

### Validation terrain
- ✅ 3 types de documents testés (PDF, image, devis)
- ✅ Tous les champs vérifiés (date, numéro, montants)
- ✅ Index global cohérent

---

## 📂 FICHIERS DE RÉFÉRENCE

| Fichier | Contenu | Localisation |
|---------|---------|--------------|
| `STRATEGIE_DEPLOIEMENT_PROGRESSIVE.md` | Vue d'ensemble (ce fichier) | `/home/user/webapp/` |
| `PHASE1_AJOUT_MODULES.md` | Détails Phase 1 (créé ci-dessous) | `/home/user/webapp/` |
| `PHASE2_1_PATCH_DATES.md` | Détails Phase 2.1 | `/home/user/webapp/` |
| `PHASE2_2_PATCH_MONTANTS.md` | Détails Phase 2.2 | `/home/user/webapp/` |
| `PHASE2_3_PATCH_NUMEROS.md` | Détails Phase 2.3 | `/home/user/webapp/` |
| `PHASE3_TESTS_TERRAIN.md` | Détails Phase 3 | `/home/user/webapp/` |
| `PHASE4_NETTOYAGE_LEGACY.md` | Détails Phase 4 | `/home/user/webapp/` |

---

## 🚀 PROCHAINE ACTION

**Commencer Phase 1** :
1. Ouvrir Apps Script BOX2026 : https://script.google.com/d/1AeIqlplLDtPUaXAHASHm91Q_wiXuXa7yNyV5sLOFfwjIKapyzwk3ha/edit
2. Créer `04_PARSERS.gs`
3. Créer `03_OCR_ENGINE.gs`
4. Tester avec une facture PDF
5. Si OK → Passer à Phase 2

**Durée totale estimée** : 80 minutes (1h20)

---

✅ **STRATÉGIE VALIDÉE — DÉPLOIEMENT SÉCURISÉ**

*2026-02-15 00:00 — Stratégie de déploiement progressive et sécurisée*
