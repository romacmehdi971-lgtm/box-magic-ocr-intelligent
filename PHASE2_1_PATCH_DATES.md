# 🔹 PHASE 2.1 : BRANCHER LES PARSERS DE DATES

## Modification de 02_SCAN_WORKER.gs

### Chercher et remplacer

**Ancien code** (à chercher dans 02_SCAN_WORKER.gs) :
```javascript
// Exemple d'ancien parsing de date (lignes ~800-850)
function _BM_parseDateFR_(text) {
  if (!text) return "";
  // ... logique de parsing ...
}
```

**Nouveau code** (remplacer par) :
```javascript
// Délégation au module 04_PARSERS.gs
function _BM_parseDateFR_(text) {
  return BM_PARSERS_parseDateFR(text);
}
```

---

### Lignes à modifier (exemples)

**Ligne ~820** : Remplacer la logique interne par :
```javascript
const dateFacture = BM_PARSERS_parseDateFR(ocrText);
```

**Ligne ~950** : Remplacer la logique interne par :
```javascript
const dateEcheance = BM_PARSERS_parseDateFR(extractedText);
```

---

## Test 2.1 : Validation terrain

**Actions** :
1. Sauvegarder 02_SCAN_WORKER.gs (Ctrl+S)
2. Uploader **une facture PDF** dans INBOX
3. Ouvrir LOGS_SYSTEM
4. Vérifier :
   - ✅ Date facture extraite correctement
   - ✅ Format date : YYYY-MM-DD
   - ✅ Aucune erreur dans LOGS_SYSTEM

**Critère de succès** :
- Date facture identique à avant (même résultat)
- Aucune erreur nouvelle

**Si échec** :
- Revenir en arrière (Ctrl+Z dans Apps Script)
- Analyser les logs
- Corriger et retester

---

## Durée estimée : 10 minutes
