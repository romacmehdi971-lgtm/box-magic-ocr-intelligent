# GUIDE D'INTÉGRATION — BOX MAGIC OCR

## 🎯 Objectif

Intégrer l'OCR Engine dans votre pipeline existant **sans casser l'existant**.

## 📋 Prérequis

### 1. Python 3.8+
```bash
python --version  # Doit être >= 3.8
```

### 2. Installation des dépendances

#### Installation minimale (texte uniquement)
```bash
pip install -r requirements.txt
```

#### Installation complète avec OCR
```bash
# Sur Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-fra poppler-utils

# Sur macOS
brew install tesseract tesseract-lang poppler

# Puis installer les dépendances Python
pip install -r requirements.txt
```

### 3. Configuration Google Sheets

1. Créer un projet Google Cloud
2. Activer l'API Google Sheets
3. Créer un compte de service
4. Télécharger les credentials JSON
5. Placer dans `config/google_credentials.json`

```bash
# Structure attendue
config/
  ├── config.yaml
  ├── entreprises.yaml
  └── google_credentials.json  # Vos credentials
```

## 🚀 Intégration Rapide (5 minutes)

### Étape 1 : Configuration

```bash
# Copier et éditer la configuration
cp config/config.yaml config/config.yaml.local
nano config/config.yaml.local
```

Modifier :
- `google_sheets.spreadsheet_id` : Votre ID de tableur
- `entreprises_config` : Vos entreprises

### Étape 2 : Test de connexion

```python
from ocr_engine import OCREngine

# Initialisation
engine = OCREngine(config_path="config/config.yaml.local")

# Test Google Sheets
if engine.sheets_connector:
    connected = engine.sheets_connector.test_connection()
    print(f"Google Sheets : {'✓ OK' if connected else '✗ Échec'}")
```

### Étape 3 : Premier document

```python
# Traiter un document
result = engine.process_document(
    file_path="chemin/vers/facture.pdf",
    source_entreprise="Martin's Traiteur"
)

print(f"Type : {result.document_type}")
print(f"Niveau : {result.level}")
print(f"Confiance : {result.confidence:.2%}")
```

✅ **Résultat automatiquement écrit dans Google Sheets !**

## 🔌 Points d'intégration

### Option 1 : Intégration Google Drive

```python
from ocr_engine import OCREngine

ocr = OCREngine("config/config.yaml")

def on_new_document_in_drive(file_path: str, metadata: dict):
    """
    Callback déclenché lors de l'ajout d'un document dans Drive
    """
    # Récupérer entreprise depuis metadata ou dossier
    entreprise = metadata.get('entreprise') or detect_from_folder(file_path)
    
    # Traiter
    result = ocr.process_document(file_path, entreprise)
    
    # Log
    logger.info(f"Document traité : {result.document_id} (Level {result.level})")
    
    return result

# Configuration du watcher Drive (selon votre implémentation)
# drive_watcher.on_new_file(on_new_document_in_drive)
```

### Option 2 : Intégration API/Webhook

```python
from flask import Flask, request, jsonify
from ocr_engine import OCREngine

app = Flask(__name__)
ocr = OCREngine("config/config.yaml")

@app.route('/ocr/process', methods=['POST'])
def process_document():
    """
    Endpoint API pour traiter un document
    
    Body JSON :
    {
      "file_path": "/path/to/document.pdf",
      "entreprise": "Martin's Traiteur",
      "options": {}
    }
    """
    data = request.json
    
    try:
        result = ocr.process_document(
            file_path=data['file_path'],
            source_entreprise=data['entreprise'],
            options=data.get('options', {})
        )
        
        return jsonify({
            'success': True,
            'document_id': result.document_id,
            'level': result.level,
            'confidence': result.confidence,
            'fields': {k: v.value for k, v in result.fields.items()}
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(port=5000)
```

### Option 3 : Traitement par lot (Cron/Scheduler)

```python
import os
from pathlib import Path
from ocr_engine import OCREngine

def process_pending_documents():
    """
    Script à exécuter périodiquement (cron)
    Traite tous les documents dans un dossier
    """
    ocr = OCREngine("config/config.yaml")
    
    pending_folder = Path("/chemin/vers/documents_pending")
    processed_folder = Path("/chemin/vers/documents_processed")
    
    for file_path in pending_folder.glob("*.pdf"):
        try:
            # Détection automatique entreprise
            result = ocr.process_document(
                file_path=str(file_path),
                source_entreprise="auto-detect"
            )
            
            print(f"✓ {file_path.name} : Level {result.level}")
            
            # Déplacer vers processed
            file_path.rename(processed_folder / file_path.name)
            
        except Exception as e:
            print(f"✗ {file_path.name} : {e}")

if __name__ == "__main__":
    process_pending_documents()
```

