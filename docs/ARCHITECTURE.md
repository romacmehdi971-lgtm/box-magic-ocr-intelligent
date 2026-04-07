# ARCHITECTURE TECHNIQUE — OCR INTELLIGENT 3 NIVEAUX

## 🎯 PRINCIPES FONDAMENTAUX

### 1. Modularité
Chaque niveau OCR est indépendant et testable séparément.

### 2. Progressive Enhancement
OCR1 → OCR2 → OCR3 uniquement si nécessaire.

### 3. Pas de régression
Un niveau supérieur ne peut pas dégrader les résultats d'un niveau inférieur.

### 4. Traçabilité totale
Chaque décision est loggée et explicable.

## 🏗️ FLUX DE TRAITEMENT DÉTAILLÉ

```
┌──────────────────────────────────────────────────────────────┐
│                     DOCUMENT ENTRANT                          │
│              (PDF, PNG, JPG via Google Drive)                 │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                    OCR ENGINE                                 │
│  • Chargement document                                        │
│  • Détection entreprise source (via patterns)                │
│  • Initialisation contexte                                   │
│  • Préparation logs                                           │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │  Vérification MEMORY STORE         │
        │  Règle existante pour ce pattern ? │
        └────────┬───────────────────┬───────┘
                 │ OUI               │ NON
                 │                   │
                 ▼                   ▼
        ┌─────────────────┐  ┌──────────────────────┐
        │ Application     │  │     OCR NIVEAU 1     │
        │ Règle directe   │  │   (RAPIDE & STABLE)  │
        │ Bypass OCR1     │  │                      │
        └────────┬────────┘  │ • Type document      │
                 │           │ • Dates évidentes    │
                 │           │ • Montants           │
                 │           │ • TVA simple         │
                 │           │ • Émetteur/Dest.     │
                 │           │ • Confiance/champ    │
                 │           └──────────┬───────────┘
                 │                      │
                 │           ┌──────────▼───────────┐
                 │           │  Confiance >= 0.7 ?  │
                 │           │  Champs complets ?   │
                 │           └──┬────────────┬──────┘
                 │              │ OUI        │ NON
                 │              │            │
                 │              │            ▼
                 │              │   ┌────────────────────┐
                 │              │   │   OCR NIVEAU 2     │
                 │              │   │  (APPROFONDI)      │
                 │              │   │                    │
                 │              │   │ • Analyse contexte │
                 │              │   │ • Croisements      │
                 │              │   │ • Amélioration     │
                 │              │   │ • Préserve OCR1    │
                 │              │   └─────────┬──────────┘
                 │              │             │
                 │              │   ┌─────────▼─────────┐
                 │              │   │ Confiance >= 0.6? │
                 │              │   │ Cohérent ?        │
                 │              │   └──┬──────────┬─────┘
                 │              │      │ OUI      │ NON
                 │              │      │          │
                 │              │      │          ▼
                 │              │      │  ┌────────────────────┐
                 │              │      │  │  OCR NIVEAU 3      │
                 │              │      │  │ (CONTRÔLE+MÉMOIRE) │
                 │              │      │  │                    │
                 │              │      │  │ • Vérif globale    │
                 │              │      │  │ • Corrections      │
                 │              │      │  │ • Complétions      │
                 │              │      │  │ • CRÉER RÈGLE      │
                 │              │      │  └─────────┬──────────┘
                 │              │      │            │
                 │              │      │            ▼
                 │              │      │  ┌──────────────────┐
                 │              │      │  │  MEMORY STORE    │
                 │              │      │  │  Enregistrement  │
                 │              │      │  │  nouvelle règle  │
                 │              │      │  └─────────┬────────┘
                 │              │      │            │
                 └──────────────┴──────┴────────────┘
                                │
                                ▼
                ┌───────────────────────────────────┐
                │     VALIDATION & NORMALISATION    │
                │  • Vérification cohérence         │
                │  • Séparation Entreprise/Client   │
                │  • Calculs (HT/TVA/TTC)           │
                │  • Formatage final                │
                └────────────────┬──────────────────┘
                                 │
                                 ▼
                ┌───────────────────────────────────┐
                │      ÉCRITURE GOOGLE SHEETS       │
                │                                   │
                │  1. INDEX GLOBAL                  │
                │     • Ligne document              │
                │     • Métadonnées OCR             │
                │                                   │
                │  2. CRM (si nouveau)              │
                │     • Nouveau client/fournisseur  │
                │                                   │
                │  3. COMPTABILITÉ                  │
                │     • Écriture comptable          │
                │                                   │
                │  4. LOG SYSTEM                    │
                │     • Logs techniques              │
                │     • Décisions prises            │
                └───────────────────────────────────┘
```

