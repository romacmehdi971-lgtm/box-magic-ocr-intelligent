"""
Orchestrateur IAPF - Commande healthcheck_iapf
"""
import json
from typing import Dict, Any
from .config import get_timestamp, get_filename_timestamp, SNAPSHOT_SCHEMA
from .tools import get_cloudrun_tool, get_github_tool, get_drive_tool, get_sheets_tool
from .utils import get_safe_logger

logger = get_safe_logger(__name__)

class IAPFOrchestrator:
    """Orchestrateur principal MCP Cockpit"""
    
    def __init__(self):
        self.cloudrun = get_cloudrun_tool()
        self.github = get_github_tool()
        self.drive = get_drive_tool()
        self.sheets = get_sheets_tool()
        
        self.risks = []
        self.conflicts = []
        self.artifacts = []
    
    def healthcheck_iapf(self) -> Dict[str, Any]:
        """
        iAPF.healthcheck.iapf
        Commande principale : exécute tous les audits et génère les rapports
        """
        logger.info("=== Starting IAPF Healthcheck ===")
        
        timestamp = get_timestamp()
        file_timestamp = get_filename_timestamp()
        
        # Reset risks/conflicts
        self.risks = []
        self.conflicts = []
        self.artifacts = []
        
        # 1. Cloud Run Status
        logger.info("Checking Cloud Run status...")
        cloudrun_status = self.cloudrun.status()
        cloudrun_logs = self.cloudrun.logs_export(hours=1, max_lines=50)
        
        # 2. GitHub Audits
        logger.info("Auditing GitHub repositories...")
        github_snapshot = self.github.snapshot()
        
        # 3. Drive Audit
        logger.info("Auditing Drive architecture...")
        drive_arch = self.drive.map_architecture()
        drive_naming = self.drive.audit_naming()
        
        # Ensure MCP structure
        drive_structure = self.drive.ensure_mcp_structure()
        
        # 4. Sheets Audit
        logger.info("Auditing Sheets...")
        box2026_audit = self.sheets.audit_box2026()
        
        # 5. Detect risks & conflicts
        self._analyze_results(cloudrun_status, cloudrun_logs, github_snapshot, 
                             drive_naming, box2026_audit)
        
        # 6. Sync to Hub (format officiel IAPF)
        logger.info("Syncing to HUB ORION...")
        # Format: ts_iso | type | title | details | author | source | tags
        details_json = json.dumps({
            "cloudrun_status": cloudrun_status.get("status"),
            "github_repos": len(github_snapshot.get("repos", {})),
            "risks_count": len(self.risks),
            "conflicts_count": len(self.conflicts)
        })
        hub_sync = self.sheets.sync_hub(
            event_type="healthcheck",
            title="IAPF Full Healthcheck",
            details=details_json,
            author="mcp_cockpit",
            tags="audit;monitoring;production"
        )
        
        # 7. Generate Snapshot JSON
        logger.info("Generating snapshot JSON...")
        snapshot = self._generate_snapshot(
            timestamp, cloudrun_status, cloudrun_logs, 
            github_snapshot, drive_arch, drive_naming,
            box2026_audit, hub_sync
        )
        
        snapshot_filename = f"snapshot_{file_timestamp}.json"
        self.artifacts.append({
            "type": "snapshot",
            "filename": snapshot_filename,
            "format": "json",
            "size_estimate": len(json.dumps(snapshot))
        })
        
        # 8. Generate Report Markdown
        logger.info("Generating report markdown...")
        report = self._generate_report(
            timestamp, cloudrun_status, cloudrun_logs,
            github_snapshot, drive_arch, drive_naming,
            box2026_audit, hub_sync
        )
        
        report_filename = f"healthcheck_{file_timestamp}.md"
        self.artifacts.append({
            "type": "report",
            "filename": report_filename,
            "format": "markdown",
            "size_estimate": len(report)
        })
        
        # 9. Generate Audit Log
        logger.info("Generating audit log...")
        audit_log = self._generate_audit_log(timestamp)
        
        audit_log_filename = f"audit_log_{file_timestamp}.json"
        self.artifacts.append({
            "type": "audit_log",
            "filename": audit_log_filename,
            "format": "json",
            "size_estimate": len(json.dumps(audit_log))
        })
        
        logger.info("=== IAPF Healthcheck Complete ===")
        
        return {
            "status": "success",
            "timestamp": timestamp,
            "snapshot": snapshot,
            "report": report,
            "audit_log": audit_log,
            "artifacts": self.artifacts,
            "risks_count": len(self.risks),
            "conflicts_count": len(self.conflicts)
        }
    
    def _analyze_results(self, cloudrun_status, cloudrun_logs, github_snapshot, 
                        drive_naming, box2026_audit):
        """Analyse les résultats et détecte les risques/conflits"""
        
        # Risque: Cloud Run status unknown
        if cloudrun_status.get("status") == "unknown":
            self.risks.append({
                "type": "cloudrun_status",
                "severity": "medium",
                "message": "Cloud Run status cannot be verified",
                "timestamp": get_timestamp()
            })
        
        # Risque: Nommage Drive non conforme
        if drive_naming.get("compliance_rate", 100) < 100:
            non_compliant = drive_naming.get("non_compliant", {}).get("count", 0)
            if non_compliant > 0:
                self.risks.append({
                    "type": "drive_naming",
                    "severity": "low",
                    "message": f"{non_compliant} files with non-compliant naming",
                    "timestamp": get_timestamp()
                })
        
        # Vérifier GitHub repos
        for repo_key, repo_data in github_snapshot.get("repos", {}).items():
            if repo_data.get("status") == "limited":
                self.risks.append({
                    "type": "github_audit",
                    "severity": "low",
                    "message": f"Limited audit for {repo_key}",
                    "timestamp": get_timestamp()
                })
    
    def _generate_snapshot(self, timestamp, cloudrun_status, cloudrun_logs,
                          github_snapshot, drive_arch, drive_naming,
                          box2026_audit, hub_sync) -> Dict[str, Any]:
        """Génère le snapshot JSON"""
        
        snapshot = {
            "meta": {
                "timestamp": timestamp,
                "version": "1.0.0",
                "environment": "PROD"
            },
            "cloudrun": {
                "status": cloudrun_status,
                "logs_summary": {
                    "count": cloudrun_logs.get("log_count", 0),
                    "status": cloudrun_logs.get("status")
                }
            },
            "github": github_snapshot,
            "drive": {
                "architecture": drive_arch,
                "naming_audit": drive_naming
            },
            "sheets": {
                "box2026": box2026_audit
            },
            "hub": hub_sync,
            "risks": self.risks,
            "conflicts": self.conflicts,
            "artifacts": self.artifacts
        }
        
        return snapshot
    
    def _generate_report(self, timestamp, cloudrun_status, cloudrun_logs,
                        github_snapshot, drive_arch, drive_naming,
                        box2026_audit, hub_sync) -> str:
        """Génère le rapport Markdown"""
        
        report_lines = [
            "# IAPF Healthcheck Report",
            "",
            f"**Generated:** {timestamp}",
            f"**Environment:** PROD",
            "",
            "---",
            "",
            "## 🌩️ Cloud Run Status",
            "",
            f"- **Service:** {cloudrun_status.get('service', 'N/A')}",
            f"- **Project:** {cloudrun_status.get('project', 'N/A')}",
            f"- **Region:** {cloudrun_status.get('region', 'N/A')}",
            f"- **Status:** {cloudrun_status.get('status', 'unknown')}",
            f"- **URL:** {cloudrun_status.get('url', 'N/A')}",
            "",
            "### Logs Summary",
            "",
            f"- **Log Count:** {cloudrun_logs.get('log_count', 0)}",
            f"- **Status:** {cloudrun_logs.get('status', 'unknown')}",
            "",
            "---",
            "",
            "## 🐙 GitHub Audit",
            ""
        ]
        
        for repo_key, repo_data in github_snapshot.get("repos", {}).items():
            report_lines.extend([
                f"### Repository: {repo_key}",
                "",
                f"- **Owner:** {repo_data.get('owner', 'N/A')}",
                f"- **Repo:** {repo_data.get('repo', 'N/A')}",
                f"- **Status:** {repo_data.get('status', 'unknown')}",
                f"- **URL:** {repo_data.get('url', 'N/A')}",
                ""
            ])
            
            if repo_data.get("recent_commits"):
                report_lines.append("**Recent Commits:**")
                for commit in repo_data["recent_commits"][:5]:
                    report_lines.append(f"- `{commit.get('sha', 'N/A')}` {commit.get('message', 'N/A')}")
                report_lines.append("")
        
        report_lines.extend([
            "---",
            "",
            "## 📁 Drive Audit",
            "",
            "### Architecture",
            "",
            f"- **Status:** {drive_arch.get('status', 'unknown')}",
            f"- **Root Path:** {drive_arch.get('root_path', 'N/A')}",
            "",
            "### Naming Compliance",
            "",
            f"- **Total Files:** {drive_naming.get('total_files', 0)}",
            f"- **Compliant:** {drive_naming.get('compliant', {}).get('count', 0)}",
            f"- **Non-Compliant:** {drive_naming.get('non_compliant', {}).get('count', 0)}",
            f"- **Compliance Rate:** {drive_naming.get('compliance_rate', 0):.1f}%",
            f"- **Template:** `{drive_naming.get('template', 'N/A')}`",
            "",
            "---",
            "",
            "## 📊 Sheets Audit",
            "",
            "### BOX2026",
            "",
            f"- **Sheet ID:** {box2026_audit.get('sheet_id', 'N/A')}",
            f"- **Name:** {box2026_audit.get('sheet_name', 'N/A')}",
            f"- **Status:** {box2026_audit.get('status', 'unknown')}",
            "",
            "---",
            "",
            "## 🔄 Hub Sync Status",
            "",
            f"- **Status:** {hub_sync.get('status', 'unknown')}",
            f"- **Hub ID:** {hub_sync.get('hub_id', 'N/A')}",
            f"- **Hub Name:** {hub_sync.get('hub_name', 'N/A')}",
            "",
            "---",
            "",
            "## ⚠️ Risks & Conflicts",
            "",
            f"### Risks Detected: {len(self.risks)}",
            ""
        ])
        
        if self.risks:
            for risk in self.risks:
                report_lines.append(f"- **[{risk['severity'].upper()}]** {risk['type']}: {risk['message']}")
        else:
            report_lines.append("No risks detected.")
        
        report_lines.extend([
            "",
            f"### Conflicts Detected: {len(self.conflicts)}",
            ""
        ])
        
        if self.conflicts:
            for conflict in self.conflicts:
                report_lines.append(f"- {conflict.get('type', 'unknown')}: {conflict.get('message', 'N/A')}")
        else:
            report_lines.append("No conflicts detected.")
        
        report_lines.extend([
            "",
            "---",
            "",
            "## 📦 Artifacts",
            ""
        ])
        
        for artifact in self.artifacts:
            report_lines.append(f"- **{artifact['type']}**: `{artifact['filename']}` ({artifact['format']}, ~{artifact['size_estimate']} bytes)")
        
        report_lines.extend([
            "",
            "---",
            "",
            f"*Report generated by MCP Central Cockpit IAPF v1.0.0 at {timestamp}*"
        ])
        
        return "\n".join(report_lines)
    
    def _generate_audit_log(self, timestamp) -> Dict[str, Any]:
        """Génère le log d'audit"""
        
        return {
            "timestamp": timestamp,
            "action": "healthcheck_iapf",
            "user": "mcp_cockpit",
            "environment": "PROD",
            "results": {
                "risks": len(self.risks),
                "conflicts": len(self.conflicts),
                "artifacts": len(self.artifacts)
            },
            "status": "completed"
        }

# Singleton
_orchestrator = None

def get_orchestrator() -> IAPFOrchestrator:
    """Factory pour IAPFOrchestrator"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = IAPFOrchestrator()
    return _orchestrator
