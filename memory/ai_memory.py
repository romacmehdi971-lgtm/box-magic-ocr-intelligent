"""
AI MEMORY - Système de mémoire et règles

Stocke les règles créées par OCR Level 3 pour réutilisation
Objectif : Éliminer l'apprentissage répétitif
"""

import json
import logging
import os
from typing import Optional, List, Dict
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("OCREngine.Memory")


class Rule:
    """
    Représente une règle d'extraction mémorisée
    
    Créée par OCR Level 3, appliquée directement sur documents similaires
    """
    
    def __init__(self, rule_dict: dict):
        """
        Initialise une règle depuis un dictionnaire
        
        Args:
            rule_dict: Dictionnaire avec id, name, conditions, actions, metadata
        """
        self.id = rule_dict['id']
        self.name = rule_dict['name']
        self.conditions = rule_dict['conditions']
        self.actions = rule_dict['actions']
        self.metadata = rule_dict['metadata']
    
    def matches(self, document, context) -> float:
        """
        Vérifie si la règle s'applique au document
        
        Returns:
            Score de correspondance (0.0 à 1.0)
        """
        text = document.get_text()
        text_lower = text.lower()
        
        score = 0.0
        max_score = 0.0
        
        # Vérification type document
        if 'document_type' in self.conditions:
            max_score += 20
            # Le type sera vérifié par OCR1, on assume match pour l'instant
            score += 20
        
        # Vérification signature
        if 'signature' in self.conditions:
            max_score += 30
            # Signature difficile à recalculer, on skip pour simplifier
            # Dans une vraie implem, recalculer et comparer
        
        # Vérification header
        if 'header_contains' in self.conditions:
            max_score += 20
            header_lines = text.split('\n')[:10]
            header_text = ' '.join(header_lines).lower()
            
            matches = sum(1 for pattern in self.conditions['header_contains'] 
                         if pattern.lower() in header_text)
            if self.conditions['header_contains']:
                score += 20 * (matches / len(self.conditions['header_contains']))
        
        # Vérification footer
        if 'footer_contains' in self.conditions:
            max_score += 20
            footer_lines = text.split('\n')[-10:]
            footer_text = ' '.join(footer_lines).lower()
            
            matches = sum(1 for pattern in self.conditions['footer_contains'] 
                         if pattern.lower() in footer_text)
            if self.conditions['footer_contains']:
                score += 20 * (matches / len(self.conditions['footer_contains']))
        
        # Vérification SIRET (fort indicateur)
        if 'siret_matches' in self.conditions:
            max_score += 30
            siret = self.conditions['siret_matches']
            if siret in text:
                score += 30
        
        # Vérification logo keywords
        if 'logo_keywords' in self.conditions:
            max_score += 10
            matches = sum(1 for kw in self.conditions['logo_keywords'] 
                         if kw.lower() in text_lower)
            if self.conditions['logo_keywords']:
                score += 10 * (matches / len(self.conditions['logo_keywords']))
        
        # Normalisation
        if max_score > 0:
            return score / max_score
        else:
            return 0.0
    
    def apply(self, document) -> Dict:
        """
        Applique la règle sur le document
        
        Returns:
            Dict de FieldValue extraits selon les actions de la règle
        """
        from ocr_engine import FieldValue
        
        fields = {}
        text = document.get_text()
        
        for field_name, action in self.actions.items():
            # Réappliquer la méthode d'extraction
            method = action.get('method')
            
            if method == 'fixed_value':
                # Valeur fixe (pour champs constants dans ce type de doc)
                fields[field_name] = FieldValue(
                    value=action['value'],
                    confidence=action.get('confidence', 0.95),
                    extraction_method='memory_rule',
                    pattern=self.id
                )
            
            elif method in ['regex', 'context_keyword']:
                # Ré-extraction avec le pattern enregistré
                pattern = action.get('pattern')
                # Simplification : réutiliser la valeur mémorisée
                # Dans une vraie implem, ré-exécuter le pattern
                fields[field_name] = FieldValue(
                    value=action['value'],
                    confidence=action.get('confidence', 0.90),
                    extraction_method='memory_rule',
                    pattern=self.id
                )
            
            else:
                # Méthode inconnue, utiliser valeur par défaut
                fields[field_name] = FieldValue(
                    value=action['value'],
                    confidence=action.get('confidence', 0.85),
                    extraction_method='memory_rule_fallback',
                    pattern=self.id
                )
        
        logger.info(f"Rule {self.id} applied: {len(fields)} fields extracted")
        
        return fields
    
    def to_dict(self) -> dict:
        """Convertit la règle en dictionnaire"""
        return {
            'id': self.id,
            'name': self.name,
            'conditions': self.conditions,
            'actions': self.actions,
            'metadata': self.metadata
        }