## 📦 MODULES DÉTAILLÉS

### 1. OCR ENGINE (Point d'entrée)

**Fichier** : `ocr_engine.py`

**Responsabilités** :
- Orchestration du flux OCR
- Détection entreprise source
- Gestion du contexte
- Routage intelligent
- Écriture finale dans Sheets

**Interface** :
```python
class OCREngine:
    def __init__(self, config_path: str):
        """Initialise l'engine avec la config"""
        
    def process_document(self, 
                        file_path: str, 
                        source_entreprise: str,
                        options: dict = None) -> OCRResult:
        """Point d'entrée principal"""
        
    def _detect_entreprise(self, document: Document) -> str:
        """Détecte l'entreprise source via patterns"""
        
    def _write_to_sheets(self, result: OCRResult) -> bool:
        """Écrit dans Google Sheets"""
```

### 2. OCR LEVEL 1 (Rapide)

**Fichier** : `levels/ocr_level1.py`

**Objectif** : Traiter 80% des cas standards en < 2 secondes

**Stratégie** :
```python
class OCRLevel1:
    def process(self, document: Document, context: Context) -> OCRResult:
        # 1. Détection type via patterns simples
        doc_type = self._detect_type(document)
        
        # 2. Extraction champs évidents
        fields = {}
        fields['date'] = self._extract_date(document)
        fields['montants'] = self._extract_amounts(document)
        fields['tva'] = self._extract_simple_tva(document)
        
        # 3. Détection émetteur/destinataire
        fields['emetteur'] = self._extract_emitter(document)
        fields['destinataire'] = self._extract_recipient(document)
        
        # 4. Séparation entreprise/client
        fields = self._separate_source_client(fields, context.source_entreprise)
        
        # 5. Score de confiance par champ
        for key, value in fields.items():
            fields[key] = {
                'value': value,
                'confidence': self._calculate_confidence(key, value)
            }
        
        # 6. Décision niveau suivant
        global_confidence = self._calculate_global_confidence(fields)
        needs_level2 = global_confidence < 0.7 or self._has_missing_critical_fields(fields)
        
        return OCRResult(
            level=1,
            confidence=global_confidence,
            fields=fields,
            needs_next_level=needs_level2
        )
```

**Techniques** :
- Regex patterns pour dates/montants
- Mots-clés pour types documents
- Position relative des champs (header/footer)
- Validation format (SIRET, TVA, IBAN)

### 3. OCR LEVEL 2 (Approfondi)

**Fichier** : `levels/ocr_level2.py`

**Objectif** : Améliorer les champs manquants/ambigus sans casser OCR1

