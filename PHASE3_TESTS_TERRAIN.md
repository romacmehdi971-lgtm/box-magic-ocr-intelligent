# 🔹 PHASE 3 : TESTS TERRAIN COMPLETS

## Objectif
Valider que les nouveaux parsers centralisés fonctionnent **aussi bien ou mieux** que l'ancien code.

---

## 📋 Tests obligatoires

### Test 3.1 : PDF classique
**Document** : Facture PDF standard avec texte numérique
**Exemple** : `Facture_2025-01-15_ACME_Corp_FA2025001_1234.56.pdf`

**Actions** :
1. Uploader le PDF dans INBOX
2. Attendre traitement (30-60 secondes)
3. Ouvrir LOGS_SYSTEM
4. Ouvrir INDEX_FACTURES

**Vérifications** :
- ✅ Date facture extraite : format YYYY-MM-DD
- ✅ Numéro facture extrait : alphanumérique
- ✅ Montant HT extrait : format décimal avec point
- ✅ Montant TTC extrait : format décimal avec point
- ✅ Montant TVA extrait : format décimal avec point
- ✅ Taux TVA extrait : "20" ou "10" ou "5.5"
- ✅ Aucune erreur dans LOGS_SYSTEM (niveau ERROR)
- ✅ Ligne créée dans INDEX_FACTURES

**Critère de succès** : Tous les champs extraits correctement (comme avant ou mieux)

---

### Test 3.2 : Image scannée (photo mobile)
**Document** : Photo de facture prise avec smartphone (orientation quelconque)
**Exemple** : `photo_facture_20250115.jpg`

**Actions** :
1. Uploader l'image dans INBOX
2. Attendre traitement (60-120 secondes, normalization + OCR)
3. Ouvrir LOGS_SYSTEM
4. Ouvrir INDEX_FACTURES

**Vérifications** :
- ✅ Date facture extraite (tolérance ±1 jour si OCR imparfait)
- ✅ Numéro facture extrait (au moins 70% des caractères)
- ✅ Montant TTC extrait (tolérance ±5% si OCR imparfait)
- ✅ Niveau OCR utilisé : 2 (Contextual) ou 3 (Memory)
- ✅ Aucune erreur bloquante dans LOGS_SYSTEM
- ✅ Ligne créée dans INDEX_FACTURES

**Critère de succès** : Extraction acceptable malgré qualité image variable

---

### Test 3.3 : Devis CRM généré
**Document** : Devis PDF généré depuis le CRM
**Exemple** : Créer un nouveau devis dans le CRM, puis générer le PDF

**Actions** :
1. Créer un devis dans le CRM (client + lignes + montants)
2. Générer le PDF
3. Vérifier que le PDF est bien dans le bon dossier
4. Attendre traitement automatique
5. Ouvrir LOGS_SYSTEM
6. Ouvrir INDEX_GLOBAL (ou équivalent)

**Vérifications** :
- ✅ Devis traité sans erreur
- ✅ Index global cohérent (pas de régression sur autres documents)
- ✅ Date devis extraite
- ✅ Montant total extrait
- ✅ Aucune erreur dans LOGS_SYSTEM

**Critère de succès** : Devis traité normalement, zéro régression sur index global

---

## 📊 Tableau de suivi des tests

| Test | Document | Date extraite | N° facture | Montant TTC | Erreurs | Statut |
|------|----------|---------------|------------|-------------|---------|--------|
| 3.1  | PDF classique | ? | ? | ? | ? | ⏳ À faire |
| 3.2  | Image scannée | ? | ? | ? | ? | ⏳ À faire |
| 3.3  | Devis CRM | ? | ? | ? | ? | ⏳ À faire |

**Remplir ce tableau après chaque test** (remplacer ? par valeurs réelles)

---

## ✅ Critère de validation Phase 3

**Tous les tests passent** : ✅ Passer à Phase 4 (nettoyage legacy)

**Au moins un test échoue** : ❌ Analyser les logs, corriger, retester

---

## Durée estimée : 20 minutes (3 tests × ~7 min chacun)