class AIMemory:
    """
    Système de mémoire pour les règles OCR
    
    Stocke et recherche les règles créées par Level 3
    """
    
    def __init__(self, storage_path: str = "memory/rules.json"):
        """
        Initialise le système de mémoire
        
        Args:
            storage_path: Chemin vers le fichier de stockage des règles
        """
        self.storage_path = storage_path
        self.rules: List[Rule] = []
        
        # Créer le répertoire si nécessaire
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        # Charger les règles existantes
        self._load_rules()
        
        logger.info(f"AI Memory initialized with {len(self.rules)} rules")
    
    def _load_rules(self):
        """Charge les règles depuis le fichier JSON"""
        if not os.path.exists(self.storage_path):
            logger.info(f"No existing rules file at {self.storage_path}")
            self.rules = []
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                rules_data = json.load(f)
            
            self.rules = [Rule(rule_dict) for rule_dict in rules_data]
            logger.info(f"Loaded {len(self.rules)} rules from storage")
            
        except Exception as e:
            logger.error(f"Failed to load rules: {e}")
            self.rules = []
    
    def _save_rules(self):
        """Sauvegarde les règles dans le fichier JSON"""
        try:
            rules_data = [rule.to_dict() for rule in self.rules]
            
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Saved {len(self.rules)} rules to storage")
            
        except Exception as e:
            logger.error(f"Failed to save rules: {e}")
    
    def find_matching_rule(self, document, context) -> Optional[Rule]:
        """
        Recherche une règle applicable au document
        
        Args:
            document: Document à traiter
            context: ProcessingContext
        
        Returns:
            Rule si trouvée, None sinon
        """
        if not self.rules:
            logger.debug("No rules in memory")
            return None
        
        # Filtrer par entreprise
        entreprise_rules = [
            rule for rule in self.rules 
            if rule.metadata.get('entreprise') == context.source_entreprise
        ]
        
        if not entreprise_rules:
            logger.debug(f"No rules for entreprise: {context.source_entreprise}")
            return None
        
        # Calculer score de correspondance pour chaque règle
        candidates = []
        for rule in entreprise_rules:
            score = rule.matches(document, context)
            if score > 0.7:  # Seuil de correspondance
                candidates.append((rule, score))
                logger.debug(f"Rule {rule.id} matches with score: {score:.2f}")
        
        if not candidates:
            logger.debug("No matching rule found")
            return None
        
        # Sélectionner la meilleure règle
        best_rule, best_score = max(candidates, key=lambda x: x[1])
        
        logger.info(f"Selected rule: {best_rule.id} (score: {best_score:.2f})")
        
        # Incrémenter compteur usage
        best_rule.metadata['usage_count'] = best_rule.metadata.get('usage_count', 0) + 1
        best_rule.metadata['last_used'] = datetime.now().isoformat()
        
        # Sauvegarder les métadonnées mises à jour
        self._save_rules()
        
        return best_rule
    
    def save_rule(self, rule_dict: dict) -> str:
        """
        Enregistre une nouvelle règle
        
        Args:
            rule_dict: Dictionnaire représentant la règle
        
        Returns:
            ID de la règle créée
        """
        # Vérifier si règle similaire existe déjà
        existing = self._find_similar_rule(rule_dict)
        
        if existing:
            logger.info(f"Similar rule exists: {existing.id}, merging...")
            return self._merge_with_existing(existing, rule_dict)
        
        # Créer nouvelle règle
        rule = Rule(rule_dict)
        self.rules.append(rule)
        
        # Sauvegarder
        self._save_rules()
        
        logger.info(f"New rule saved: {rule.id} - {rule.name}")
        
        return rule.id
    
    def _find_similar_rule(self, rule_dict: dict) -> Optional[Rule]:
        """Recherche une règle similaire existante"""
        new_conditions = rule_dict['conditions']
        
        for rule in self.rules:
            # Comparaison simple : même SIRET ou même signature
            if 'siret_matches' in new_conditions and 'siret_matches' in rule.conditions:
                if new_conditions['siret_matches'] == rule.conditions['siret_matches']:
                    return rule
            
            if 'signature' in new_conditions and 'signature' in rule.conditions:
                if new_conditions['signature'] == rule.conditions['signature']:
                    return rule
        
        return None
    
    def _merge_with_existing(self, existing_rule: Rule, new_rule_dict: dict) -> str:
        """Fusionne une nouvelle règle avec une existante"""
        # Mettre à jour les actions avec les nouvelles si meilleures
        for field_name, action in new_rule_dict['actions'].items():
            if field_name not in existing_rule.actions:
                existing_rule.actions[field_name] = action
                logger.debug(f"Added new field to rule: {field_name}")
            else:
                # Garder l'action avec la meilleure confiance
                existing_conf = existing_rule.actions[field_name].get('confidence', 0)
                new_conf = action.get('confidence', 0)
                
                if new_conf > existing_conf:
                    existing_rule.actions[field_name] = action
                    logger.debug(f"Updated field in rule: {field_name}")
        
        # Incrémenter usage count
        existing_rule.metadata['usage_count'] = existing_rule.metadata.get('usage_count', 0) + 1
        
        # Sauvegarder
        self._save_rules()
        
        logger.info(f"Merged with existing rule: {existing_rule.id}")
        
        return existing_rule.id
    
    def get_rule_stats(self) -> dict:
        """
        Retourne les statistiques des règles
        
        Returns:
            dict avec statistiques globales
        """
        if not self.rules:
            return {
                'total_rules': 0,
                'most_used': [],
                'by_entreprise': {},
                'by_doc_type': {}
            }
        
        # Most used rules
        sorted_rules = sorted(
            self.rules,
            key=lambda r: r.metadata.get('usage_count', 0),
            reverse=True
        )
        most_used = [
            {
                'id': r.id,
                'name': r.name,
                'usage_count': r.metadata.get('usage_count', 0),
                'success_rate': r.metadata.get('success_rate', 1.0)
            }
            for r in sorted_rules[:10]
        ]
        
        # Group by entreprise
        by_entreprise = {}
        for rule in self.rules:
            entreprise = rule.metadata.get('entreprise', 'Unknown')
            by_entreprise[entreprise] = by_entreprise.get(entreprise, 0) + 1
        
        # Group by doc type
        by_doc_type = {}
        for rule in self.rules:
            doc_type = rule.metadata.get('document_type', 'unknown')
            by_doc_type[doc_type] = by_doc_type.get(doc_type, 0) + 1
        
        return {
            'total_rules': len(self.rules),
            'most_used': most_used,
            'by_entreprise': by_entreprise,
            'by_doc_type': by_doc_type
        }
    
    def delete_rule(self, rule_id: str) -> bool:
        """
        Supprime une règle
        
        Args:
            rule_id: ID de la règle à supprimer
        
        Returns:
            True si supprimée, False si non trouvée
        """
        initial_count = len(self.rules)
        self.rules = [r for r in self.rules if r.id != rule_id]
        
        if len(self.rules) < initial_count:
            self._save_rules()
            logger.info(f"Rule deleted: {rule_id}")
            return True
        else:
            logger.warning(f"Rule not found: {rule_id}")
            return False
    
    def export_rules(self, export_path: str) -> bool:
        """
        Exporte toutes les règles vers un fichier
        
        Args:
            export_path: Chemin du fichier d'export
        
        Returns:
            True si succès
        """
        try:
            rules_data = [rule.to_dict() for rule in self.rules]
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(rules_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(self.rules)} rules to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export rules: {e}")
            return False
    
    def import_rules(self, import_path: str, merge: bool = True) -> int:
        """
        Importe des règles depuis un fichier
        
        Args:
            import_path: Chemin du fichier d'import
            merge: Si True, fusionne avec les règles existantes
        
        Returns:
            Nombre de règles importées
        """
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            imported_rules = [Rule(rule_dict) for rule_dict in imported_data]
            
            if merge:
                # Fusionner avec existantes
                for rule in imported_rules:
                    if not any(r.id == rule.id for r in self.rules):
                        self.rules.append(rule)
            else:
                # Remplacer
                self.rules = imported_rules
            
            self._save_rules()
            
            logger.info(f"Imported {len(imported_rules)} rules from {import_path}")
            return len(imported_rules)
            
        except Exception as e:
            logger.error(f"Failed to import rules: {e}")
            return 0