**Stratégie** :
```python
class OCRLevel2:
    def process(self, document: Document, ocr1_result: OCRResult, context: Context) -> OCRResult:
        # 1. Copie des résultats OCR1 (préservation)
        fields = deepcopy(ocr1_result.fields)
        
        # 2. Analyse contextuelle avancée
        context_data = self._extract_context(document)
        
        # 3. Amélioration ciblée champs faibles
        for field_name, field_data in fields.items():
            if field_data['confidence'] < 0.7 or field_data['value'] is None:
                improved = self._improve_field(field_name, document, context_data)
                if improved and improved['confidence'] > field_data['confidence']:
                    fields[field_name] = improved
        
        # 4. Croisement d'informations
        fields = self._cross_validate(fields, context_data)
        
        # 5. Calculs et vérifications
        if self._can_calculate_missing_values(fields):
            fields = self._calculate_missing(fields)
        
        # 6. Décision niveau suivant
        global_confidence = self._calculate_global_confidence(fields)
        needs_level3 = global_confidence < 0.6 or self._is_unknown_pattern(document, context)
        
        return OCRResult(
            level=2,
            confidence=global_confidence,
            fields=fields,
            improved_fields=self._list_improved_fields(ocr1_result, fields),
            needs_next_level=needs_level3
        )
```

**Techniques** :
- Analyse sémantique (proximité mots-clés)
- Relations spatiales avancées
- Calculs inverses (TTC → HT si TVA connue)
- Recherche dans CRM existant
- Pattern matching avancé

### 4. OCR LEVEL 3 (Mémoire)

**Fichier** : `levels/ocr_level3.py`

**Objectif** : Résoudre cas complexes ET créer règle réutilisable

**Stratégie** :
```python
class OCRLevel3:
    def process(self, document: Document, ocr2_result: OCRResult, context: Context) -> OCRResult:
        # 1. Analyse pattern document
        pattern = self._analyze_pattern(document)
        
        # 2. Vérification cohérence globale
        issues = self._find_inconsistencies(ocr2_result.fields)
        
        # 3. Corrections ciblées
        fields = deepcopy(ocr2_result.fields)
        for issue in issues:
            correction = self._correct_field(issue, document, context)
            if correction:
                fields[issue.field_name] = correction
        
        # 4. Complétion champs absents
        missing = self._find_missing_critical_fields(fields)
        for field_name in missing:
            value = self._extract_missing_field(field_name, document, context)
            if value:
                fields[field_name] = value
        
        # 5. CRÉATION RÈGLE MÉMOIRE
        rule = self._create_rule(
            pattern=pattern,
            document=document,
            fields=fields,
            context=context
        )
        
        # 6. Enregistrement règle
        self.memory_store.save_rule(rule)
        
        return OCRResult(
            level=3,
            confidence=0.9,  # Confiance haute car validé
            fields=fields,
            corrections=self._list_corrections(ocr2_result, fields),
            rule_created=rule.to_dict()
        )
```

**Création de règle** :
```python
def _create_rule(self, pattern, document, fields, context):
    rule = Rule()
    
    # Conditions de déclenchement
    rule.add_condition('document_type', pattern.doc_type)
    rule.add_condition('footer_contains', pattern.footer_keywords)
    rule.add_condition('header_contains', pattern.header_keywords)
    
    if pattern.siret:
        rule.add_condition('siret_matches', pattern.siret)
    
    # Actions à appliquer
    for field_name, field_data in fields.items():
        if field_data['confidence'] > 0.8:
            rule.add_action(f'extract_{field_name}', {
                'method': field_data.get('extraction_method'),
                'position': field_data.get('position'),
                'pattern': field_data.get('pattern')
            })
    
    # Métadonnées
    rule.metadata = {
        'created_at': datetime.now(),
        'source_document': document.id,
        'entreprise': context.source_entreprise,
        'creator': 'OCR_Level3',
        'usage_count': 0
    }
    
    return rule
```

### 5. MEMORY STORE

**Fichier** : `memory/ai_memory.py`

