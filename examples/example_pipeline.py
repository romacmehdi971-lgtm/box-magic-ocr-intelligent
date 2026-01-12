#!/usr/bin/env python3
"""
Exemple d'utilisation de l'OCR Engine dans un pipeline

Ce script montre comment intégrer l'OCR Engine dans votre pipeline existant
"""

import sys
import os
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ocr_engine import OCREngine


def example_single_document():
    """Exemple 1 : Traitement d'un seul document"""
    print("=== Exemple 1 : Document unique ===\n")
    
    # Initialisation de l'engine
    engine = OCREngine(config_path="config/config.yaml")
    
    # Traitement d'une facture
    result = engine.process_document(
        file_path="documents/facture_exemple.pdf",
        source_entreprise="Martin's Traiteur"
    )
    
    # Affichage résultat
    print(f"Document traité : {result.document_id}")
    print(f"Type détecté : {result.document_type}")
    print(f"Niveau OCR utilisé : {result.level}")
    print(f"Confiance globale : {result.confidence:.2%}")
    print(f"\nChamps extraits :")
    
    for field_name, field_value in result.fields.items():
        print(f"  - {field_name}: {field_value.value} (confiance: {field_value.confidence:.2f})")
    
    # Résultat automatiquement écrit dans Google Sheets
    print(f"\n✓ Résultats écrits dans Google Sheets")


def example_auto_detect_entreprise():
    """Exemple 2 : Détection automatique de l'entreprise"""
    print("\n\n=== Exemple 2 : Détection automatique entreprise ===\n")
    
    engine = OCREngine(config_path="config/config.yaml")
    
    # Utiliser 'auto-detect' pour détecter l'entreprise depuis le document
    result = engine.process_document(
        file_path="documents/facture_mt_production.pdf",
        source_entreprise="auto-detect"
    )
    
    print(f"Entreprise détectée : {result.entreprise_source}")
    print(f"Confiance : {result.confidence:.2%}")


def example_batch_processing():
    """Exemple 3 : Traitement par lot"""
    print("\n\n=== Exemple 3 : Traitement par lot ===\n")
    
    engine = OCREngine(config_path="config/config.yaml")
    
    # Liste de documents à traiter
    documents = [
        ("documents/facture1.pdf", "Martin's Traiteur"),
        ("documents/facture2.pdf", "Martin's Traiteur"),
        ("documents/devis1.pdf", "MT Production"),
    ]
    
    results = []
    
    for file_path, entreprise in documents:
        try:
            result = engine.process_document(file_path, entreprise)
            results.append(result)
            print(f"✓ {file_path} : Level {result.level}, confiance {result.confidence:.2%}")
        except Exception as e:
            print(f"✗ {file_path} : Erreur - {e}")
    
    # Statistiques globales
    total = len(results)
    level1 = sum(1 for r in results if r.level == 1)
    level2 = sum(1 for r in results if r.level == 2)
    level3 = sum(1 for r in results if r.level == 3)
    avg_confidence = sum(r.confidence for r in results) / total if total > 0 else 0
    
    print(f"\n=== Statistiques ===")
    print(f"Total documents : {total}")
    print(f"Level 1 (rapide) : {level1} ({level1/total*100:.1f}%)")
    print(f"Level 2 (approfondi) : {level2} ({level2/total*100:.1f}%)")
    print(f"Level 3 (mémoire) : {level3} ({level3/total*100:.1f}%)")
    print(f"Confiance moyenne : {avg_confidence:.2%}")


def example_with_options():
    """Exemple 4 : Options avancées"""
    print("\n\n=== Exemple 4 : Options avancées ===\n")
    
    engine = OCREngine(config_path="config/config.yaml")
    
    # Options personnalisées
    result = engine.process_document(
        file_path="documents/facture_complexe.pdf",
        source_entreprise="Martin's Traiteur",
        options={
            'priority': 'high',          # Priorité haute
            'force_full_ocr': True,      # Forcer OCR complet (ignorer règles mémoire)
            'create_rule': True          # Forcer création règle si Level 3
        }
    )
    
    print(f"Traitement avec options avancées")
    print(f"Niveau utilisé : {result.level}")
    
    if result.rule_created:
        print(f"✓ Règle mémoire créée : {result.rule_created['id']}")


def example_statistics():
    """Exemple 5 : Statistiques du moteur"""
    print("\n\n=== Exemple 5 : Statistiques ===\n")
    
    engine = OCREngine(config_path="config/config.yaml")
    
    stats = engine.get_statistics()
    
    print("Statistiques du moteur OCR :")
    print(f"\nMémoire :")
    print(f"  - Total règles : {stats['memory_rules']['total_rules']}")
    print(f"  - Par entreprise : {stats['memory_rules']['by_entreprise']}")
    print(f"  - Par type : {stats['memory_rules']['by_doc_type']}")
    
    print(f"\nConfiguration :")
    print(f"  - Entreprises configurées : {stats['config']['entreprises_count']}")
    print(f"  - Niveau log : {stats['config']['log_level']}")
    print(f"  - Google Sheets : {'Activé' if stats['config']['sheets_enabled'] else 'Désactivé'}")
    
    if stats['memory_rules']['most_used']:
        print(f"\nRègles les plus utilisées :")
        for rule in stats['memory_rules']['most_used'][:5]:
            print(f"  - {rule['name']} : {rule['usage_count']} utilisations (succès: {rule['success_rate']:.1%})")


def example_integration_drive():
    """Exemple 6 : Intégration avec Google Drive (conceptuel)"""
    print("\n\n=== Exemple 6 : Intégration Google Drive ===\n")
    
    print("Exemple de callback pour Google Drive :")
    print("""
    from ocr_engine import OCREngine
    
    ocr = OCREngine("config/config.yaml")
    
    def on_new_file_in_drive(file_path: str, metadata: dict):
        '''Callback appelé quand nouveau fichier dans Drive'''
        
        # Récupérer entreprise depuis metadata ou auto-detect
        entreprise = metadata.get('entreprise', 'auto-detect')
        
        # Traiter avec OCR
        result = ocr.process_document(file_path, entreprise)
        
        # Résultats automatiquement dans Google Sheets
        print(f"Traité : {result.document_id}")
        
        return result
    
    # Configuration Google Drive watcher
    # drive_watcher.on_new_file(on_new_file_in_drive)
    """)


if __name__ == "__main__":
    print("=" * 60)
    print("BOX MAGIC OCR ENGINE - Exemples d'utilisation")
    print("=" * 60)
    
    # Note : Ces exemples sont conceptuels
    # Les fichiers documents doivent exister pour exécution réelle
    
    print("\n⚠️  Note : Ces exemples sont conceptuels")
    print("Pour exécution réelle, créez les fichiers dans documents/")
    print("\nExemples disponibles :")
    print("  1. Document unique")
    print("  2. Détection automatique entreprise")
    print("  3. Traitement par lot")
    print("  4. Options avancées")
    print("  5. Statistiques")
    print("  6. Intégration Google Drive")
    
    # Décommenter pour exécuter les exemples
    # example_single_document()
    # example_auto_detect_entreprise()
    # example_batch_processing()
    # example_with_options()
    # example_statistics()
    # example_integration_drive()
