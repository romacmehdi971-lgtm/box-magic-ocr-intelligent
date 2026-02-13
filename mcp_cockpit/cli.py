#!/usr/bin/env python3
"""
CLI pour MCP Central Cockpit IAPF
Commande unique: healthcheck_iapf
"""
import sys
import json
import argparse
from pathlib import Path
from .orchestrator import get_orchestrator
from .config import get_filename_timestamp
from .utils import get_safe_logger

logger = get_safe_logger(__name__)

def save_artifacts(results: dict, output_dir: str = "mcp_cockpit/reports"):
    """Sauvegarde les artifacts générés"""
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    file_timestamp = get_filename_timestamp()
    
    # Save snapshot JSON
    snapshot_file = output_path / f"snapshot_{file_timestamp}.json"
    with open(snapshot_file, 'w') as f:
        json.dump(results['snapshot'], f, indent=2)
    logger.info(f"Snapshot saved: {snapshot_file}")
    
    # Save report Markdown
    report_file = output_path / f"healthcheck_{file_timestamp}.md"
    with open(report_file, 'w') as f:
        f.write(results['report'])
    logger.info(f"Report saved: {report_file}")
    
    # Save audit log
    audit_log_file = output_path / f"audit_log_{file_timestamp}.json"
    with open(audit_log_file, 'w') as f:
        json.dump(results['audit_log'], f, indent=2)
    logger.info(f"Audit log saved: {audit_log_file}")
    
    return {
        "snapshot": str(snapshot_file),
        "report": str(report_file),
        "audit_log": str(audit_log_file)
    }

def cmd_healthcheck(args):
    """Exécute la commande healthcheck_iapf"""
    
    logger.info("Executing healthcheck_iapf command...")
    
    orchestrator = get_orchestrator()
    results = orchestrator.healthcheck_iapf()
    
    # Save artifacts
    saved_files = save_artifacts(results, args.output_dir)
    
    # Print summary
    print("\n" + "="*60)
    print("IAPF HEALTHCHECK COMPLETE")
    print("="*60)
    print(f"Status: {results['status']}")
    print(f"Timestamp: {results['timestamp']}")
    print(f"Risks: {results['risks_count']}")
    print(f"Conflicts: {results['conflicts_count']}")
    print(f"Artifacts: {len(results['artifacts'])}")
    print("\nGenerated files:")
    for file_type, file_path in saved_files.items():
        print(f"  - {file_type}: {file_path}")
    print("="*60 + "\n")
    
    return 0

def main():
    """Point d'entrée CLI"""
    
    parser = argparse.ArgumentParser(
        description="MCP Central Cockpit IAPF - Production Monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s healthcheck              # Run full healthcheck
  %(prog)s healthcheck -o ./output  # Save artifacts to custom directory
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # healthcheck_iapf command
    healthcheck_parser = subparsers.add_parser(
        'healthcheck',
        help='Execute full IAPF healthcheck'
    )
    healthcheck_parser.add_argument(
        '-o', '--output-dir',
        default='mcp_cockpit/reports',
        help='Output directory for artifacts (default: mcp_cockpit/reports)'
    )
    healthcheck_parser.set_defaults(func=cmd_healthcheck)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        return args.func(args)
    except Exception as e:
        logger.error(f"Command failed: {str(e)}")
        print(f"ERROR: {str(e)}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())