**Structure** :
```python
class AIMemory:
    def __init__(self, storage_path: str):
        """Initialise le stockage des règles"""
        
    def find_matching_rule(self, document: Document, context: Context) -> Optional[Rule]:
        """Recherche une règle applicable"""
        # 1. Extraction caractéristiques document
        features = self._extract_features(document)
        
        # 2. Recherche règles candidates
        candidates = self._search_rules(features, context.source_entreprise)
        
        # 3. Scoring et sélection meilleure règle
        best_rule = self._select_best_rule(candidates, features)
        
        # 4. Incrémentation compteur usage
        if best_rule:
            best_rule.usage_count += 1
            self._update_rule(best_rule)
        
        return best_rule
    
    def save_rule(self, rule: Rule) -> str:
        """Enregistre une nouvelle règle"""
        # 1. Vérification doublon
        if self._rule_exists(rule):
            return self._merge_with_existing(rule)
        
        # 2. Attribution ID unique
        rule.id = self._generate_rule_id()
        
        # 3. Sauvegarde
        self.storage.save(rule)
        
        return rule.id
    
    def get_rule_stats(self) -> dict:
        """Statistiques des règles"""
        return {
            'total_rules': len(self.storage.all()),
            'most_used': self._get_most_used_rules(10),
            'by_entreprise': self._group_by_entreprise(),
            'by_doc_type': self._group_by_doc_type()
        }
```

**Format stockage** :
```json
{
  "id": "rule_20260112_001",
  "name": "Facture METRO - Format standard",
  "conditions": {
    "footer_contains": ["METRO", "SIRET 123456789"],
    "document_type": "facture",
    "header_pattern": "^FACTURE N°"
  },
  "actions": {
    "extract_client": {
      "method": "regex",
      "pattern": "(?:Client|Destinataire):\\s*([^\\n]+)",
      "position": "after_header"
    },
    "extract_tva": {
      "method": "line_position",
      "line_keyword": "TVA",
      "column": 2,
      "format": "percentage"
    },
    "extract_total_ttc": {
      "method": "footer_last_amount",
      "validation": "must_be_greater_than_ht"
    }
  },
  "metadata": {
    "created_at": "2026-01-12T10:30:00",
    "entreprise": "Martin's Traiteur",
    "usage_count": 42,
    "success_rate": 0.95,
    "last_used": "2026-01-12T15:45:00"
  }
}
```

## 🔌 CONNECTEURS GOOGLE SHEETS

**Fichier** : `connectors/google_sheets.py`

```python
class GoogleSheetsConnector:
    def __init__(self, credentials_path: str, spreadsheet_id: str):
        """Initialise connexion Google Sheets"""
        
    def write_to_index_global(self, ocr_result: OCRResult) -> bool:
        """Écrit dans INDEX GLOBAL"""
        row = [
            ocr_result.document_id,
            ocr_result.document_type,
            ocr_result.processing_date,
            ocr_result.entreprise_source,
            ocr_result.fields.get('client', {}).get('value'),
            ocr_result.fields.get('total_ttc', {}).get('value'),
            f"OCR Level {ocr_result.level}",
            ocr_result.confidence
        ]
        return self._append_row('INDEX GLOBAL', row)
    
    def write_to_crm(self, ocr_result: OCRResult) -> bool:
        """Écrit dans CRM si nouveau client"""
        client = ocr_result.fields.get('client')
        if not client or not self._is_new_client(client.get('value')):
            return False
        
        row = [
            client.get('value'),
            ocr_result.fields.get('client_siret', {}).get('value'),
            ocr_result.fields.get('client_address', {}).get('value'),
            ocr_result.fields.get('client_phone', {}).get('value'),
            f"OCR Detection - {ocr_result.processing_date}"
        ]
        return self._append_row('CRM', row)
    
    def write_to_comptabilite(self, ocr_result: OCRResult) -> bool:
        """Écrit dans COMPTABILITÉ"""
        row = [
            ocr_result.fields.get('reference', {}).get('value'),
            ocr_result.document_type,
            ocr_result.fields.get('montant_ht', {}).get('value'),
            ocr_result.fields.get('montant_tva', {}).get('value'),
            ocr_result.fields.get('total_ttc', {}).get('value'),
            ocr_result.fields.get('date', {}).get('value')
        ]
        return self._append_row('COMPTABILITÉ', row)
    
    def write_to_log_system(self, log_entry: dict) -> bool:
        """Écrit dans LOG SYSTEM"""
        row = [
            log_entry['timestamp'],
            log_entry['level'],
            log_entry['document_id'],
            log_entry['ocr_level'],
            log_entry['message'],
            log_entry.get('decisions', ''),
            log_entry.get('errors', '')
        ]
        return self._append_row('LOG SYSTEM', row)
```

