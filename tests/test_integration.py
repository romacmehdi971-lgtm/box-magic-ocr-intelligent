"""
Tests d'intégration de base

Note : Tests conceptuels, nécessitent documents de test réels
"""

import pytest
from pathlib import Path
import sys

# Ajouter le parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ocr_engine import OCREngine, OCRResult
from memory.ai_memory import AIMemory, Rule


class TestOCREngine:
    """Tests du moteur OCR principal"""
    
    def test_engine_initialization(self):
        """Test initialisation de l'engine"""
        # Note : nécessite config valide
        # engine = OCREngine("config/config.yaml")
        # assert engine is not None
        pass
    
    def test_configuration_loading(self):
        """Test chargement configuration"""
        # Vérifier que les fichiers de config existent
        assert Path("config/config.yaml").exists()
        assert Path("config/entreprises.yaml").exists()


class TestMemorySystem:
    """Tests du système de mémoire"""
    
    def test_memory_initialization(self):
        """Test initialisation de la mémoire"""
        memory = AIMemory("memory/test_rules.json")
        assert memory is not None
        assert isinstance(memory.rules, list)
    
    def test_rule_creation(self):
        """Test création d'une règle"""
        rule_dict = {
            'id': 'test_rule_001',
            'name': 'Test Rule',
            'conditions': {
                'document_type': 'facture'
            },
            'actions': {
                'total_ttc': {
                    'method': 'fixed_value',
                    'value': 1000.0,
                    'confidence': 0.9
                }
            },
            'metadata': {
                'created_at': '2026-01-12',
                'entreprise': 'Test Entreprise',
                'usage_count': 0
            }
        }
        
        rule = Rule(rule_dict)
        assert rule.id == 'test_rule_001'
        assert rule.name == 'Test Rule'
    
    def test_rule_save_load(self):
        """Test sauvegarde et rechargement de règle"""
        import tempfile
        import os
        
        # Créer fichier temporaire
        temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json')
        temp_path = temp_file.name
        temp_file.close()
        
        try:
            # Créer mémoire
            memory = AIMemory(temp_path)
            
            # Ajouter règle
            rule_dict = {
                'id': 'test_rule_002',
                'name': 'Test Rule 2',
                'conditions': {'document_type': 'devis'},
                'actions': {},
                'metadata': {'created_at': '2026-01-12', 'usage_count': 0}
            }
            
            rule_id = memory.save_rule(rule_dict)
            assert rule_id == 'test_rule_002'
            
            # Recharger
            memory2 = AIMemory(temp_path)
            assert len(memory2.rules) == 1
            assert memory2.rules[0].id == 'test_rule_002'
            
        finally:
            # Nettoyer
            if os.path.exists(temp_path):
                os.remove(temp_path)


class TestDocumentTypes:
    """Tests des types de documents"""
    
    def test_document_type_enum(self):
        """Test enum des types"""
        from utils.document_types import DocumentType
        
        assert DocumentType.FACTURE.value == "facture"
        assert DocumentType.DEVIS.value == "devis"
        
        # Test conversion
        doc_type = DocumentType.from_string("facture")
        assert doc_type == DocumentType.FACTURE
        
        # Test inconnu
        unknown = DocumentType.from_string("xyz")
        assert unknown == DocumentType.UNKNOWN
    
    def test_is_accounting_document(self):
        """Test détection document comptable"""
        from utils.document_types import DocumentType
        
        assert DocumentType.FACTURE.is_accounting_document()
        assert DocumentType.DEVIS.is_accounting_document()
        assert not DocumentType.UNKNOWN.is_accounting_document()


class TestValidators:
    """Tests des validateurs"""
    
    def test_validation_result(self):
        """Test structure ValidationResult"""
        from utils.validators import ValidationResult
        
        result = ValidationResult(
            is_valid=True,
            warnings=["Test warning"],
            errors=[]
        )
        
        assert result.is_valid
        assert len(result.warnings) == 1
        assert len(result.errors) == 0


class TestLogger:
    """Tests du système de logs"""
    
    def test_logger_setup(self):
        """Test configuration logger"""
        from utils.logger import setup_logger
        
        logger = setup_logger("TestLogger", "INFO")
        assert logger is not None
        assert logger.name == "TestLogger"


if __name__ == "__main__":
    # Exécution directe
    print("Exécution des tests basiques...")
    
    test_memory = TestMemorySystem()
    test_memory.test_memory_initialization()
    test_memory.test_rule_creation()
    test_memory.test_rule_save_load()
    
    test_types = TestDocumentTypes()
    test_types.test_document_type_enum()
    test_types.test_is_accounting_document()
    
    print("✓ Tests basiques OK")
