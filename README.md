# BOX MAGIC OCR INTELLIGENT 2026

## 🎯 OBJECTIF

Brique OCR modulaire intelligente à 3 niveaux pour le traitement automatisé de documents comptables et commerciaux.

**RÈGLE ABSOLUE** : Ce module est une BRIQUE INTÉGRABLE, pas une refonte globale.

## 🏗️ ARCHITECTURE GLOBALE

```
┌─────────────────────────────────────────────────────────────┐
│                    PIPELINE EXISTANT                         │
│              (Google Drive + Google Sheets)                  │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Document PDF/Image
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   OCR ENGINE (Point d'entrée)                │
│                  - Détection entreprise                       │
│                  - Routage intelligent                        │
│                  - Gestion logs                              │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
    ┌─────────┐           ┌──────────┐
    │  OCR 1  │──Échec──→ │  OCR 2   │
    │ RAPIDE  │           │ APPROFONDI│
    └────┬────┘           └────┬─────┘
         │                     │
         │ 80% OK              │ Échec rare
         │                     ▼
         │              ┌──────────────┐
         │              │    OCR 3     │
         │              │ CONTRÔLE +   │
         │              │ MÉMOIRE      │
         │              └──────┬───────┘
         │                     │
         │                     │ Crée règle
         │                     ▼
         └──────────────→ ┌──────────────┐
                          │ MEMORY STORE │
                          │ (Règles AI)  │
                          └──────┬───────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────┐
│              ÉCRITURE GOOGLE SHEETS                          │
│  - INDEX GLOBAL                                              │
│  - CRM                                                       │
│  - COMPTABILITÉ                                              │
│  - LOG SYSTEM                                                │
└─────────────────────────────────────────────────────────────┘
```

## 📋 NIVEAUX OCR DÉTAILLÉS

### 🔹 OCR NIVEAU 1 — RAPIDE & STABLE
**Objectif** : Traiter 80% des documents standards

**Fonctions** :
- ✅ Détection type document (facture, devis, ticket, reçu, BL)
- ✅ Extraction dates (émission, échéance, paiement)
- ✅ Montants (HT / TVA / TTC)
- ✅ TVA si unique et évidente
- ✅ Émetteur / Destinataire (logique classique)
- ✅ Score de confiance par champ
- ✅ Séparation ENTREPRISE SOURCE / CLIENT / FOURNISSEUR

**Sortie** :
```json
{
  "level": 1,
  "confidence": 0.85,
  "type": "facture",
  "entreprise_source": "Martin's Traiteur",
  "client": {
    "name": "Restaurant Le Gourmet",
    "confidence": 0.9
  },
  "fields": {
    "date": {"value": "2026-01-10", "confidence": 0.95},
    "total_ttc": {"value": 1200.00, "confidence": 0.90}
  },
  "needs_level2": false
}
```

### 🔹 OCR NIVEAU 2 — ANALYSE APPROFONDIE
**Déclenchement** :
- Confiance OCR1 < seuil (par défaut 0.7)
- Champs manquants critiques
- Ambiguïtés détectées

**Fonctions** :
- ✅ Analyse contextuelle avancée
- ✅ Recherche croisée d'informations
- ✅ Amélioration champ par champ
- ✅ Préservation des champs fiables d'OCR1
- ✅ Calculs et vérifications de cohérence

**Sortie** :
```json
{
  "level": 2,
  "confidence": 0.78,
  "improved_fields": ["tva", "client_siret"],
  "needs_level3": false
}
```

### 🔹 OCR NIVEAU 3 — CONTRÔLE & MÉMOIRE (RARE)
**Déclenchement** :
- OCR2 insuffisant
- Cas nouveau/inconnu
- Demande explicite de validation

**Fonctions** :
- ✅ Vérification cohérence globale
- ✅ Correction champs FAUX
- ✅ Complétion champs ABSENTS
- ✅ Création RÈGLE MÉMOIRE réutilisable
- ✅ Stockage dans AI Memory

**Sortie** :
```json
{
  "level": 3,
  "confidence": 0.92,
  "corrections": ["client_name", "tva_rate"],
  "rule_created": {
    "id": "rule_20260112_001",
    "pattern": "Facture METRO format spécifique",
    "conditions": ["footer_contains:METRO", "siret:123456789"],
    "actions": ["apply_tva_10", "extract_client_from_line_3"]
  }
}
```

## 🗂️ STRUCTURE DU PROJET

