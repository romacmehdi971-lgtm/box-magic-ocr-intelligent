#!/usr/bin/env python3
"""
BOX MAGIC OCR ENGINE - Point d'entrée principal
Architecture 3 niveaux : Rapide → Approfondi → Mémoire
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional, List
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml

from levels.ocr_level1 import OCRLevel1
from levels.ocr_level2 import OCRLevel2
from levels.ocr_level3 import OCRLevel3
from memory.ai_memory import AIMemory
from connectors.google_sheets import GoogleSheetsConnector
from connectors.document_loader import DocumentLoader
from utils.logger import setup_logger, log_ocr_decision
from utils.validators import validate_ocr_result
from utils.document_types import DocumentType
from utils.type_detector import detect_document_type, get_document_type_confidence

# =============================
# BOX MAGIC — GOVERNANCE GUARD
# Cloud Run MUST be READ-ONLY.
# OCR + JSON only. No Sheets/CRM/Drive writes.
# Default = READ_ONLY enabled.
# =============================
OCR_READ_ONLY = os.getenv('OCR_READ_ONLY', 'true').strip().lower() in ('1','true','yes','y','on')



@dataclass
class FieldValue:
    """Valeur d'un champ extrait avec sa confiance"""
    value: any
    confidence: float
    extraction_method: Optional[str] = None
    position: Optional[dict] = None
    pattern: Optional[str] = None


@dataclass
class OCRResult:
    """Résultat complet d'un traitement OCR"""
    document_id: str
    document_type: str
    level: int  # 1, 2 ou 3
    confidence: float  # 0.0 à 1.0
    entreprise_source: str
    fields: Dict[str, FieldValue]
    processing_date: datetime
    needs_next_level: bool = False
    improved_fields: Optional[List[str]] = None
    corrections: Optional[List[str]] = None
    rule_created: Optional[dict] = None
    logs: List[str] = field(default_factory=list)

    def to_dict(self):
        """Convertit en dictionnaire"""
        result = asdict(self)
        result['processing_date'] = self.processing_date.isoformat()
        return result


@dataclass
class ProcessingContext:
    """Contexte de traitement d'un document"""
    source_entreprise: str
    entreprise_config: dict
    options: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


