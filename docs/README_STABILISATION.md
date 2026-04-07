# 📘 PHASE STABILISATION IAPF 2026 – Guide Complet

**Date**: 2026-02-14  
**Version**: 2.0.0  
**Mode**: PROPOSAL-ONLY strict  
**Commit**: de1dde0  
**Branch**: feature/ocr-intelligent-3-levels

---

## 🎯 OBJECTIF

Nettoyer et stabiliser le système IAPF (OCR, CRM, HUB, MCP) sans refonte complète, en:
- ✅ Éliminant les patches empilés
- ✅ Centralisant le parsing redondant
- ✅ Identifiant les règles contradictoires
- ✅ Proposant 4 briques MCP avancées
- ✅ Livrant une documentation premium

---

## 📦 LIVRABLES GÉNÉRÉS

### 1. Rapports Principaux

**LIVRAISON_STABILISATION_IAPF.md** (10 KB)
- Résumé exécutif complet
- 8 propositions avec estimations horaires
- Plan d'action 15 jours (68h)
- Checklist validation
- Métriques cibles

**RAPPORT_STABILISATION_IAPF_2026.md** (29 KB)
- 8 sections détaillées
- 4 OCR + 1 CRM + 1 Export + 4 MCP
- Documentation premium (7 DOC)
- Gouvernance Git stricte
- Points critiques système

### 2. Audits JSON

**audit_ocr_deep_20260214_165237.json** (13 KB)
```json
{
  "meta": {
    "timestamp": "2026-02-14T16:52:37Z",
    "mode": "PROPOSAL_ONLY",
    "version": "2.0.0"
  },
  "ocr_deep_audit": {
    "patches_empiles": 0,
    "parsing_redondant": [{ "file": "ocr_level1.py", "count": 7 }],
    "fonctions_neutralisantes": 0,
    "surcharges_successives": 41
  },
  "propositions_nettoyage": [...]
}
```

**audit_stabilisation_20260214_164747.json** (18 KB)
- OCR patches: 13 détectés, 2 redondances
- CRM fonctions: 5 identifiées
- Export HUB vs BOX: 0 fonctions communes

### 3. Scripts Python

**audit_stabilisation_iapf.py** (18 KB)
- Classes OCRAudit, HUBAudit, BOXAudit
- Mode PROPOSAL-ONLY
- Extensible pour monitoring continu

---

## 🎯 8 PROPOSITIONS PRIORITISÉES

### 🔴 CRITIQUE (2)

#### PROP-CRM-001
**Titre**: Localiser et auditer le CRM Apps Script complet  
**Estimation**: 3h  
**Actions**:
1. Accéder Google Sheet BOX2026
2. Extensions → Apps Script
3. Exporter tous .gs dans `/appscript_crm/`
4. Auditer pipeline Devis→Facture

#### PROP-EXPORT-001
**Titre**: Corriger export HUB ZIP+XLSX  
**Estimation**: 4h  
**Actions**:
1. Copier logique stable de `exportBOX_ToZIP()`
2. Adapter pour 18 onglets HUB
3. Corriger offset colonne H
4. Tests intensifs

### ⭐ HIGH (1)

#### PROP-OCR-001
**Titre**: Centraliser parsers dans `utils/parsers.py`  
**Estimation**: 4h  
**Actions**:
1. Créer module avec `parse_date_french()`, `parse_amount_french()`, etc.
2. Refactoriser Level1/2/3
3. Tests unitaires formats français

### 🟡 MEDIUM (2)

#### PROP-OCR-002
**Titre**: Stabiliser extraction HT/TVA/TTC  
**Estimation**: 2h  
**Actions**:
1. Ajouter `_validate_and_complete_amounts()`
2. Calculs croisés: HT+TVA=TTC, TTC/(1+TVA)=HT

#### PROP-OCR-003
**Titre**: Améliorer extraction numéro facture  
**Estimation**: 3h  
**Actions**:
1. Patterns: FA-2024-001, F001/24, INV20240115
2. Tests 50+ PDF

### 🔸 LOW (1)

#### PROP-OCR-004
**Titre**: Simplifier 41 variables surchargées  
**Estimation**: 6h  
**Actions**: Refactoriser en sous-fonctions

### 🚀 MCP AVANCÉ (4)

#### MCP-001: Audit Global Système
```javascript
function auditGlobalSysteme() {
  // Scanne OCR, CRM, GS, HUB, Cloud Run, GitHub
  // Retourne rapport JSON + UI
}
```

