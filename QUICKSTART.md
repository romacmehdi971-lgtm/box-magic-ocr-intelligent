# QUICKSTART — BOX MAGIC OCR

## ⚡ Démarrage en 3 minutes

### 1. Installation (1 minute)

```bash
# Cloner le dépôt
git clone https://github.com/YOUR_ORG/box-magic-ocr-intelligent.git
cd box-magic-ocr-intelligent

# Installer les dépendances
pip install -r requirements.txt

# Installer Tesseract (OCR) - Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-fra

# macOS
# brew install tesseract tesseract-lang
```

### 2. Configuration (1 minute)

```bash
# Éditer la configuration
nano config/config.yaml
```

Modifier :
- `google_sheets.spreadsheet_id` → Votre ID Google Sheets
- Placer vos credentials dans `config/google_credentials.json`

**Pour tester sans Google Sheets :**
```yaml
google_sheets:
  enabled: false  # Mode dry-run
```

### 3. Premier test (1 minute)

```python
from ocr_engine import OCREngine

# Initialiser
engine = OCREngine("config/config.yaml")

# Traiter un document
result = engine.process_document(
    file_path="votre_facture.pdf",
    source_entreprise="Martin's Traiteur"  # ou "auto-detect"
)

# Voir résultat
print(f"Type: {result.document_type}")
print(f"Niveau OCR: {result.level}")
print(f"Confiance: {result.confidence:.2%}")
print(f"Champs extraits: {len(result.fields)}")

for field_name, field_value in result.fields.items():
    print(f"  {field_name}: {field_value.value}")
```

## ✅ C'est prêt !

Le document est automatiquement traité et les résultats écrits dans Google Sheets :
- ✅ INDEX GLOBAL
- ✅ CRM (si nouveau client)
- ✅ COMPTABILITÉ
- ✅ LOG SYSTEM

## 🎯 Les 3 niveaux en action

### Level 1 (80% des cas) - Rapide
```
[2026-01-12 10:30:45] INFO Starting OCR Level 1
[2026-01-12 10:30:46] INFO Document type: facture (confidence: 0.92)
[2026-01-12 10:30:46] INFO OCR Level 1 sufficient, stopping here
```
⚡ **< 2 secondes**

### Level 2 (15% des cas) - Approfondi
```
[2026-01-12 10:35:12] INFO Escalating to OCR Level 2
[2026-01-12 10:35:14] INFO Field improved: tva_rate (0.45 → 0.88)
[2026-01-12 10:35:15] INFO OCR Level 2 sufficient, stopping here
```
⏱️ **< 5 secondes**

### Level 3 (5% des cas) - Mémoire
```
[2026-01-12 10:40:20] WARNING Escalating to OCR Level 3 (RARE)
[2026-01-12 10:40:25] INFO Memory rule created: rule_20260112_001
[2026-01-12 10:40:25] INFO Future similar documents will bypass OCR1/OCR2
```
🧠 **Crée une règle réutilisable**

## 📚 Documentation complète

- **[README.md](README.md)** - Vue d'ensemble et architecture
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Détails techniques
- **[INTEGRATION.md](INTEGRATION.md)** - Guide d'intégration complet
- **[examples/](examples/)** - Exemples d'utilisation

## 🔧 Configuration entreprises

Éditer `config/entreprises.yaml` :

```yaml
entreprises:
  - name: "Votre Entreprise"
    siret: "12345678900012"
    address: "123 rue Example"
    phone: "01 23 45 67 89"
    iban: "FR76..."
    tva: "FR123..."
    
    identity:
      logo_patterns:
        - "Votre Entreprise"
      footer_patterns:
        - "votre-site.fr"
```

## 🧪 Tests

```bash
# Tests basiques
python tests/test_integration.py

# Avec pytest
pytest tests/ -v

# Exemple d'utilisation
python examples/example_pipeline.py
```

## 📊 Voir les statistiques

```python
from ocr_engine import OCREngine

engine = OCREngine("config/config.yaml")
stats = engine.get_statistics()

print(f"Règles mémoire: {stats['memory_rules']['total_rules']}")
print(f"Entreprises: {stats['config']['entreprises_count']}")
```

## 🚨 Troubleshooting

### Erreur "tesseract not found"
```bash
# Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-fra

# macOS
brew install tesseract tesseract-lang
```

### Erreur Google Sheets
Vérifier :
1. Credentials dans `config/google_credentials.json`
2. API Google Sheets activée
3. `spreadsheet_id` correct dans `config.yaml`

Ou désactiver :
```yaml
google_sheets:
  enabled: false
```

### Document non reconnu
- Vérifier qualité du scan (min 300 DPI)
- Essayer avec `source_entreprise="auto-detect"`
- Consulter les logs pour détails

## 🎓 Aller plus loin

### Intégration Google Drive
Voir [INTEGRATION.md](INTEGRATION.md#option-1--intégration-google-drive)

### API REST
Voir [INTEGRATION.md](INTEGRATION.md#option-2--intégration-apiwebhook)

### Traitement par lot
Voir [INTEGRATION.md](INTEGRATION.md#option-3--traitement-par-lot-cronscheduler)

---

## 🎯 Résumé : 3 commandes

```bash
# 1. Installer
pip install -r requirements.txt && sudo apt-get install tesseract-ocr

# 2. Configurer
nano config/config.yaml  # Éditer spreadsheet_id

# 3. Utiliser
python -c "from ocr_engine import OCREngine; print(OCREngine('config/config.yaml').process_document('facture.pdf', 'auto-detect'))"
```

**C'est tout ! 🚀**

---

**BOX MAGIC 2026** - IA PROCESS FACTORY