## 📊 STRUCTURE DES DONNÉES

### OCRResult
```python
@dataclass
class OCRResult:
    document_id: str
    document_type: str
    level: int  # 1, 2 ou 3
    confidence: float  # 0.0 à 1.0
    entreprise_source: str
    fields: Dict[str, FieldValue]
    processing_date: datetime
    needs_next_level: bool = False
    improved_fields: List[str] = None
    corrections: List[str] = None
    rule_created: dict = None
    logs: List[str] = None

@dataclass
class FieldValue:
    value: Any
    confidence: float
    extraction_method: str = None
    position: dict = None
    pattern: str = None
```

## 🎯 POINTS D'INTÉGRATION

### 1. Déclenchement depuis Google Drive
```python
# Dans le pipeline existant
from ocr_engine import OCREngine

ocr = OCREngine("config/config.yaml")

def on_new_document(file_path: str, metadata: dict):
    """Callback quand nouveau document dans Drive"""
    
    # Détection entreprise depuis metadata ou contenu
    entreprise = metadata.get('entreprise') or 'auto-detect'
    
    # Traitement OCR
    result = ocr.process_document(
        file_path=file_path,
        source_entreprise=entreprise,
        options={'priority': metadata.get('priority', 'normal')}
    )
    
    # Résultat automatiquement dans Sheets
    print(f"Document traité : {result.document_id}")
    print(f"Niveau OCR : {result.level}")
    print(f"Confiance : {result.confidence}")
```

### 2. Traitement par lot
```python
def process_batch(file_paths: List[str], entreprise: str):
    """Traitement multiple documents"""
    ocr = OCREngine("config/config.yaml")
    
    results = []
    for file_path in file_paths:
        result = ocr.process_document(file_path, entreprise)
        results.append(result)
    
    # Statistiques globales
    stats = {
        'total': len(results),
        'level1': sum(1 for r in results if r.level == 1),
        'level2': sum(1 for r in results if r.level == 2),
        'level3': sum(1 for r in results if r.level == 3),
        'avg_confidence': sum(r.confidence for r in results) / len(results)
    }
    
    return results, stats
```

## 🔍 SYSTÈME DE LOGS

### Niveaux de logs
- **DEBUG** : Détails techniques (désactivé en prod)
- **INFO** : Étapes normales du traitement
- **WARNING** : Situations inhabituelles mais gérées
- **ERROR** : Erreurs nécessitant attention

### Exemple de log
```
[2026-01-12 15:30:45] INFO [doc_12345] OCR Level 1 started
[2026-01-12 15:30:46] INFO [doc_12345] Document type detected: facture (confidence: 0.92)
[2026-01-12 15:30:46] INFO [doc_12345] Entreprise source: Martin's Traiteur
[2026-01-12 15:30:47] INFO [doc_12345] Fields extracted: date, montant_ttc, client
[2026-01-12 15:30:47] WARNING [doc_12345] TVA field low confidence (0.45), escalating to Level 2
[2026-01-12 15:30:48] INFO [doc_12345] OCR Level 2 started
[2026-01-12 15:30:50] INFO [doc_12345] TVA improved: 20% (confidence: 0.88)
[2026-01-12 15:30:50] INFO [doc_12345] Final confidence: 0.85 - SUCCESS
[2026-01-12 15:30:51] INFO [doc_12345] Written to Google Sheets: INDEX GLOBAL, COMPTABILITÉ
```

---

**Architecture conçue pour : STABILITÉ • ÉVOLUTIVITÉ • TRAÇABILITÉ**