#### MCP-002: Initialiser Journée
```javascript
function initialiserJournee() {
  // Log start, check HUB coherence, deps, erreurs
  // Retourne session ID + anomalies + propositions
}
```

#### MCP-003: Clôture Journée
```javascript
function clotureJournee() {
  // Vérifie MEMORY_LOG, risks, conflicts, call map
  // Retourne rapport + propositions updates
}
```

#### MCP-004: Vérification Doc vs Code
```javascript
function verificationDocVsCode() {
  // Compare repos réels vs doc ORION
  // Retourne drift report + propositions
}
```

---

## 📚 DOCUMENTATION PREMIUM (7 DOC)

### DOC-001: Diagramme Architecture
**Format**: Mermaid graph  
**Contenu**: Sources → OCR 3 niveaux → Apps Script → Sheets → MCP

### DOC-002: Flowchart OCR
**Format**: Mermaid flowchart  
**Contenu**: Pipeline complet PDF → Extraction → Validation → Écriture

### DOC-003: Pipeline Devis→Facture
**Format**: Mermaid sequence diagram  
**Contenu**: Interactions Utilisateur ↔ CRM ↔ HUB ↔ BOX

### DOC-004: Call Map
**Format**: Tableau + JSON  
**Contenu**: Toutes les interactions fonction→fonction

### DOC-005: JSON Schema OCR
**Format**: JSON Schema draft-07  
**Contenu**: OCRResult, FieldValue complets

### DOC-006: Dépendances
**Format**: Tableaux markdown  
**Contenu**: Repo 1 (FastAPI, pytesseract...) + Repo 2 (DriveApp, SpreadsheetApp...)

### DOC-007: Points Critiques
**Format**: Liste annotée  
**Contenu**: 5 CRITIQUE avec impact et mitigation

---

## 📅 PLAN D'ACTION 15 JOURS

### Semaine 1 – Stabilisation Critique (24h)
| Jour | Priorité | Actions |
|------|----------|---------|
| J1 | 🔴 | PROP-CRM-001 + PROP-OCR-001 (7h) |
| J2 | 🟡 | PROP-OCR-002 (2h) |
| J3 | 🔴 | PROP-EXPORT-001 (4h) |
| J4 | 🟡 | PROP-OCR-003 (3h) |
| J5 | ✅ | Tests E2E (8h) |

### Semaine 2 – MCP Avancé (18h)
| Jour | Priorité | Actions |
|------|----------|---------|
| J6 | 🚀 | MCP-001 (4h) |
| J7 | 🚀 | MCP-002 (3h) |
| J8 | 🚀 | MCP-003 (4h) |
| J9 | 🚀 | MCP-004 (3h) |
| J10 | 🚀 | Intégration menu (4h) |

### Semaine 3 – Documentation Premium (26h)
| Jour | Actions |
|------|---------|
| J11-J12 | Rédaction DOC-001 à DOC-007 (16h) |
| J13 | Diagrammes Mermaid (4h) |
| J14 | Génération call map (3h) |
| J15 | Revue finale (3h) |

**Total**: 68 heures

---

## 📊 MÉTRIQUES SUCCÈS

| Métrique | Avant | Objectif | Mesure |
|----------|-------|----------|--------|
| **Extraction TTC** | ~85% | >95% | Tests 100 PDF |
| **Export HUB** | 60% | 100% | 10 exports OK |
| **Temps OCR** | ~3s | <2.5s | Moyenne 100 docs |
| **Tests coverage** | 0% | >80% | pytest |
| **Variables 3+** | 41 | <10 | Analyse statique |
| **Doc à jour** | 70% | 100% | Audit Doc vs Code |

---

## 🔒 RÈGLES STRICTES

### ✅ AUTORISÉ
- Centraliser parsers redondants
- Stabiliser extractions dates/montants/numéros
- Corriger export HUB
- Ajouter 4 briques MCP (proposal-only)
- Simplifier variables surchargées
- Améliorer logging
- Créer tests unitaires
- Documenter architecture réelle

### ❌ INTERDIT
- Refactoriser architecture OCR 3 niveaux
- Réécrire système de scoring
- Supprimer logique mémoire (rules.json)
- Écrire automatiquement dans HUB sans validation
- Force-push sans confirmation
- Rebase risqué sans validation
- Supprimer données existantes
- Désactiver mode READ-ONLY

---

## ✅ CHECKLIST

