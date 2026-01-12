# CHANGELOG

Toutes les modifications notables de ce projet seront documentées dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [1.0.0] - 2026-01-12

### Ajouté

#### Architecture Principale
- ✅ Moteur OCR intelligent à 3 niveaux (Level 1 → 2 → 3)
- ✅ Système de mémoire avec règles réutilisables
- ✅ Connecteur Google Sheets (INDEX, CRM, COMPTABILITÉ, LOGS)
- ✅ Chargeur de documents multi-format (PDF, images)

#### OCR Level 1 - Rapide & Stable
- Détection type document (facture, devis, ticket, reçu, BL)
- Extraction dates (émission, échéance)
- Extraction montants (HT, TVA, TTC)
- Détection TVA simple
- Extraction émetteur/destinataire
- Score de confiance par champ
- Séparation stricte entreprise source / client / fournisseur
- Objectif : 80% des documents en < 2 secondes

#### OCR Level 2 - Approfondi
- Analyse contextuelle avancée
- Recherche croisée d'informations
- Amélioration ciblée des champs faibles
- Préservation résultats OCR Level 1
- Calculs montants manquants (HT ↔ TVA ↔ TTC)
- Validation croisée des champs

#### OCR Level 3 - Contrôle & Mémoire (RARE)
- Vérification cohérence globale
- Correction champs incorrects
- Complétion champs absents
- **CRÉATION RÈGLE MÉMOIRE réutilisable**
- Analyse pattern document
- Élimination apprentissage répétitif

#### Système de Mémoire
- Stockage règles JSON
- Recherche règles applicables par pattern
- Score de correspondance document/règle
- Statistiques d'utilisation
- Fusion règles similaires
- Import/Export règles

#### Connecteurs
- Google Sheets API complet
- Écriture automatique dans 4 feuilles
- Mode dry-run pour tests
- Test de connexion

#### Multi-entreprise
- Configuration YAML des entreprises
- Détection automatique via patterns
- Séparation stricte données entreprise/client
- Support illimité d'entreprises

#### Utilitaires
- Logger structuré avec niveaux
- Validateurs de cohérence
- Types de documents (enum)
- Gestion erreurs robuste

#### Documentation
- README.md complet avec architecture
- ARCHITECTURE.md technique détaillée
- INTEGRATION.md pas à pas
- Exemples d'utilisation commentés
- Configuration YAML documentée

#### Tests
- Tests d'intégration de base
- Tests système de mémoire
- Tests validateurs
- Infrastructure pytest

### Principes de Conception

#### ✅ OBLIGATOIRE
- Logs détaillés et lisibles
- Décisions explicables
- OCR progressif (1 → 2 → 3)
- Apprentissage rare et utile
- Intégration sans casser l'existant
- Score de confiance par champ

#### ❌ INTERDIT
- Normalisation agressive prématurée
- Renommage automatique des fichiers
- Anti-doublon bloquant
- Boucles infinies
- Ré-apprentissage permanent inutile
- Pollution données entreprise/client

### Objectifs Atteints

✅ **Stable** - Pas de crash, pas de boucle  
✅ **Intelligent** - Apprend des cas complexes  
✅ **Auto-améliorant** - Crée des règles réutilisables  
✅ **Multi-entreprise** - Gère plusieurs sociétés proprement  
✅ **Sans boucle** - OCR3 élimine les cas répétitifs  
✅ **Sans nuits blanches** - Logs clairs, debuggable  

### Types de Documents Supportés

- Factures (clients/fournisseurs)
- Devis
- Tickets de caisse
- Reçus CB
- Notes de frais
- Bons de livraison
- Documents scannés/photos

### Formats Supportés

- PDF textuels (PyPDF2, pdfplumber)
- PDF scannés (OCR Tesseract)
- Images (PNG, JPG, TIFF)
- Texte brut

## [Unreleased]

### À venir
- Support Google Vision API pour OCR avancé
- Support AWS Textract
- Dashboard web de monitoring
- API REST complète
- Webhooks pour intégrations externes
- Support multi-langue
- Export comptabilité (FEC)

---

**BOX MAGIC 2026** - IA PROCESS FACTORY
