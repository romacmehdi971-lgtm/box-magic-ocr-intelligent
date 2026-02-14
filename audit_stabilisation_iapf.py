#!/usr/bin/env python3
"""
AUDIT STABILISATION + NETTOYAGE STRUCTUREL IAPF
================================================

Mode : PROPOSAL-ONLY strict
Objectif : Identifier patchs OCR empilés, parsing redondants, règles contradictoires
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import ast

WEBAPP_DIR = Path("/home/user/webapp")


class OCRPatchAudit:
    """Audit des patchs OCR accumulés"""
    
    def __init__(self):
        self.patches_detected = []
        self.redundancies = []
        self.contradictions = []
        self.parsing_layers = []
        
    def analyze_file(self, file_path: Path) -> Dict[str, Any]:
        """Analyse un fichier Python pour détecter patchs et redondances"""
        print(f"\n📂 Analyse {file_path.name}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
        
        analysis = {
            "file": str(file_path.relative_to(WEBAPP_DIR)),
            "total_lines": len(lines),
            "functions": [],
            "patches": [],
            "date_parsers": [],
            "amount_parsers": [],
            "overrides": [],
            "comments_fix": []
        }
        
        # Détecter fonctions
        func_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        for i, line in enumerate(lines, 1):
            if match := re.search(func_pattern, line):
                analysis["functions"].append({
                    "name": match.group(1),
                    "line": i
                })
        
        # Détecter mentions de FIX/PATCH dans commentaires
        fix_pattern = r'#.*\b(FIX|PATCH|TODO|FIXME|HACK|WORKAROUND)\b'
        for i, line in enumerate(lines, 1):
            if match := re.search(fix_pattern, line, re.IGNORECASE):
                analysis["comments_fix"].append({
                    "line": i,
                    "type": match.group(1).upper(),
                    "content": line.strip()
                })
        
        # Détecter parsers de dates multiples
        date_patterns = [
            r'DATE_PATTERNS?\s*=',
            r'parse.*date',
            r'extract.*date',
            r'\d{2}[/-]\d{2}[/-]\d{4}'
        ]
        for i, line in enumerate(lines, 1):
            for pattern in date_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    analysis["date_parsers"].append({
                        "line": i,
                        "content": line.strip()[:80]
                    })
                    break
        
        # Détecter parsers de montants multiples
        amount_patterns = [
            r'AMOUNT_PATTERNS?\s*=',
            r'parse.*amount',
            r'extract.*amount',
            r'extract.*montant',
                r'\d+[.,]\d{2}\s*€'
        ]
        for i, line in enumerate(lines, 1):
            for pattern in amount_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    analysis["amount_parsers"].append({
                        "line": i,
                        "content": line.strip()[:80]
                    })
                    break
        
        # Détecter overrides (fonction définie plusieurs fois)
        func_names = [f["name"] for f in analysis["functions"]]
        for name in set(func_names):
            count = func_names.count(name)
            if count > 1:
                analysis["overrides"].append({
                    "function": name,
                    "count": count,
                    "lines": [f["line"] for f in analysis["functions"] if f["name"] == name]
                })
        
        return analysis
    
    def run(self) -> Dict[str, Any]:
        """Exécute l'audit complet OCR"""
        print("\n" + "="*80)
        print("🔍 AUDIT PATCHS OCR ACCUMULÉS")
        print("="*80)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "files_analyzed": [],
            "summary": {
                "total_files": 0,
                "total_patches": 0,
                "total_date_parsers": 0,
                "total_amount_parsers": 0,
                "total_overrides": 0,
                "redundancies_detected": []
            },
            "proposals": []
        }
        
        # Fichiers à analyser
        files_to_analyze = [
            WEBAPP_DIR / "ocr_engine.py",
            WEBAPP_DIR / "levels" / "ocr_level1.py",
            WEBAPP_DIR / "levels" / "ocr_level2.py",
            WEBAPP_DIR / "levels" / "ocr_level3.py",
            WEBAPP_DIR / "utils" / "type_detector.py"
        ]
        
        for file_path in files_to_analyze:
            if file_path.exists():
                analysis = self.analyze_file(file_path)
                results["files_analyzed"].append(analysis)
                results["summary"]["total_files"] += 1
                results["summary"]["total_patches"] += len(analysis["comments_fix"])
                results["summary"]["total_date_parsers"] += len(analysis["date_parsers"])
                results["summary"]["total_amount_parsers"] += len(analysis["amount_parsers"])
                results["summary"]["total_overrides"] += len(analysis["overrides"])
        
        # Analyser redondances entre fichiers
        self._detect_redundancies(results)
        
        # Générer propositions
        self._generate_proposals(results)
        
        return results
    
    def _detect_redundancies(self, results: Dict[str, Any]):
        """Détecte les redondances entre fichiers"""
        print("\n🔄 Détection redondances...")
        
        all_date_parsers = []
        all_amount_parsers = []
        
        for file_analysis in results["files_analyzed"]:
            for parser in file_analysis["date_parsers"]:
                all_date_parsers.append({
                    "file": file_analysis["file"],
                    "line": parser["line"],
                    "content": parser["content"]
                })
            for parser in file_analysis["amount_parsers"]:
                all_amount_parsers.append({
                    "file": file_analysis["file"],
                    "line": parser["line"],
                    "content": parser["content"]
                })
        
        # Si plusieurs fichiers définissent des parsers de dates
        date_files = set(p["file"] for p in all_date_parsers)
        if len(date_files) > 1:
            results["summary"]["redundancies_detected"].append({
                "type": "date_parsers",
                "description": f"Parsers de dates définis dans {len(date_files)} fichiers différents",
                "files": list(date_files),
                "severity": "MEDIUM"
            })
        
        # Si plusieurs fichiers définissent des parsers de montants
        amount_files = set(p["file"] for p in all_amount_parsers)
        if len(amount_files) > 1:
            results["summary"]["redundancies_detected"].append({
                "type": "amount_parsers",
                "description": f"Parsers de montants définis dans {len(amount_files)} fichiers différents",
                "files": list(amount_files),
                "severity": "MEDIUM"
            })
    
    def _generate_proposals(self, results: Dict[str, Any]):
        """Génère les propositions de nettoyage"""
        print("\n💡 Génération propositions...")
        
        # Proposition 1 : Centraliser parsers
        if len(results["summary"]["redundancies_detected"]) > 0:
            results["proposals"].append({
                "id": "PROP-001",
                "category": "Centralisation",
                "priority": "HIGH",
                "description": "Centraliser tous les parsers (dates, montants) dans un module unique utils/parsers.py",
                "rationale": f"{len(results['summary']['redundancies_detected'])} redondances détectées entre fichiers",
                "impact": "Facilite maintenance et cohérence des extractions",
                "breaking": False
            })
        
        # Proposition 2 : Nettoyer commentaires FIX
        total_fixes = sum(len(f["comments_fix"]) for f in results["files_analyzed"])
        if total_fixes > 5:
            results["proposals"].append({
                "id": "PROP-002",
                "category": "Nettoyage",
                "priority": "LOW",
                "description": f"Nettoyer ou documenter les {total_fixes} commentaires FIX/TODO/HACK",
                "rationale": "Commentaires accumulés indiquent patchs empilés",
                "impact": "Code plus propre et maintenable",
                "breaking": False
            })
        
        # Proposition 3 : Supprimer overrides
        total_overrides = sum(len(f["overrides"]) for f in results["files_analyzed"])
        if total_overrides > 0:
            results["proposals"].append({
                "id": "PROP-003",
                "category": "Refactoring",
                "priority": "MEDIUM",
                "description": f"Résoudre {total_overrides} fonction(s) définies plusieurs fois",
                "rationale": "Fonctions multiples créent confusion et bugs",
                "impact": "Comportement OCR plus prévisible",
                "breaking": False
            })