```
box-magic-ocr-intelligent/
├── README.md                      # Documentation principale
├── ARCHITECTURE.md                # Architecture détaillée
├── INTEGRATION.md                 # Guide d'intégration
├── requirements.txt               # Dépendances Python
├── config/
│   ├── config.yaml               # Configuration globale
│   └── entreprises.yaml          # Configuration multi-entreprises
├── ocr_engine.py                 # 🎯 POINT D'ENTRÉE PRINCIPAL
├── levels/
│   ├── __init__.py
│   ├── ocr_level1.py            # OCR Niveau 1 - Rapide
│   ├── ocr_level2.py            # OCR Niveau 2 - Approfondi
│   └── ocr_level3.py            # OCR Niveau 3 - Mémoire
├── memory/
│   ├── __init__.py
│   ├── rule_engine.py           # Gestion des règles
│   └── ai_memory.py             # Stockage intelligent
├── connectors/
│   ├── __init__.py
│   ├── google_sheets.py         # Connecteur Google Sheets
│   └── document_loader.py       # Chargement documents
├── utils/
│   ├── __init__.py
│   ├── logger.py                # Système de logs
│   ├── validators.py            # Validations
│   └── document_types.py        # Types de documents
├── tests/
│   └── test_integration.py      # Tests d'intégration
└── examples/
    ├── example_pipeline.py       # Exemple d'utilisation
    └── sample_config.yaml        # Configuration exemple
```

## 🚀 UTILISATION RAPIDE

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

1. Copier `config/config.yaml.example` vers `config/config.yaml`
2. Configurer vos entreprises dans `config/entreprises.yaml`
3. Configurer les credentials Google Sheets

### Intégration dans le pipeline existant

```python
from ocr_engine import OCREngine

# Initialisation
ocr = OCREngine(config_path="config/config.yaml")

# Traitement d'un document
result = ocr.process_document(
    file_path="document.pdf",
    source_entreprise="Martin's Traiteur"
)

# Résultat automatiquement écrit dans Google Sheets
# - INDEX GLOBAL
# - CRM (si nouveau client détecté)
# - COMPTABILITÉ
# - LOG SYSTEM
```

## 📊 GOOGLE SHEETS EXISTANT (UTILISÉ, PAS MODIFIÉ)

### CONFIG
Paramètres globaux + entreprises

### INDEX GLOBAL
Chaque document traité = 1 ligne
- ID document
- Type
- Date traitement
- Entreprise source
- Client/Fournisseur
- Montants
- Statut OCR (niveau utilisé)
- Confiance

### CRM
Clients détectés / enrichis
- Nom
- SIRET
- Adresse
- Contact
- Source (détection OCR)

### COMPTABILITÉ
Factures, tickets, paiements
- Référence
- Type écriture
- Montants HT/TVA/TTC
- Comptes comptables

### LOG SYSTEM
Logs techniques uniquement
- Timestamp
- Niveau OCR
- Décisions prises
- Erreurs

## 🏢 MULTI-ENTREPRISE

Le système gère plusieurs sociétés :
- Martin's Traiteur (Cyril Martins)
- MT Production
- Autres futures

**RÈGLE CRITIQUE** : Les infos de l'entreprise SOURCE ne polluent JAMAIS les champs CLIENT/FOURNISSEUR.

Configuration entreprise :
```yaml
entreprises:
  - name: "Martin's Traiteur"
    siret: "12345678900012"
    address: "123 rue Example, 75001 Paris"
    phone: "01 23 45 67 89"
    iban: "FR76..."
    tva: "FR12345678900"
    identity:
      logo_patterns: ["martin", "traiteur"]
      footer_patterns: ["Cyril Martins"]
```

## 🔐 RÈGLES DE CONCEPTION

### ✅ OBLIGATOIRE
- Logs détaillés et lisibles
- Décisions explicables
- OCR progressif (1 → 2 → 3)
- Apprentissage rare et utile
- Intégration sans casser l'existant
- Score de confiance par champ

### ❌ INTERDIT
- Normalisation agressive prématurée
- Renommage automatique des fichiers
- Anti-doublon bloquant
- Boucles infinies
- Ré-apprentissage permanent inutile
- Pollution des données entreprise/client

## 📝 TYPES DE DOCUMENTS GÉRÉS

- ✅ Factures (clients/fournisseurs)
- ✅ Devis
- ✅ Tickets de caisse
- ✅ Reçus CB
- ✅ Notes de frais
- ✅ Bons de livraison
- ✅ Documents scannés/photos

Même logique, même pipeline.

## 🎯 OBJECTIF FINAL

Un OCR :
- ✅ **Stable** - Pas de crash, pas de boucle
- ✅ **Intelligent** - Apprend des cas complexes
- ✅ **Auto-améliorant** - Crée des règles réutilisables
- ✅ **Multi-entreprise** - Gère plusieurs sociétés proprement
- ✅ **Sans boucle** - OCR3 élimine les cas répétitifs
- ✅ **Sans nuits blanches** - Logs clairs, debuggable

## 📚 DOCUMENTATION COMPLÈTE

- [ARCHITECTURE.md](ARCHITECTURE.md) - Architecture technique détaillée
- [INTEGRATION.md](INTEGRATION.md) - Guide d'intégration pas à pas
- [MEMORY_SYSTEM.md](memory/README.md) - Système de mémoire et règles
- [API.md](API.md) - Documentation API complète

## 🤝 SUPPORT

Ce module est conçu pour être **stable et autonome**.

En cas de besoin :
1. Consulter les logs dans Google Sheets LOG SYSTEM
2. Vérifier la configuration dans CONFIG
3. Analyser les règles créées dans MEMORY STORE

---

**BOX MAGIC 2026** — IA PROCESS FACTORY
Version : 1.0.0
Date : Janvier 2026
