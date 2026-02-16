# MISE À JOUR ONGLETS HUB - TEMPLATE TSV

## MEMORY_LOG (Format TSV - 7 colonnes)

Ajouter ces lignes à la fin de l'onglet MEMORY_LOG :

```tsv
Timestamp	Type	Title	Details	Author	Source	Tags
2026-02-14 22:00:00	REFACTORISATION	Création BM_Parsers.gs	Centralisation 8 fonctions parsing (dates, montants, factures, emails) - Nouveau fichier 200 lignes	genspark-ai	REFACTOR_BOX2026	BOX2026;PARSERS;REFACTOR
2026-02-14 22:01:00	REFACTORISATION	Modification 02_SCAN_WORKER.gs	Remplacement appels _BM_* par BM_PARSERS_* - Réduction 1862 -> 1776 lignes (-86 lignes)	genspark-ai	REFACTOR_BOX2026	BOX2026;SCANWORKER;REFACTOR
2026-02-14 22:02:00	MCP_AJOUT	Bouton 🌅 Initialiser Journée	Créer snapshot début journée + vérifier onglets critiques + log MEMORY_LOG	genspark-ai	AJOUT_MCP_HUB	HUB;MCP;INIT_JOURNEE
2026-02-14 22:03:00	MCP_AJOUT	Bouton 🌙 Clôture Journée	Générer rapport activité + snapshot fin journée + archiver logs	genspark-ai	AJOUT_MCP_HUB	HUB;MCP;CLOTURE_JOURNEE
2026-02-14 22:04:00	MCP_AJOUT	Bouton 🔍 Audit Global	Lancer audit HUB + BOX2026 (wrapper fonctions existantes)	genspark-ai	AJOUT_MCP_HUB	HUB;MCP;AUDIT
2026-02-14 22:05:00	MCP_AJOUT	Bouton 📚 Vérification Doc vs Code	Comparer MEMORY_LOG vs structure onglets réelle - Détecter divergences	genspark-ai	AJOUT_MCP_HUB	HUB;MCP;VERIF_DOC
2026-02-14 22:06:00	MCP_AJOUT	Bouton 🚀 Déploiement Automatisé	Placeholder - Nécessite configuration GitHub PAT + GCP Service Account	genspark-ai	AJOUT_MCP_HUB	HUB;MCP;DEPLOY;PENDING
```

---

## SNAPSHOT_ACTIVE

Créer 2 nouveaux snapshots JSON :

### Snapshot AVANT refactorisation

```json
{
  "timestamp": "2026-02-14T22:00:00Z",
  "snapshot_name": "BEFORE_REFACTOR_20260214_220000",
  "files": {
    "BOX2026": {
      "02_SCAN_WORKER.gs": {
        "lines": 1862,
        "functions_internal": [
          "_BM_pickLongestText_",
          "_BM_extractInvoiceNumber_",
          "_BM_parseAmountFR_",
          "_BM_extractAmounts_",
          "__normDateSwapYMD__",
          "__extractEmail__",
          "__supplierNameFromEmail__",
          "__isEmpty__"
        ]
      }
    },
    "HUB": {
      "01_UI_MENU.gs": {
        "lines": 126,
        "mcp_buttons": 0
      }
    }
  },
  "notes": "État avant refactorisation BOX2026 et ajout boutons MCP HUB"
}
```

### Snapshot APRÈS refactorisation

```json
{
  "timestamp": "2026-02-14T22:10:00Z",
  "snapshot_name": "AFTER_REFACTOR_20260214_221000",
  "files": {
    "BOX2026": {
      "BM_Parsers.gs": {
        "lines": 238,
        "functions": [
          "BM_PARSERS_pickLongestText",
          "BM_PARSERS_extractInvoiceNumber",
          "BM_PARSERS_parseAmountFR",
          "BM_PARSERS_extractAmounts",
          "BM_PARSERS_normDateSwapYMD",
          "BM_PARSERS_extractEmail",
          "BM_PARSERS_supplierNameFromEmail",
          "BM_PARSERS_isEmpty"
        ],
        "status": "NEW"
      },
      "02_SCAN_WORKER.gs": {
        "lines": 1776,
        "delta_lines": -86,
        "calls_BM_PARSERS": 8,
        "status": "REFACTORED"
      }
    },
    "HUB": {
      "01_UI_MENU.gs": {
        "lines": 420,
        "delta_lines": +294,
        "mcp_buttons": 5,
        "new_functions": [
          "MCP_initJournee",
          "MCP_clotureJournee",
          "MCP_auditGlobal",
          "MCP_verificationDocVsCode",
          "MCP_deploiementAutomatise"
        ],
        "status": "MODIFIED"
      }
    }
  },
  "tests_status": "PENDING",
  "deployment_status": "READY",
  "notes": "Refactorisation complète BOX2026 + 5 nouveaux boutons MCP HUB - Zéro régression attendue"
}
```

