# ✅ CHECKLIST VALIDATION ÉLIA — Patch BLK-001/002/003

**Date** : 2026-02-20  
**Patch** : Correction BLK-001 (MEMORY_APPEND_FAIL), BLK-002 (Audit Global), BLK-003 (Doc vs Code)  
**Source** : IAPF_HUB_EXPORT__20260220_112308.zip  
**Fichiers modifiés** : `G01_UI_MENU.gs`, `G08_MCP_ACTIONS.gs`

---

## 🎯 OBJECTIF

Prouver que les 3 blocages racines (BLK-001, BLK-002, BLK-003) + 2 correctifs UI/SAFE sont résolus.

---

## 📥 ÉTAPE 1 : Déploiement (5 min)

### 1.1 Copier fichiers corrigés
1. Ouvrir **Apps Script** du HUB IAPF Memory : `Extensions → Apps Script`
2. Remplacer ces 2 fichiers :
   - `G01_UI_MENU.gs` → copier contenu de `/HUB_COMPLET/G01_UI_MENU.gs`
   - `G08_MCP_ACTIONS.gs` → copier contenu de `/HUB_COMPLET/G08_MCP_ACTIONS.gs`
3. Cliquer **"Enregistrer"** (Ctrl+S)
4. Fermer Apps Script

### 1.2 Activer API Apps Script (prérequis BLK-003)
1. Ouvrir : https://console.cloud.google.com/apis/api/script.googleapis.com
2. Cliquer **"Activer"**
3. Retour Apps Script : éditer `appsscript.json` :
   ```json
   {
     "timeZone": "Europe/Paris",
     "dependencies": {},
     "exceptionLogging": "STACKDRIVER",
     "runtimeVersion": "V8",
     "oauthScopes": [
       "https://www.googleapis.com/auth/script.projects.readonly",
       "https://www.googleapis.com/auth/spreadsheets",
       "https://www.googleapis.com/auth/drive"
     ]
   }
   ```
4. Sauvegarder + fermer Apps Script
5. **Recharger Google Sheets (F5)**

### 1.3 (Optionnel) Configuration SETTINGS
Si vous voulez tester **Audit Lecture Partout (P1)**, ajouter dans onglet **SETTINGS** :
| Clé | Valeur |
|-----|--------|
| `github_token` | `<votre_token>` |
| `github_repo` | `romacmehdi971-lgtm/box-magic-ocr-intelligent` |

Si vous voulez tester **SAFE Mode (déploiement)**, ajouter :
| Clé | Valeur |
|-----|--------|
| `mcp_deploy_mode` | `DRY_RUN` (défaut) ou `PRODUCTION` |

---

## ✅ ÉTAPE 2 : Validation BLK-001 (10 min)

**Test** : Prouver que `Session.getActiveUser()` ne provoque jamais d'échec MEMORY_APPEND_FAIL

### Actions
1. Ouvrir onglet **MEMORY_LOG**, noter le nombre de lignes (ex: 50)
2. Menu **IAPF Memory → MCP Cockpit → 1️⃣ Initialiser Journée** (×10 runs)
3. Pour chaque run :
   - Popup "MCP — Initialiser Journée" → cliquer **Oui**
   - Attendre popup "✅ Snapshot créé..." → cliquer **OK**
4. Retour onglet **MEMORY_LOG**, noter le nouveau nombre de lignes (ex: 60)

### ✅ Critères de succès
| Critère | Résultat attendu | Statut |
|---------|------------------|--------|
| 10 runs sans erreur | Aucun popup d'erreur | ⏳ |
| 10 nouvelles lignes MEMORY_LOG | Count final = initial + 10 | ⏳ |
| Colonne `author` remplie | Jamais vide (email OU "SYSTEM/MCP" OU "SYSTEM") | ⏳ |
| Onglet LOGS sans erreur | Pas de ligne "MEMORY_APPEND_FAIL" | ⏳ |

**Si échec** : Vérifier G03_MEMORY_WRITE.gs lignes 7-24 (fonction `_getAuthorSafe_()`)