Crontab :
```bash
# Exécuter toutes les 5 minutes
*/5 * * * * /usr/bin/python3 /path/to/process_pending.py
```

## 📊 Écriture dans Google Sheets

L'OCR Engine écrit automatiquement dans 4 feuilles :

### 1. INDEX GLOBAL
Chaque document traité → 1 ligne

| ID Document | Type | Date | Entreprise | Client | Montant TTC | Statut OCR | Confiance |
|-------------|------|------|------------|--------|-------------|------------|-----------|
| doc_202601... | facture | 2026-01-12 | Martin's | Client A | 1200.00 | OCR Level 1 | 85% |

### 2. CRM
Nouveaux clients détectés

| Nom | SIRET | Adresse | Téléphone | Source | Date |
|-----|-------|---------|-----------|--------|------|
| Client A | 12345... | 10 rue... | 01... | OCR Detection | 2026-01-12 |

### 3. COMPTABILITÉ
Écritures comptables

| Référence | Type | Date | HT | TVA | TTC | Entreprise | Client |
|-----------|------|------|----|----|-----|------------|--------|
| FA-2026-001 | facture | 2026-01-10 | 1000 | 200 | 1200 | Martin's | Client A |

### 4. LOG SYSTEM
Logs techniques

| Timestamp | Level | Document ID | OCR Level | Message | Décisions | Erreurs |
|-----------|-------|-------------|-----------|---------|-----------|---------|
| 2026-01-12... | INFO | doc_20260... | 1 | OCR completed | ... | |

## 🔧 Configuration avancée

### Multi-entreprise

Éditer `config/entreprises.yaml` :

```yaml
entreprises:
  - name: "Votre Entreprise"
    siret: "12345678900012"
    address: "..."
    phone: "..."
    iban: "..."
    tva: "..."
    
    identity:
      logo_patterns:
        - "Votre Entreprise"
        - "VOTRE_SIGLE"
      
      footer_patterns:
        - "votre-site.fr"
        - "Votre slogan"
```

### Seuils de confiance

Dans `config/config.yaml` :

```yaml
ocr_level1:
  confidence_threshold: 0.7  # Baisser = moins de Level 2

ocr_level2:
  confidence_threshold: 0.6  # Baisser = moins de Level 3
```

### Désactiver Google Sheets (mode test)

```yaml
google_sheets:
  enabled: false  # Mode dry-run
```

## 🧪 Tests

### Test unitaire

```python
from ocr_engine import OCREngine

def test_ocr_basic():
    engine = OCREngine("config/config.yaml")
    
    # Document de test
    result = engine.process_document(
        file_path="tests/fixtures/facture_test.pdf",
        source_entreprise="Martin's Traiteur"
    )
    
    assert result.document_type == "facture"
    assert result.confidence > 0.5
    assert 'total_ttc' in result.fields
    
    print("✓ Test OK")

test_ocr_basic()
```

### Test avec pytest

```bash
pytest tests/ -v
```

## 📈 Monitoring

### Vérifier les règles mémoire

```python
from ocr_engine import OCREngine

engine = OCREngine("config/config.yaml")
stats = engine.get_statistics()

print(f"Règles mémoire : {stats['memory_rules']['total_rules']}")
print(f"Plus utilisées : {stats['memory_rules']['most_used']}")
```

### Logs

Les logs sont écrits dans :
- Console (stdout)
- Google Sheets LOG SYSTEM

Surveiller les WARNING/ERROR pour détecter les problèmes.

## ⚠️ Gestion des erreurs

### Erreur de connexion Sheets

```python
try:
    result = engine.process_document(file_path, entreprise)
except Exception as e:
    logger.error(f"OCR failed: {e}")
    # Fallback : sauvegarder localement
    save_to_local_queue(file_path, entreprise)
```

### Document non lisible

Si OCR échoue sur un document :
1. Vérifier qualité du scan
2. Essayer re-scan avec meilleure résolution
3. Vérifier logs pour détails de l'erreur

### Règle mémoire incorrecte

Si une règle produit des résultats incorrects :

```python
from memory.ai_memory import AIMemory

memory = AIMemory("memory/rules.json")

# Supprimer la règle problématique
memory.delete_rule("rule_id_here")
```

## 🎓 Exemples avancés

Voir `examples/example_pipeline.py` pour :
- Traitement par lot
- Options avancées
- Statistiques
- Intégration complète

## 📞 Support

En cas de problème :
1. Vérifier les logs dans Google Sheets LOG SYSTEM
2. Consulter `ARCHITECTURE.md` pour comprendre le flux
3. Activer le mode DEBUG dans `config.yaml`

---

**Intégration sans casser l'existant** ✅  
**Résultats automatiquement dans Sheets** ✅  
**Apprentissage progressif** ✅