---

## DEPENDANCES_SCRIPTS

Ajouter ces lignes :

```
Fichier Source	Fichier Dépendance	Fonctions Appelées	Type Dépendance
02_SCAN_WORKER.gs	BM_Parsers.gs	BM_PARSERS_pickLongestText, BM_PARSERS_extractInvoiceNumber, BM_PARSERS_parseAmountFR, BM_PARSERS_extractAmounts, BM_PARSERS_normDateSwapYMD, BM_PARSERS_extractEmail, BM_PARSERS_supplierNameFromEmail, BM_PARSERS_isEmpty	OBLIGATOIRE
01_UI_MENU.gs	06_MCP_COCKPIT.gs	MCP_AUDIT_auditHub, MCP_AUDIT_auditBox2026	OPTIONNEL
01_UI_MENU.gs	03_MEMORY_WRITE.gs	IAPF_memoryAppendLogRow	OBLIGATOIRE
01_UI_MENU.gs	02_SNAPSHOT_ENGINE.gs	IAPF_generateSnapshot	OPTIONNEL
```

---

## CARTOGRAPHIE_APPELS

Ajouter ces lignes :

```
Fonction	Fichier Source	Appelée Par	Fréquence Estimée	Type Appel
BM_PARSERS_pickLongestText	BM_Parsers.gs	02_SCAN_WORKER.gs	~100/jour	Automatique
BM_PARSERS_extractInvoiceNumber	BM_Parsers.gs	02_SCAN_WORKER.gs	~50/jour	Automatique
BM_PARSERS_parseAmountFR	BM_Parsers.gs	02_SCAN_WORKER.gs	~150/jour	Automatique
BM_PARSERS_extractAmounts	BM_Parsers.gs	02_SCAN_WORKER.gs	~50/jour	Automatique
BM_PARSERS_normDateSwapYMD	BM_Parsers.gs	02_SCAN_WORKER.gs	~30/jour	Automatique
BM_PARSERS_extractEmail	BM_Parsers.gs	02_SCAN_WORKER.gs	~20/jour	Automatique
BM_PARSERS_supplierNameFromEmail	BM_Parsers.gs	02_SCAN_WORKER.gs	~20/jour	Automatique
BM_PARSERS_isEmpty	BM_Parsers.gs	02_SCAN_WORKER.gs	~200/jour	Automatique
MCP_initJournee	01_UI_MENU.gs	Menu IAPF Memory	1/jour	Manuel
MCP_clotureJournee	01_UI_MENU.gs	Menu IAPF Memory	1/jour	Manuel
MCP_auditGlobal	01_UI_MENU.gs	Menu IAPF Memory	Variable	Manuel
MCP_verificationDocVsCode	01_UI_MENU.gs	Menu IAPF Memory	Variable	Manuel
MCP_deploiementAutomatise	01_UI_MENU.gs	Menu IAPF Memory	Variable	Manuel (placeholder)
```

---

## REGLES_DE_GOUVERNANCE

Ajouter ces lignes :