---

## ✅ ÉTAPE 3 : Validation BLK-002 (5 min)

**Test** : Prouver que l'audit global scanne transversalement tous les onglets + cartographie

### Actions
1. Menu **IAPF Memory → MCP Cockpit → 3️⃣ Audit Global**
2. Popup "MCP — Audit Global" → cliquer **Oui**
3. Attendre popup "=== AUDIT GLOBAL HUB (TRANSVERSAL) ===" :
   - Noter **"1) ONGLETS SCANNÉS : Total"** (ex: 15)
   - Noter **"3) CARTOGRAPHIE_APPELS : Fonctions détectées"** (ex: 120)
   - Vérifier **"5) STRUCTURE MEMORY_LOG : ✅ OK (7 colonnes)"**
4. Cliquer **OK**
5. Ouvrir onglet **CARTOGRAPHIE_APPELS** :
   - Vérifier colonnes : `file` | `function` | `updated_at`
   - Vérifier contenu : liste fonctions Apps Script (ex: `IAPF_generateSnapshot`, `MCP_IMPL_initializeDay`, etc.)
6. Ouvrir onglet **DEPENDANCES_SCRIPTS** :
   - Vérifier au moins une ligne : `GLOBAL | Audit scan executed | <timestamp>`
7. Ouvrir onglet **MEMORY_LOG** :
   - Vérifier dernière ligne : type=`CONSTAT`, title=`MCP — Audit global HUB (transversal complet)`, tags=`MCP;AUDIT;TRANSVERSAL`

### ✅ Critères de succès
| Critère | Résultat attendu | Statut |
|---------|------------------|--------|
| Rapport transversal complet | Popup avec 6 sections (onglets, cartographie, dépendances, structure, conflits, logs) | ⏳ |
| CARTOGRAPHIE_APPELS remplie | Min. 50 fonctions Apps Script | ⏳ |
| DEPENDANCES_SCRIPTS mis à jour | Au moins 1 ligne "Audit scan executed" | ⏳ |
| MEMORY_LOG audit tracé | Dernière ligne type CONSTAT, tags MCP;AUDIT;TRANSVERSAL | ⏳ |
| LOGS sans erreur | Pas de ligne "AUDIT_FAIL" | ⏳ |

**Si échec** : Vérifier G08_MCP_ACTIONS.gs lignes 168-315 (fonction `MCP_IMPL_globalAudit`)

---

## ✅ ÉTAPE 4 : Validation BLK-003 (5 min)

**Test** : Prouver que la vérification Doc vs Code génère un rapport diff exploitable

### Prérequis
⚠️ API Apps Script activée (ÉTAPE 1.2) ⚠️  
⚠️ Scope OAuth `script.projects.readonly` ajouté dans appsscript.json ⚠️

### Actions
1. Menu **IAPF Memory → MCP Cockpit → 4️⃣ Vérification Doc vs Code**
2. Popup "MCP — Vérification Doc vs Code" → cliquer **Oui**
3. **Si erreur "OAuth scope manquant"** :
   - Retour ÉTAPE 1.2 (ajouter scope dans appsscript.json)
   - Relancer (fermer/rouvrir Sheets + réautoriser)
4. Attendre popup "=== DOC vs CODE ===" :
   - Noter **"1) FONCTIONS DOCUMENTÉES (CARTOGRAPHIE_APPELS) : Total"** (ex: 120)
   - Noter **"2) FONCTIONS DANS LE CODE : Total"** (ex: 125)
   - Lire **"3) ÉCARTS"** :
     - "Dans doc, absentes du code" : count + liste (max 5)
     - "Dans code, absentes de doc" : count + liste (max 5)
   - Vérifier **"4) RÉSULTAT"** : "✅ Doc et Code 100% alignés" OU "⚠️ Écarts détectés"
5. Cliquer **OK**
6. Ouvrir onglet **MEMORY_LOG** :
   - Vérifier dernière ligne : type=`CONSTAT`, title=`MCP — Vérification Doc vs Code`, tags=`MCP;VERIFY;DIFF`

