"""
Cloud Run Tool - READ-ONLY
"""
import json
import subprocess
from typing import Dict, Any, List
from ..config import CLOUDRUN_CONFIG, get_timestamp
from ..utils import get_safe_logger

logger = get_safe_logger(__name__)

class CloudRunTool:
    """Outil READ-ONLY pour Cloud Run"""
    
    def __init__(self):
        self.config = CLOUDRUN_CONFIG
        self.project = self.config["project"]
        self.region = self.config["region"]
        self.service = self.config["service"]
    
    def status(self) -> Dict[str, Any]:
        """
        iAPF.cloudrun.status
        Récupère le statut du service Cloud Run
        """
        logger.info(f"Checking Cloud Run status: {self.service}")
        
        try:
            # Tentative de récupération via gcloud (peut ne pas être disponible)
            cmd = [
                "gcloud", "run", "services", "describe", self.service,
                "--project", self.project,
                "--region", self.region,
                "--format=json"
            ]
            
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                return {
                    "status": "success",
                    "timestamp": get_timestamp(),
                    "service": self.service,
                    "project": self.project,
                    "region": self.region,
                    "url": data.get("status", {}).get("url", "N/A"),
                    "conditions": data.get("status", {}).get("conditions", []),
                    "traffic": data.get("spec", {}).get("traffic", [])
                }
            else:
                logger.warning(f"gcloud command failed: {result.stderr}")
                return self._fallback_status()
                
        except FileNotFoundError:
            logger.warning("gcloud CLI not available, using fallback")
            return self._fallback_status()
        except Exception as e:
            logger.error(f"Error getting Cloud Run status: {str(e)}")
            return self._fallback_status()
    
    def _fallback_status(self) -> Dict[str, Any]:
        """Statut fallback quand gcloud n'est pas disponible"""
        return {
            "status": "unknown",
            "timestamp": get_timestamp(),
            "service": self.service,
            "project": self.project,
            "region": self.region,
            "url": self.config.get("url", "N/A"),
            "message": "Status check requires gcloud CLI or service account"
        }
    
    def logs_export(self, hours: int = 1, max_lines: int = 100) -> Dict[str, Any]:
        """
        iAPF.cloudrun.logs.export
        Exporte les logs Cloud Run (sans données sensibles)
        """
        logger.info(f"Exporting Cloud Run logs: last {hours}h, max {max_lines} lines")
        
        try:
            cmd = [
                "gcloud", "logging", "read",
                f'resource.type="cloud_run_revision" AND resource.labels.service_name="{self.service}"',
                f"--project={self.project}",
                f"--limit={max_lines}",
                "--format=json",
                f"--freshness={hours}h"
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logs = json.loads(result.stdout) if result.stdout else []
                
                # Sanitize logs
                safe_logs = []
                for log in logs:
                    safe_log = {
                        "timestamp": log.get("timestamp"),
                        "severity": log.get("severity"),
                        "textPayload": self._sanitize_log(log.get("textPayload", "")),
                        "resource": {
                            "type": log.get("resource", {}).get("type"),
                            "service": self.service
                        }
                    }
                    safe_logs.append(safe_log)
                
                return {
                    "status": "success",
                    "timestamp": get_timestamp(),
                    "log_count": len(safe_logs),
                    "logs": safe_logs[:max_lines]
                }
            else:
                logger.warning(f"Log export failed: {result.stderr}")
                return self._fallback_logs()
                
        except FileNotFoundError:
            logger.warning("gcloud CLI not available for logs")
            return self._fallback_logs()
        except Exception as e:
            logger.error(f"Error exporting logs: {str(e)}")
            return self._fallback_logs()
    
    def _sanitize_log(self, text: str) -> str:
        """Supprime les données sensibles des logs"""
        import re
        
        # Masquer patterns sensibles
        patterns = [
            (r'\b\d{16}\b', '****'),
            (r'\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b', '****EMAIL****'),
            (r'TTC[_\s]+[\d.]+\s*EUR', '****AMOUNT****'),
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _fallback_logs(self) -> Dict[str, Any]:
        """Logs fallback"""
        return {
            "status": "unavailable",
            "timestamp": get_timestamp(),
            "message": "Log export requires gcloud CLI or service account",
            "logs": []
        }

# Singleton
_cloudrun_tool = None

def get_cloudrun_tool() -> CloudRunTool:
    """Factory pour CloudRunTool"""
    global _cloudrun_tool
    if _cloudrun_tool is None:
        _cloudrun_tool = CloudRunTool()
    return _cloudrun_tool