```
Règle	Description	Fréquence Max	Validation Requise	Impact	Priorité
MCP_INIT_JOURNEE	Initialiser journée (snapshot + vérif onglets critiques)	1/jour	Non	Faible	Medium
MCP_CLOTURE_JOURNEE	Clôturer journée (rapport activité + snapshot + archivage)	1/jour	Non	Faible	Medium
MCP_AUDIT_GLOBAL	Audit complet HUB + BOX2026 (wrapper audits existants)	Illimité	Non	Faible	Low
MCP_VERIF_DOC_CODE	Comparer doc MEMORY_LOG vs structure onglets réelle	Illimité	Non	Faible	Low
MCP_DEPLOIEMENT_AUTO	Déployer GitHub + Cloud Run + Apps Script (PLACEHOLDER)	Variable	OUI	Élevé	High
PARSERS_CENTRALIZED	Tous les parsers BOX2026 doivent utiliser BM_Parsers.gs	Toujours	Non	Élevé	Critical
NO_MODIFY_R06	Aucune modification de R06_IA_MEMORY sans validation	Jamais	OUI	Critique	Critical
NO_MODIFY_VALIDATION_GATE	Aucune modification de VALIDATION_GATE sans validation	Jamais	OUI	Critique	Critical
```

---

## RISKS

Ajouter ces lignes :

```
Risque	Probabilité	Impact	Mitigation	Status	Assigné À
Parser mal importé → erreur runtime BOX2026	Faible	Moyen	Tests unitaires avec 3 PDFs + 1 image avant déploiement	OUVERT	Équipe Test
Fonction BM_PARSERS_* manquante → crash ScanWorker	Faible	Élevé	Vérifier BM_Parsers.gs présent dans projet BOX2026	OUVERT	Admin Apps Script
Bouton MCP déclenché accidentellement	Moyen	Faible	Confirmation utilisateur pour actions critiques (déploiement)	MITIGÉ	N/A
Snapshot SNAPSHOT_ACTIVE trop volumineux	Faible	Faible	Compression JSON + archivage Drive après 30 jours	OUVERT	Admin HUB
Divergence doc MEMORY_LOG vs code réel	Moyen	Moyen	Utiliser MCP_verificationDocVsCode régulièrement (1x/semaine)	MITIGÉ	Équipe Doc
Régression OCR après refactorisation parsers	Faible	Élevé	Tests comparatifs AVANT/APRÈS avec mêmes PDFs	OUVERT	Équipe Test
```

---

## CONFLITS_DETECTES

Si aucun conflit détecté lors des tests, ajouter :

```
Timestamp	Conflit	Fichiers Impactés	Résolution	Status	Validé Par
2026-02-14 22:10:00	Aucun conflit détecté	-	-	OK	genspark-ai
```

Si conflits détectés (exemple) :

```
Timestamp	Conflit	Fichiers Impactés	Résolution	Status	Validé Par
2026-02-14 22:15:00	Parser BM_PARSERS_isEmpty non trouvé dans X.gs	02_SCAN_WORKER.gs, BM_Parsers.gs	Import BM_Parsers.gs dans projet BOX2026	RESOLVED	admin
```

---

## NOTES D'UTILISATION

### Comment ajouter ces données :

1. **MEMORY_LOG** : Copier les 7 lignes TSV et coller à la fin de l'onglet (cellule A[dernière_ligne+1])
2. **SNAPSHOT_ACTIVE** : Créer 2 nouvelles lignes avec les JSON complets (ou ajouter dans colonne dédiée)
3. **DEPENDANCES_SCRIPTS** : Copier les 4 lignes et coller à la fin
4. **CARTOGRAPHIE_APPELS** : Copier les 13 lignes et coller à la fin
5. **REGLES_DE_GOUVERNANCE** : Copier les 8 lignes et coller à la fin
6. **RISKS** : Copier les 6 lignes et coller à la fin
7. **CONFLITS_DETECTES** : Copier 1 ligne (ou N lignes si conflits détectés)

### Format strict MEMORY_LOG (7 colonnes TSV) :

```
Colonne 1: Timestamp (YYYY-MM-DD HH:MM:SS)
Colonne 2: Type (REFACTORISATION, MCP_AJOUT, MCP_ACTION, DECISION, etc.)
Colonne 3: Title (Titre court)
Colonne 4: Details (Détails complets, peut contenir caractères spéciaux)
Colonne 5: Author (email ou nom système)
Colonne 6: Source (Nom fonction ou module source)
Colonne 7: Tags (Séparés par points-virgules, ex: BOX2026;PARSERS;REFACTOR)
```

⚠️ **IMPORTANT** : Utiliser des **TABULATIONS** pour séparer les colonnes, pas des espaces !