### ✅ Critères de succès
| Critère | Résultat attendu | Statut |
|---------|------------------|--------|
| Rapport diff complet | Popup avec 4 sections (doc, code, écarts, résultat) | ⏳ |
| Détection écarts bidirectionnel | Listes "doc→code" ET "code→doc" (peut être vide si aligné) | ⏳ |
| Première 5 entrées affichées | Si écarts > 5, afficher "... (+N autres)" | ⏳ |
| MEMORY_LOG vérification tracée | Dernière ligne type CONSTAT, tags MCP;VERIFY;DIFF | ⏳ |
| LOGS sans erreur | Pas de ligne "VERIFY_FAIL" (sauf si API désactivée) | ⏳ |

**Si erreur "API Apps Script non activée"** : Retour ÉTAPE 1.2  
**Si erreur "OAuth scope manquant"** : Retour ÉTAPE 1.2 (ajouter scope `script.projects.readonly`)

---

## ✅ ÉTAPE 5 : Validation UI Fix (2 min)

**Test** : Vérifier qu'il n'y a qu'une seule entrée "Générer snapshot" dans les menus

### Actions
1. Ouvrir menu **IAPF Memory** (menu principal)
2. Vérifier présence : **"Générer Snapshot"** ✅
3. Ouvrir menu **IAPF Memory → MCP Cockpit** (sous-menu)
4. Vérifier absence : **"Générer snapshot"** ❌ (doublon retiré)
5. Exécuter **IAPF Memory → Générer Snapshot** :
   - Doit créer un snapshot dans onglet **SNAPSHOT_ACTIVE**
   - Popup : **"Snapshot: OK"**

### ✅ Critères de succès
| Critère | Résultat attendu | Statut |
|---------|------------------|--------|
| Une seule entrée "Générer Snapshot" | Menu principal IAPF Memory | ⏳ |
| Pas de doublon | Sous-menu MCP Cockpit ne contient PAS "Générer snapshot" | ⏳ |
| Exécution OK | Onglet SNAPSHOT_ACTIVE mis à jour, popup "Snapshot: OK" | ⏳ |

**Si doublon présent** : Vérifier G01_UI_MENU.gs lignes 12-35 (menu MCP Cockpit)

---

## ✅ ÉTAPE 6 : Validation SAFE Mode (3 min)

**Test** : Vérifier que le mode SAFE (DRY_RUN) est actif par défaut pour le déploiement

### Actions
1. Ouvrir onglet **SETTINGS** :
   - Chercher ligne `mcp_deploy_mode`
   - Si absente → Mode par défaut = `DRY_RUN` ✅
   - Si présente → Noter valeur (DRY_RUN / STAGING / PRODUCTION)
2. Menu **IAPF Memory → MCP Cockpit → 5️⃣ Déploiement Automatisé (SAFE)**
3. Lire popup "MCP — Déploiement Automatisé (SAFE)" :
   - Vérifier ligne : **"Mode actuel : DRY_RUN"** (ou autre si configuré)
   - Si DRY_RUN : vérifier ligne **"✅ Mode SAFE : aucune action destructive"**
   - Si PRODUCTION : vérifier ligne **"⚠️ ATTENTION : déploiement en PRODUCTION"**
4. Cliquer **Oui**
5. Popup "ℹ️ Action en mode DRY_RUN" → cliquer **OK**
6. Ouvrir onglet **MEMORY_LOG** :
   - Vérifier dernière ligne : tags=`MCP;DEPLOY;SAFE`

### ✅ Critères de succès
| Critère | Résultat attendu | Statut |
|---------|------------------|--------|
| Mode par défaut DRY_RUN | Si SETTINGS.mcp_deploy_mode absent → DRY_RUN | ⏳ |
| Popup affiche mode actuel | "Mode actuel : DRY_RUN" (ou autre si configuré) | ⏳ |
| Warning PRODUCTION si configuré | Si mode=PRODUCTION, popup affiche "⚠️ ATTENTION : déploiement en PRODUCTION" | ⏳ |
| MEMORY_LOG tracé avec tags SAFE | Dernière ligne tags=MCP;DEPLOY;SAFE | ⏳ |
| Pas d'action destructive | Aucune modification Drive/GitHub/Cloud Run (mode DRY_RUN) | ⏳ |