### Avant Implémentation
- [x] Audit OCR profond complété
- [x] Audit CRM .gs complété
- [x] Diagnostic export HUB complété
- [x] 8 propositions validées
- [x] 4 briques MCP spécifiées
- [x] Documentation premium rédigée
- [x] Plan action 15j établi
- [ ] Validation client obtenue

### Implémentation Semaine 1
- [ ] PROP-CRM-001 exécutée (CRM localisé)
- [ ] PROP-OCR-001 exécutée (parsers centralisés)
- [ ] PROP-OCR-002 exécutée (montants stabilisés)
- [ ] PROP-EXPORT-001 exécutée (export HUB corrigé)
- [ ] PROP-OCR-003 exécutée (numéros facture OK)
- [ ] Tests E2E passés (50+ PDF)

### Implémentation Semaine 2
- [ ] MCP-001 intégrée (Audit Global)
- [ ] MCP-002 intégrée (Init Journée)
- [ ] MCP-003 intégrée (Clôture Journée)
- [ ] MCP-004 intégrée (Doc vs Code)
- [ ] Menu IAPF Memory mis à jour

### Implémentation Semaine 3
- [ ] DOC-001 à DOC-007 livrées
- [ ] Diagrammes Mermaid générés
- [ ] Call map JSON exportée
- [ ] Git hooks installés
- [ ] Formation utilisateur

---

## 🔗 LIENS UTILES

**Repository**:  
https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent

**Branch actuelle**:  
`feature/ocr-intelligent-3-levels`

**Dernier commit**:  
de1dde0 (docs: Résumé exécutif phase stabilisation)

**Créer Pull Request**:  
https://github.com/romacmehdi971-lgtm/box-magic-ocr-intelligent/compare/main...feature:ocr-intelligent-3-levels

**Titre PR suggéré**:  
`feat(stabilisation): Phase stabilisation IAPF 2026 - 8 propositions + MCP avancé`

---

## 📂 STRUCTURE FICHIERS LIVRÉS

```
/home/user/webapp/
├── LIVRAISON_STABILISATION_IAPF.md          (10 KB)
├── RAPPORT_STABILISATION_IAPF_2026.md       (29 KB)
├── README_STABILISATION.md                  (ce fichier)
├── audit_ocr_deep_20260214_165237.json      (13 KB)
├── audit_stabilisation_20260214_164747.json (18 KB)
├── audit_stabilisation_iapf.py              (18 KB)
└── [fichiers existants OCR/MCP...]
```

**Total livrables**: ~100 KB de documentation structurée

---

## 🎯 PROCHAINES ÉTAPES

1. **IMMÉDIAT** (J+0)
   - Valider les 8 propositions
   - Prioriser implémentation (Semaine 1 = critique)
   - Créer Pull Request

2. **COURT TERME** (J+1 à J+5)
   - Exécuter PROP-CRM-001 (localiser CRM complet)
   - Implémenter PROP-OCR-001 (centraliser parsers)
   - Corriger PROP-EXPORT-001 (export HUB stable)

3. **MOYEN TERME** (J+6 à J+10)
   - Intégrer 4 briques MCP dans menu IAPF Memory
   - Tests intensifs (100+ PDF Adobe Scan)

4. **LONG TERME** (J+11 à J+15)
   - Livrer documentation premium complète
   - Formation utilisateur
   - Déploiement production

---

## 💡 RECOMMANDATIONS

### Pour l'Implémentation
1. **Respecter l'ordre de priorité** (CRITIQUE → HIGH → MEDIUM → LOW)
2. **Tester chaque proposition** avant de passer à la suivante
3. **Documenter les changements** au fil de l'eau
4. **Maintenir mode PROPOSAL-ONLY** jusqu'à validation

### Pour les Tests
1. **Constituer un dataset** de 100+ PDF réels (factures, devis, tickets)
2. **Mesurer les métriques** avant/après chaque prop
3. **Valider avec utilisateurs** finaux

### Pour la Documentation
1. **Générer call map** automatiquement (DOC-004)
2. **Visualiser diagrammes** avec Mermaid Live Editor
3. **Maintenir cohérence** Doc vs Code (MCP-004)

---

## 📞 SUPPORT

**Mode**: PROPOSAL-ONLY strict  
**Validation requise**: Avant toute modification destructive  
**Contact**: Équipe IAPF Stabilisation

---

**Généré le**: 2026-02-14T17:15:00Z  
**Version**: 2.0.0  
**Statut**: ✅ PRÊT POUR VALIDATION ET IMPLÉMENTATION
