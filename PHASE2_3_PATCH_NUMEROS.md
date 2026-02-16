# 🔹 PHASE 2.3 : BRANCHER LES PARSERS DE NUMÉROS DE FACTURE

## Modification de 02_SCAN_WORKER.gs

### Chercher et remplacer

**Ancien code** (à chercher dans 02_SCAN_WORKER.gs) :
```javascript
// Exemple d'ancien parsing de numéro de facture (lignes ~750-800)
function _BM_extractInvoiceNumber_(ocrText) {
  if (!ocrText) return "";
  // ... logique d'extraction avec regex multiples ...
}
```

**Nouveau code** (remplacer par) :
```javascript
// Délégation au module 04_PARSERS.gs
function _BM_extractInvoiceNumber_(ocrText) {
  return BM_PARSERS_extractInvoiceNumber(ocrText);
}
```

---

### Lignes à modifier (exemples)

**Ligne ~780** : Remplacer la logique interne par :
```javascript
const numeroFacture = BM_PARSERS_extractInvoiceNumber(ocrText);
```

**Ligne ~1050** : Remplacer l'injection dans l'objet data par :
```javascript
if (numeroFacture) {
  data.numero_facture = numeroFacture;
} else {
  logAction("SCAN_WORKER", "Numéro facture non extrait", { ocrTextLength: ocrText.length }, "WARN");
}
```

---

## Test 2.3 : Validation terrain

**Actions** :
1. Sauvegarder 02_SCAN_WORKER.gs (Ctrl+S)
2. Uploader **la même facture PDF que Phase 2.1** dans INBOX
3. Ouvrir LOGS_SYSTEM
4. Vérifier :
   - ✅ Numéro facture extrait correctement
   - ✅ Format : chaîne alphanumérique (ex: "FA2025001")
   - ✅ Aucune erreur dans LOGS_SYSTEM

**Critère de succès** :
- Numéro facture identique à avant (même résultat)
- Aucune erreur nouvelle

**Si échec** :
- Revenir en arrière (Ctrl+Z dans Apps Script)
- Analyser les logs (chercher "extractInvoiceNumber")
- Corriger et retester

---

## Durée estimée : 10 minutes

---

## ✅ FIN DE PHASE 2 : BILAN

Après Phase 2.3, vous avez :
- ✅ Parsers de dates branchés et testés
- ✅ Parsers de montants branchés et testés
- ✅ Parsers de numéros de facture branchés et testés
- ✅ 02_SCAN_WORKER.gs délègue aux nouveaux modules
- ✅ Anciens parsers internes toujours présents (backup)

**Test global** :
- Uploader 3 factures différentes (PDF, image, devis CRM)
- Vérifier extraction complète (dates + montants + numéros)
- Vérifier LOGS_SYSTEM sans erreurs

**Durée totale Phase 2** : ~30 minutes