class CRMGSAudit:
    """Audit CRM réel via fichiers .gs"""
    
    def __init__(self):
        self.functions_detected = []
        
    def run(self) -> Dict[str, Any]:
        """Exécute l'audit CRM .gs"""
        print("\n" + "="*80)
        print("🔍 AUDIT CRM RÉEL (.gs)")
        print("="*80)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "gs_files_found": [],
            "crm_functions": [],
            "mapping_hub": [],
            "pipeline_devis_facture": [],
            "proposals": []
        }
        
        # Chercher fichiers .gs
        gs_files = list(WEBAPP_DIR.glob("**/*.gs"))
        
        print(f"\n📄 Fichiers .gs trouvés : {len(gs_files)}")
        
        for gs_file in gs_files:
            print(f"  • {gs_file.name}")
            results["gs_files_found"].append(str(gs_file.relative_to(WEBAPP_DIR)))
            
            with open(gs_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Détecter fonctions CRM
            crm_keywords = [
                "devis", "facture", "client", "CRM", "validation", 
                "envoi", "PDF", "template", "numéro"
            ]
            
            func_pattern = r'function\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
            for match in re.finditer(func_pattern, content):
                func_name = match.group(1)
                func_content = content[match.start():match.start()+500]  # 500 chars context
                
                # Vérifier si fonction CRM
                is_crm = any(keyword.lower() in func_content.lower() for keyword in crm_keywords)
                
                if is_crm:
                    results["crm_functions"].append({
                        "file": gs_file.name,
                        "function": func_name,
                        "context": func_content[:200]
                    })
        
        # Analyse
        if len(results["crm_functions"]) == 0:
            results["proposals"].append({
                "id": "PROP-CRM-001",
                "category": "CRM",
                "priority": "HIGH",
                "description": "Localiser fichiers .gs CRM manquants (création devis, factures, validation)",
                "rationale": "Aucune fonction CRM détectée dans fichiers .gs présents dans repo",
                "impact": "Impossible d'auditer pipeline devis → facture sans fichiers",
                "action_required": "Obtenir accès aux fichiers .gs complets du Dashboard Google Sheets"
            })
        else:
            print(f"\n✅ {len(results['crm_functions'])} fonctions CRM détectées")
            
            # Analyser pipeline
            pipeline_keywords = {
                "creation": ["create", "nouveau", "new", "add"],
                "modification": ["update", "modif", "edit", "change"],
                "envoi": ["send", "email", "envoyer", "envoi"],
                "validation": ["valid", "approve", "accept", "confirm"],
                "facture": ["facture", "invoice", "bill"]
            }
            
            for stage, keywords in pipeline_keywords.items():
                matching_funcs = [
                    f for f in results["crm_functions"]
                    if any(kw in f["function"].lower() or kw in f["context"].lower() for kw in keywords)
                ]
                
                if matching_funcs:
                    results["pipeline_devis_facture"].append({
                        "stage": stage,
                        "functions": [f["function"] for f in matching_funcs],
                        "count": len(matching_funcs)
                    })
        
        return results


class ExportHUBAudit:
    """Audit export HUB vs BOX"""
    
    def run(self) -> Dict[str, Any]:
        """Exécute l'audit export"""
        print("\n" + "="*80)
        print("🔍 AUDIT EXPORT HUB vs BOX")
        print("="*80)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "box_export_analysis": {},
            "hub_export_analysis": {},
            "differences": [],
            "proposals": []
        }
        
        # Chercher fonctions export dans .gs
        gs_files = list(WEBAPP_DIR.glob("**/*.gs"))
        
        export_functions = {
            "BOX": [],
            "HUB": []
        }
        
        for gs_file in gs_files:
            with open(gs_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Chercher fonctions export
            export_pattern = r'function\s+([a-zA-Z_][a-zA-Z0-9_]*Export[a-zA-Z0-9_]*)\s*\('
            for match in re.finditer(export_pattern, content, re.IGNORECASE):
                func_name = match.group(1)
                func_context = content[match.start():match.start()+300]
                
                if "BOX" in func_name.upper() or "box" in func_context.lower():
                    export_functions["BOX"].append({
                        "file": gs_file.name,
                        "function": func_name
                    })
                elif "HUB" in func_name.upper() or "hub" in func_context.lower():
                    export_functions["HUB"].append({
                        "file": gs_file.name,
                        "function": func_name
                    })
        
        results["box_export_analysis"] = {
            "functions_found": len(export_functions["BOX"]),
            "functions": export_functions["BOX"]
        }
        
        results["hub_export_analysis"] = {
            "functions_found": len(export_functions["HUB"]),
            "functions": export_functions["HUB"]
        }
        
        # Comparer
        if len(export_functions["BOX"]) > 0 and len(export_functions["HUB"]) == 0:
            results["differences"].append({
                "type": "missing_hub_export",
                "description": "Export BOX présent mais export HUB absent ou non détecté",
                "severity": "HIGH"
            })
            
            results["proposals"].append({
                "id": "PROP-EXPORT-001",
                "category": "Export",
                "priority": "HIGH",
                "description": "Implémenter fonction export HUB similaire à export BOX",
                "rationale": "Export BOX fonctionne, utiliser comme modèle pour HUB",
                "impact": "Stabilise backup HUB ORION",
                "action_required": "Dupliquer et adapter logique export BOX pour HUB"
            })
        
        print(f"\n📊 Export BOX : {len(export_functions['BOX'])} fonction(s)")
        print(f"📊 Export HUB : {len(export_functions['HUB'])} fonction(s)")
        
        return results


def main():
    """Point d'entrée principal"""
    print("\n" + "="*80)
    print("🚀 AUDIT STABILISATION + NETTOYAGE STRUCTUREL IAPF")
    print("="*80)
    print(f"📅 Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Répertoire : {WEBAPP_DIR}")
    print("🔒 Mode : PROPOSAL-ONLY strict")
    print("="*80)
    
    full_report = {
        "meta": {
            "timestamp": datetime.now().isoformat(),
            "mode": "PROPOSAL_ONLY",
            "version": "1.0.0"
        },
        "audits": {}
    }
    
    # PHASE 1 : Audit OCR
    ocr_audit = OCRPatchAudit()
    ocr_results = ocr_audit.run()
    full_report["audits"]["ocr_patches"] = ocr_results
    
    # PHASE 2 : Audit CRM
    crm_audit = CRMGSAudit()
    crm_results = crm_audit.run()
    full_report["audits"]["crm_gs"] = crm_results
    
    # PHASE 3 : Audit Export
    export_audit = ExportHUBAudit()
    export_results = export_audit.run()
    full_report["audits"]["export_hub"] = export_results
    
    # Sauvegarder rapport
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = WEBAPP_DIR / f"audit_stabilisation_{timestamp}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(full_report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Rapport sauvegardé : {output_file}")
    
    # Résumé
    print("\n" + "="*80)
    print("📊 RÉSUMÉ AUDIT")
    print("="*80)
    
    total_proposals = (
        len(ocr_results.get("proposals", [])) +
        len(crm_results.get("proposals", [])) +
        len(export_results.get("proposals", []))
    )
    
    print(f"🔍 Fichiers OCR analysés : {ocr_results['summary']['total_files']}")
    print(f"🔍 Patchs détectés : {ocr_results['summary']['total_patches']}")
    print(f"🔍 Redondances : {len(ocr_results['summary']['redundancies_detected'])}")
    print(f"🔍 Fonctions CRM : {len(crm_results['crm_functions'])}")
    print(f"💡 Propositions générées : {total_proposals}")
    print("="*80)
    
    return full_report


if __name__ == "__main__":
    report = main()
