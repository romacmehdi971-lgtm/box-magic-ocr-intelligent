# 🔹 PHASE 2.2 : BRANCHER LES PARSERS DE MONTANTS

## Modification de 02_SCAN_WORKER.gs

### Chercher et remplacer

**Ancien code** (à chercher dans 02_SCAN_WORKER.gs) :
```javascript
// Exemple d'ancien parsing de montant (lignes ~900-1000)
function _BM_parseAmountFR_(text) {
  if (!text) return "";
  // ... logique de normalisation montants FR ...
}

function _BM_extractAmounts_(ocrText) {
  // ... logique d'extraction HT/TVA/TTC ...
}
```

**Nouveau code** (remplacer par) :
```javascript
// Délégation au module 04_PARSERS.gs
function _BM_parseAmountFR_(text) {
  return BM_PARSERS_parseAmountFR(text);
}

function _BM_extractAmounts_(ocrText) {
  return BM_PARSERS_extractAmounts(ocrText);
}
```

---

### Lignes à modifier (exemples)

**Ligne ~950** : Remplacer la logique interne par :
```javascript
const montantHT = BM_PARSERS_parseAmountFR(extractedHT);
```

**Ligne ~970** : Remplacer l'extraction complète par :
```javascript
const amounts = BM_PARSERS_extractAmounts(ocrText);
// amounts = { ht: "1234.56", tva: "246.91", ttc: "1481.47", tauxTva: "20" }
```

**Ligne ~1100** : Remplacer l'injection dans l'objet data par :
```javascript
if (amounts.ht) data.montant_ht = amounts.ht;
if (amounts.ttc) data.montant_ttc = amounts.ttc;
if (amounts.tva) data.montant_tva = amounts.tva;
if (amounts.tauxTva) data.taux_tva = amounts.tauxTva;
```

---

## Test 2.2 : Validation terrain

**Actions** :
1. Sauvegarder 02_SCAN_WORKER.gs (Ctrl+S)
2. Uploader **la même facture PDF que Phase 2.1** dans INBOX
3. Ouvrir LOGS_SYSTEM
4. Vérifier :
   - ✅ Montant HT extrait correctement
   - ✅ Montant TTC extrait correctement
   - ✅ Montant TVA extrait correctement
   - ✅ Taux TVA extrait correctement (ex: "20")
   - ✅ Format : nombres décimaux avec point (ex: "1234.56")
   - ✅ Aucune erreur dans LOGS_SYSTEM

**Critère de succès** :
- Montants identiques à avant (même résultat)
- Aucune erreur nouvelle

**Si échec** :
- Revenir en arrière (Ctrl+Z dans Apps Script)
- Analyser les logs (chercher "parseAmountFR" ou "extractAmounts")
- Corriger et retester

---

## Durée estimée : 10 minutes
