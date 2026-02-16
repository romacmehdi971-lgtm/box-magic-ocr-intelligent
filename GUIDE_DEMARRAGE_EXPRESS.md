# ⚡ GUIDE DÉMARRAGE EXPRESS — DÉPLOIEMENT PROGRESSIF

**Date** : 2026-02-15 00:10  
**Durée totale** : 45 minutes (Option B recommandée)  
**Principe** : Zéro casse, validation terrain

---

## 🎯 OBJECTIF

Déployer les nouveaux parsers centralisés **sans supprimer l'ancien code**, en testant à chaque étape.

---

## 📋 ÉTAPES SIMPLIFIÉES

### ✅ ÉTAPE 1 : Ajouter les nouveaux modules (15 min)

**Ouvrir** : https://script.google.com/d/1AeIqlplLDtPUaXAHASHm91Q_wiXuXa7yNyV5sLOFfwjIKapyzwk3ha/edit

**Créer 2 fichiers** :
1. `04_PARSERS.gs` → copier depuis `/home/user/webapp/BOX2026_COMPLET/04_PARSERS.gs`
2. `03_OCR_ENGINE.gs` → copier depuis `/home/user/webapp/BOX2026_COMPLET/03_OCR_ENGINE.gs`

**Tester** : Uploader une facture PDF → vérifier LOGS_SYSTEM (aucune erreur nouvelle)

**Fichier détaillé** : `/home/user/webapp/PHASE1_AJOUT_MODULES.md`

---

### ✅ ÉTAPE 2 : Brancher les parsers (30 min)

**Modifier** `02_SCAN_WORKER.gs` en 3 étapes :

#### 2.1 : Dates (10 min)
Remplacer `_BM_parseDateFR_()` par appel à `BM_PARSERS_parseDateFR()`  
→ Tester : date facture extraite correctement

#### 2.2 : Montants (10 min)
Remplacer `_BM_parseAmountFR_()` et `_BM_extractAmounts_()` par appels à `BM_PARSERS_*`  
→ Tester : montants HT/TTC/TVA extraits correctement

#### 2.3 : Numéros (10 min)
Remplacer `_BM_extractInvoiceNumber_()` par appel à `BM_PARSERS_extractInvoiceNumber()`  
→ Tester : numéro facture extrait correctement

**Fichiers détaillés** :
- `/home/user/webapp/PHASE2_1_PATCH_DATES.md`
- `/home/user/webapp/PHASE2_2_PATCH_MONTANTS.md`
- `/home/user/webapp/PHASE2_3_PATCH_NUMEROS.md`

---

### ⏸️ ARRÊT RECOMMANDÉ

**Après Étape 2** : STOP et valider en production pendant quelques jours.

**Pourquoi ?**
- Les nouveaux parsers sont actifs
- L'ancien code est toujours présent (backup)
- Validation terrain réelle (pas seulement 1 test)

**Étapes 3-4** : À faire plus tard (après validation terrain complète)

---

### 🔄 ROLLBACK SI PROBLÈME

**Phase 1** : Supprimer `04_PARSERS.gs` et `03_OCR_ENGINE.gs`

**Phase 2** : Ctrl+Z dans Apps Script (annuler modifications dans `02_SCAN_WORKER.gs`)

---

## 📂 FICHIERS DISPONIBLES

### Code source
```
/home/user/webapp/BOX2026_COMPLET/
├── 04_PARSERS.gs          (14 KB)  → À copier dans Apps Script
├── 03_OCR_ENGINE.gs       (14 KB)  → À copier dans Apps Script
└── 02_SCAN_ORCHESTRATOR.gs (7 KB)  → Pour référence (ne pas déployer maintenant)
```

### Documentation
```
/home/user/webapp/
├── DEPLOIEMENT_PROGRESSIF_RESUME.md     → Vue d'ensemble
├── GUIDE_DEMARRAGE_EXPRESS.md           → Ce fichier
├── PHASE1_AJOUT_MODULES.md              → Détails Étape 1
├── PHASE2_1_PATCH_DATES.md              → Détails Étape 2.1
├── PHASE2_2_PATCH_MONTANTS.md           → Détails Étape 2.2
├── PHASE2_3_PATCH_NUMEROS.md            → Détails Étape 2.3
├── PHASE3_TESTS_TERRAIN.md              → Étape 3 (plus tard)
└── PHASE4_NETTOYAGE_LEGACY.md           → Étape 4 (plus tard)
```

---

## ✅ CHECKLIST MINIMALE (45 min)

### Phase 1 (15 min)
- [ ] `04_PARSERS.gs` créé dans Apps Script
- [ ] `03_OCR_ENGINE.gs` créé dans Apps Script
- [ ] Sauvegarde (Ctrl+S)
- [ ] Test facture PDF → Aucune erreur dans LOGS_SYSTEM

### Phase 2.1 (10 min)
- [ ] Modifier `02_SCAN_WORKER.gs` : parsers dates
- [ ] Sauvegarde (Ctrl+S)
- [ ] Test facture PDF → Date extraite correctement

### Phase 2.2 (10 min)
- [ ] Modifier `02_SCAN_WORKER.gs` : parsers montants
- [ ] Sauvegarde (Ctrl+S)
- [ ] Test facture PDF → Montants extraits correctement

### Phase 2.3 (10 min)
- [ ] Modifier `02_SCAN_WORKER.gs` : parsers numéros
- [ ] Sauvegarde (Ctrl+S)
- [ ] Test facture PDF → Numéro extrait correctement

---

## 🎯 RÉSULTAT ATTENDU

Après ces 45 minutes :
- ✅ Nouveaux parsers centralisés actifs
- ✅ Ancien code toujours présent (backup)
- ✅ Extraction identique ou meilleure
- ✅ Zéro régression

**Validation terrain** : Laisser tourner quelques jours avant Phase 3-4

---

## 📞 AIDE

**Si blocage** : Lire les fichiers détaillés (`PHASE*.md`)

**Si erreur** : Analyser LOGS_SYSTEM + Ctrl+Z pour rollback

**Support complet** : `/home/user/webapp/STRATEGIE_DEPLOIEMENT_PROGRESSIVE.md`

---

✅ **PRÊT À DÉPLOYER EN 45 MINUTES**

*2026-02-15 00:10 — Guide express de déploiement progressif*