class OCREngine:
    """
    Moteur OCR intelligent à 3 niveaux
    
    Usage:
        engine = OCREngine(config_path="config/config.yaml")
        result = engine.process_document("facture.pdf", "Martin's Traiteur")
    """
    
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialise le moteur OCR
        
        Args:
            config_path: Chemin vers le fichier de configuration YAML
        """
        self.config = self._load_config(config_path)
        self.logger = setup_logger(
            "OCREngine", 
            self.config.get('log_level', 'INFO')
        )
        
        # Initialisation des niveaux OCR
        self.ocr_level1 = OCRLevel1(self.config)
        self.ocr_level2 = OCRLevel2(self.config)
        self.ocr_level3 = OCRLevel3(self.config)
        
        # Initialisation de la mémoire
        memory_path = self.config.get('memory_store_path', 'memory/rules.json')
        self.memory = AIMemory(memory_path)
        
        # Initialisation des connecteurs
        self.sheets_connector = self._init_sheets_connector()
        self.document_loader = DocumentLoader(self.config)
        
        self.logger.info("OCR Engine initialized successfully")
    
    def _load_config(self, config_path: str) -> dict:
        """Charge la configuration depuis YAML"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Charger aussi les configurations entreprises
        entreprises_path = config.get('entreprises_config', 'config/entreprises.yaml')
        if os.path.exists(entreprises_path):
            with open(entreprises_path, 'r', encoding='utf-8') as f:
                config['entreprises'] = yaml.safe_load(f)
        
        return config
    
    
        """(GOV) Cloud Run is READ-ONLY — never initialize Sheets connector."""
    
        self.logger.info('[GOV] OCR_READ_ONLY=TRUE — Sheets connector initialization skipped (Cloud Run read-only).')
    
        return None

    
    def process_document(self, 
                        file_path: str, 
                        source_entreprise: str,
                        options: Optional[dict] = None) -> OCRResult:
        """
        Point d'entrée principal - Traite un document
        
        Args:
            file_path: Chemin vers le document (PDF, image)
            source_entreprise: Nom de l'entreprise source
            options: Options supplémentaires (priority, force_level, etc.)
        
        Returns:
            OCRResult avec tous les champs extraits
        """
        options = options or {}
        document_id = self._generate_document_id(file_path)
        
        self.logger.info(f"[{document_id}] Starting OCR processing")
        self.logger.info(f"[{document_id}] File: {file_path}")
        self.logger.info(f"[{document_id}] Source entreprise: {source_entreprise}")
        
        try:
            # 1. Chargement du document
            document = self.document_loader.load(file_path)
            self.logger.info(f"[{document_id}] Document loaded successfully")
            
            # 1.1 Détection type de document (basée sur le texte extrait)
            detected_doc_type = detect_document_type(document.get_text())
            type_confidence = get_document_type_confidence(document.get_text(), detected_doc_type)
            self.logger.info(f"[{document_id}] Document type detected: {detected_doc_type} (confidence: {type_confidence:.2f})")
            
            # 1.2 Récupérer métadonnées OCR
            ocr_mode = document.metadata.get('ocr_mode', 'UNKNOWN')
            pdf_text_detected = document.metadata.get('pdf_text_detected', None)
            
            self.logger.info(f"[{document_id}] OCR metadata: mode={ocr_mode}, pdf_text_detected={pdf_text_detected}")
            
            # 2. Préparation du contexte
            context = self._prepare_context(source_entreprise, options)
            
            # 3. Détection entreprise si auto-detect
            if source_entreprise == 'auto-detect':
                detected_entreprise = self._detect_entreprise(document)
                context.source_entreprise = detected_entreprise
                self.logger.info(f"[{document_id}] Entreprise auto-detected: {detected_entreprise}")
            
            # 4. Vérification règle mémoire existante
            matching_rule = self.memory.find_matching_rule(document, context)
            if matching_rule and not options.get('force_full_ocr', False):
                self.logger.info(f"[{document_id}] Applying memory rule: {matching_rule.id}")
                result = self._apply_memory_rule(document, matching_rule, context, document_id)
                # Ajouter le type détecté
                result.document_type = detected_doc_type
            else:
                # 5. Traitement OCR progressif
                result = self._progressive_ocr(document, context, document_id)
                # Remplacer le document_type par celui détecté (plus fiable que OCR1)
                result.document_type = detected_doc_type
            
            # 5.1 Ajouter métadonnées OCR au résultat
            result.logs.append(f"OCR_MODE={ocr_mode}")
            result.logs.append(f"PDF_TEXT_DETECTED={pdf_text_detected}")
            result.logs.append(f"DOCUMENT_TYPE={detected_doc_type} (confidence: {type_confidence:.2f})")
            
            # 6. Validation finale
            validation_result = validate_ocr_result(result)
            if not validation_result.is_valid:
                self.logger.warning(f"[{document_id}] Validation warnings: {validation_result.warnings}")
            
            # 7. Écriture dans Google Sheets
            if self.sheets_connector:
                self._write_to_sheets(result)
                self.logger.info(f"[{document_id}] Results written to Google Sheets")
            
            # 8. Log final
            self._log_final_result(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"[{document_id}] OCR processing failed: {e}", exc_info=True)
            # Log dans Google Sheets
            if self.sheets_connector:
                self.sheets_connector.write_to_log_system({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'ERROR',
                    'document_id': document_id,
                    'ocr_level': 0,
                    'message': f"OCR processing failed: {str(e)}",
                    'errors': str(e)
                })
            raise
    
    def _progressive_ocr(self, document, context: ProcessingContext, document_id: str) -> OCRResult:
        """
        Traitement OCR progressif : Level 1 → Level 2 → Level 3
        """
        # LEVEL 1 - RAPIDE & STABLE
        self.logger.info(f"[{document_id}] Starting OCR Level 1")
        log_ocr_decision(self.logger, document_id, 1, "Starting fast extraction")
        
        result = self.ocr_level1.process(document, context)
        result.document_id = document_id
        
        self.logger.info(f"[{document_id}] OCR Level 1 completed (confidence: {result.confidence:.2f})")
        log_ocr_decision(self.logger, document_id, 1, 
                        f"Extracted {len(result.fields)} fields, confidence: {result.confidence:.2f}")
        
        # Décision Level 2
        if not result.needs_next_level:
            self.logger.info(f"[{document_id}] OCR Level 1 sufficient, stopping here")
            return result
        
        # LEVEL 2 - APPROFONDI
        self.logger.info(f"[{document_id}] Escalating to OCR Level 2")
        log_ocr_decision(self.logger, document_id, 2, 
                        f"Level 1 insufficient (confidence: {result.confidence:.2f}), starting deep analysis")
        
        result = self.ocr_level2.process(document, result, context)
        
        self.logger.info(f"[{document_id}] OCR Level 2 completed (confidence: {result.confidence:.2f})")
        log_ocr_decision(self.logger, document_id, 2, 
                        f"Improved fields: {result.improved_fields}, confidence: {result.confidence:.2f}")
        
        # Décision Level 3
        if not result.needs_next_level:
            self.logger.info(f"[{document_id}] OCR Level 2 sufficient, stopping here")
            return result
        
        # LEVEL 3 - CONTRÔLE & MÉMOIRE (RARE)
        self.logger.warning(f"[{document_id}] Escalating to OCR Level 3 (RARE)")
        log_ocr_decision(self.logger, document_id, 3, 
                        "Level 2 insufficient or unknown pattern, activating memory creation")
        
        result = self.ocr_level3.process(document, result, context)
        
        self.logger.info(f"[{document_id}] OCR Level 3 completed (confidence: {result.confidence:.2f})")
        if result.rule_created:
            self.logger.info(f"[{document_id}] Memory rule created: {result.rule_created.get('id')}")
            log_ocr_decision(self.logger, document_id, 3, 
                            f"Rule created: {result.rule_created.get('id')}, future similar documents will be faster")
        
        return result
    
    def _apply_memory_rule(self, document, rule, context: ProcessingContext, document_id: str) -> OCRResult:
        """Applique une règle mémoire existante (bypass OCR classique)"""
        self.logger.info(f"[{document_id}] Applying memory rule: {rule.name}")
        
        # Application de la règle
        fields = rule.apply(document)
        
        # Construction du résultat
        result = OCRResult(
            document_id=document_id,
            document_type=rule.metadata.get('document_type', 'unknown'),
            level=0,  # Level 0 = règle mémoire
            confidence=0.95,  # Confiance haute pour règle validée
            entreprise_source=context.source_entreprise,
            fields=fields,
            processing_date=datetime.now(),
            needs_next_level=False
        )
        
        result.logs.append(f"Memory rule applied: {rule.id}")
        result.logs.append(f"Rule success rate: {rule.metadata.get('success_rate', 'N/A')}")
        
        return result
    
    def _detect_entreprise(self, document) -> str:
        """
        Détecte l'entreprise source via patterns
        
        Recherche dans le document :
        - Patterns logo/identité visuelle
        - SIRET
        - Mots-clés footer/header
        """
        entreprises = self.config.get('entreprises', {}).get('entreprises', [])
        
        document_text = document.get_text().lower()
        
        for entreprise in entreprises:
            name = entreprise['name']
            identity = entreprise.get('identity', {})
            
            # Vérification patterns logo
            logo_patterns = identity.get('logo_patterns', [])
            for pattern in logo_patterns:
                if pattern.lower() in document_text:
                    self.logger.debug(f"Entreprise detected via logo pattern: {pattern}")
                    return name
            
            # Vérification footer patterns
            footer_patterns = identity.get('footer_patterns', [])
            for pattern in footer_patterns:
                if pattern.lower() in document_text:
                    self.logger.debug(f"Entreprise detected via footer pattern: {pattern}")
                    return name
            
            # Vérification SIRET
            siret = entreprise.get('siret', '')
            if siret and siret in document_text:
                self.logger.debug(f"Entreprise detected via SIRET: {siret}")
                return name
        
        # Par défaut, première entreprise
        default_entreprise = entreprises[0]['name'] if entreprises else 'Unknown'
        self.logger.warning(f"No entreprise pattern matched, using default: {default_entreprise}")
        return default_entreprise
    
    def _prepare_context(self, source_entreprise: str, options: dict) -> ProcessingContext:
        """Prépare le contexte de traitement"""
        entreprises = self.config.get('entreprises', {}).get('entreprises', [])
        entreprise_config = next(
            (e for e in entreprises if e['name'] == source_entreprise),
            {}
        )
        
        return ProcessingContext(
            source_entreprise=source_entreprise,
            entreprise_config=entreprise_config,
            options=options
        )
    
    
        """(GOV) Cloud Run is READ-ONLY — never initialize Sheets connector."""
    
        self.logger.info('[GOV] OCR_READ_ONLY=TRUE — Sheets connector initialization skipped (Cloud Run read-only).')
    
        return None

    
    def _log_final_result(self, result: OCRResult):
        """Log du résultat final"""
        self.logger.info(f"[{result.document_id}] === FINAL RESULT ===")
        self.logger.info(f"[{result.document_id}] Type: {result.document_type}")
        self.logger.info(f"[{result.document_id}] Level: {result.level}")
        self.logger.info(f"[{result.document_id}] Confidence: {result.confidence:.2%}")
        self.logger.info(f"[{result.document_id}] Fields extracted: {len(result.fields)}")
        
        # Détails des champs
        for field_name, field_value in result.fields.items():
            if isinstance(field_value, FieldValue):
                self.logger.debug(f"[{result.document_id}]   {field_name}: {field_value.value} (conf: {field_value.confidence:.2f})")
    
    def _generate_document_id(self, file_path: str) -> str:
        """Génère un ID unique pour le document"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = Path(file_path).stem
        return f"doc_{timestamp}_{filename}"
    
    def get_statistics(self) -> dict:
        """Retourne les statistiques du moteur OCR"""
        return {
            'memory_rules': self.memory.get_rule_stats(),
            'config': {
                'entreprises_count': len(self.config.get('entreprises', {}).get('entreprises', [])),
                'log_level': self.config.get('log_level', 'INFO'),
                'sheets_enabled': self.config.get('google_sheets', {}).get('enabled', False)
            }
        }


if __name__ == "__main__":
    # Test basique
    print("BOX MAGIC OCR Engine - Ready")
    print("Usage: from ocr_engine import OCREngine")