**Si mode PRODUCTION par défaut** : Vérifier G08_MCP_ACTIONS.gs ligne 485 (défaut = "DRY_RUN")

---

## 📊 TABLEAU DE VALIDATION GLOBAL

| Blocage | Test | Critères OK | Statut | Notes |
|---------|------|-------------|--------|-------|
| **BLK-001** | 10 runs Init Journée | 10/10 OK, MEMORY_LOG +10 lignes, author rempli | ⏳ | |
| **BLK-002** | Audit Global | Rapport 6 sections, CARTOGRAPHIE_APPELS remplie, DEPENDANCES_SCRIPTS OK | ⏳ | |
| **BLK-003** | Doc vs Code | Rapport diff 4 sections, écarts détectés, MEMORY_LOG tracé | ⏳ | Prérequis : API Apps Script |
| **UI Fix** | Menu unique | Une seule entrée "Générer Snapshot" (menu principal) | ⏳ | |
| **SAFE Mode** | DRY_RUN défaut | Mode DRY_RUN par défaut, popup affiche mode, tags SAFE | ⏳ | |

**Légende** :
- ✅ Validé (tous critères OK)
- ⚠️ Partiel (certains critères KO)
- ❌ Échec (bloqué)
- ⏳ À tester

---

## 🚨 POINTS D'ATTENTION

### 1. BLK-003 (Doc vs Code) : Prérequis obligatoires
⚠️ **ÉTAPE 1.2 CRITIQUE** : Si API Apps Script pas activée OU scope OAuth manquant → Test BLK-003 échouera  
→ Erreur attendue : "⚠️ Impossible de scanner le code" + instructions dans popup  
→ Solution : Suivre ÉTAPE 1.2 (activer API + ajouter scope + relancer)

### 2. BLK-001 : Fallback déjà implémenté
✅ Aucune modification requise (G03_MEMORY_WRITE.gs déjà à jour dans export 112308)  
→ Test validera simplement l'absence de régression

### 3. BLK-002 : Audit transversal déjà implémenté
✅ Aucune modification requise (G08_MCP_ACTIONS.gs déjà à jour dans export 112308)  
→ Test validera simplement l'absence de régression

### 4. Patch minimal
🔧 Seules 2 fichiers modifiés :
- `G01_UI_MENU.gs` : suppression doublon "Générer snapshot" (ligne 30)
- `G08_MCP_ACTIONS.gs` : ajout SAFE Mode (lignes 476-520)

---

## 📝 RAPPORT À FOURNIR

Après validation, remplir ce tableau :

| Blocage | Statut | Critères validés | Critères échec | Notes |
|---------|--------|------------------|----------------|-------|
| BLK-001 | ✅ / ⚠️ / ❌ | N / 4 | | |
| BLK-002 | ✅ / ⚠️ / ❌ | N / 5 | | |
| BLK-003 | ✅ / ⚠️ / ❌ | N / 5 | | Prérequis API Apps Script OK ? |
| UI Fix | ✅ / ⚠️ / ❌ | N / 3 | | |
| SAFE Mode | ✅ / ⚠️ / ❌ | N / 5 | | |

**Score global** : ___ / 22 critères validés

**Conclusion** :
- [ ] ✅ Patch validé (22/22 OK) → Production
- [ ] ⚠️ Patch partiel (≥18/22 OK) → Ajustements mineurs
- [ ] ❌ Patch refusé (<18/22 OK) → Correction nécessaire

---

**Date création** : 2026-02-20 17:50 UTC  
**Validateur** : Élia  
**Version** : IAPF_HUB_EXPORT__20260220_112308 + patch BLK-001/002/003  
**Durée estimée** : 30 minutes (déploiement + 5 tests)
