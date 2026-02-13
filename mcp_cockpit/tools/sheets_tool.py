"""
Sheets Tool PROD - READ pour BOX2026, WRITE contrôlé pour HUB ORION
Format MEMORY_LOG officiel IAPF : ts_iso | type | title | details | author | source | tags

Mode PROD : Authentification via Application Default Credentials (metadata)
"""
import os
import json
from typing import Dict, Any, List, Optional
from ..config import iapf_config
from ..utils import safe_logger

logger = safe_logger.get_safe_logger(__name__)

# Import conditionnel Google Sheets API
try:
    from google.auth import default as google_auth_default
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    SHEETS_API_AVAILABLE = True
except ImportError:
    SHEETS_API_AVAILABLE = False
    logger.warning("Google Sheets API not available - running in simulated mode")


class SheetsTool:
    """Outil pour Google Sheets avec contrôle d'accès PROD"""
    
    def __init__(self):
        self.config = iapf_config.SHEETS_CONFIG
        self.use_metadata_auth = os.getenv("USE_METADATA_AUTH", "false").lower() == "true"
        self.service = None
        
        if SHEETS_API_AVAILABLE:
            try:
                self._init_service()
            except Exception as e:
                logger.error(f"Failed to initialize Sheets service: {e}")
    
    def _init_service(self):
        """Initialise le service Google Sheets avec ADC"""
        try:
            if self.use_metadata_auth:
                # PROD : Utiliser Application Default Credentials (metadata)
                credentials, project = google_auth_default(
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                logger.info(f"Using metadata auth for project: {project}")
            else:
                # DEV : Utiliser service account file
                logger.warning("Using local service account (DEV mode)")
                credentials, project = google_auth_default()
            
            self.service = build('sheets', 'v4', credentials=credentials)
            logger.info("Sheets service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Sheets service: {e}")
            self.service = None
    
    def audit_box2026(self) -> Dict[str, Any]:
        """
        iAPF.sheets.box2026.audit
        Audite le fichier BOX2026 (READ-ONLY)
        """
        logger.info("Auditing BOX2026 sheet")
        
        if not self.service:
            return self._fallback_audit("BOX2026", "Sheets API not initialized")
        
        try:
            spreadsheet_id = self.config["box2026"]["id"]
            
            # Lire les métadonnées du spreadsheet
            spreadsheet = self.service.spreadsheets().get(
                spreadsheetId=spreadsheet_id
            ).execute()
            
            sheet_names = [sheet['properties']['title'] for sheet in spreadsheet.get('sheets', [])]
            
            # Vérifier présence des onglets critiques
            has_config = 'CONFIG' in sheet_names
            crm_sheets = [name for name in sheet_names if name.startswith('CRM_')]
            
            # Audit simple
            risks = []
            if not has_config:
                risks.append({
                    "level": "high",
                    "type": "missing_config_sheet",
                    "message": "CONFIG sheet not found in BOX2026"
                })
            
            if len(crm_sheets) < 3:
                risks.append({
                    "level": "medium",
                    "type": "missing_crm_sheets",
                    "message": f"Expected at least 3 CRM_ sheets, found {len(crm_sheets)}"
                })
            
            return {
                "status": "success",
                "timestamp": iapf_config.get_timestamp(),
                "sheet_id": spreadsheet_id,
                "sheet_name": self.config["box2026"]["name"],
                "url": self.config["box2026"]["url"],
                "checks": {
                    "config_sheet_exists": has_config,
                    "crm_sheets_exist": len(crm_sheets) > 0,
                    "crm_sheets": crm_sheets,
                    "total_sheets": len(sheet_names)
                },
                "risks": risks
            }
        
        except HttpError as e:
            logger.error(f"HTTP error auditing BOX2026: {e}")
            if e.resp.status == 403:
                return self._fallback_audit("BOX2026", "Permission denied - check sharing with service account")
            return self._fallback_audit("BOX2026", f"HTTP {e.resp.status}: {e.reason}")
        
        except Exception as e:
            logger.error(f"Error auditing BOX2026: {e}")
            return self._fallback_audit("BOX2026", str(e))
    
    def sync_hub(self, event_type: str, title: str, details: str, 
                 author: str = "mcp_cockpit", tags: str = "") -> Dict[str, Any]:
        """
        iAPF.sheets.hub.sync
        Synchronise avec HUB ORION selon format officiel IAPF
        
        Format MEMORY_LOG : ts_iso | type | title | details | author | source | tags
        - Séparateur : TAB (\t)
        - 7 colonnes exactes
        - ts_iso : ISO UTC
        - tags : séparés par ;
        """
        logger.info(f"Syncing to HUB ORION: {event_type} / {title}")
        
        if not self.service:
            return self._fallback_sync("Sheets API not initialized")
        
        try:
            spreadsheet_id = self.config["hub_orion"]["id"]
            timestamp = iapf_config.get_timestamp()
            source = "cloud_run_job" if self.use_metadata_auth else "local_dev"
            
            # Construire la ligne MEMORY_LOG (7 colonnes TSV)
            memory_log_row = [
                timestamp,      # ts_iso
                event_type,     # type
                title,          # title
                details if isinstance(details, str) else json.dumps(details),  # details
                author,         # author
                source,         # source
                tags            # tags
            ]
            
            # Vérifier format strict
            if len(memory_log_row) != 7:
                raise ValueError(f"MEMORY_LOG requires 7 columns, got {len(memory_log_row)}")
            
            # Append à MEMORY_LOG
            range_name = "MEMORY_LOG!A:G"
            body = {
                'values': [memory_log_row]
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            logger.info(f"Appended {result.get('updates', {}).get('updatedRows', 0)} row to MEMORY_LOG")
            
            return {
                "status": "success",
                "timestamp": timestamp,
                "hub_id": spreadsheet_id,
                "hub_name": self.config["hub_orion"]["name"],
                "memory_log_appended": {
                    "ts_iso": timestamp,
                    "type": event_type,
                    "title": title,
                    "details": details,
                    "author": author,
                    "source": source,
                    "tags": tags
                },
                "sheets_updated": result.get('updates', {})
            }
        
        except HttpError as e:
            logger.error(f"HTTP error syncing HUB: {e}")
            if e.resp.status == 403:
                return self._fallback_sync("Permission denied - check HUB ORION is shared with Editor access")
            return self._fallback_sync(f"HTTP {e.resp.status}: {e.reason}")
        
        except Exception as e:
            logger.error(f"Error syncing HUB: {e}")
            return self._fallback_sync(str(e))
    
    def append_risk(self, risk: Dict[str, Any]) -> Dict[str, Any]:
        """Append un risk dans HUB ORION"""
        logger.info(f"Appending risk: {risk.get('type', 'unknown')}")
        
        if not self.service:
            return {"status": "fallback", "message": "Sheets API not initialized"}
        
        try:
            spreadsheet_id = self.config["hub_orion"]["id"]
            timestamp = iapf_config.get_timestamp()
            
            risk_row = [
                timestamp,
                risk.get('level', 'unknown'),
                risk.get('type', 'unknown'),
                risk.get('message', ''),
                risk.get('source', 'mcp_cockpit')
            ]
            
            range_name = "RISKS!A:E"
            body = {'values': [risk_row]}
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            return {
                "status": "success",
                "risk_appended": risk,
                "rows_updated": result.get('updates', {}).get('updatedRows', 0)
            }
        
        except Exception as e:
            logger.error(f"Error appending risk: {e}")
            return {"status": "error", "message": str(e)}
    
    def append_conflict(self, conflict: Dict[str, Any]) -> Dict[str, Any]:
        """Append un conflict dans HUB ORION"""
        logger.info(f"Appending conflict: {conflict.get('type', 'unknown')}")
        
        if not self.service:
            return {"status": "fallback", "message": "Sheets API not initialized"}
        
        try:
            spreadsheet_id = self.config["hub_orion"]["id"]
            timestamp = iapf_config.get_timestamp()
            
            conflict_row = [
                timestamp,
                conflict.get('type', 'unknown'),
                conflict.get('source1', ''),
                conflict.get('source2', ''),
                conflict.get('description', '')
            ]
            
            range_name = "CONFLITS_DETECTES!A:E"
            body = {'values': [conflict_row]}
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            return {
                "status": "success",
                "conflict_appended": conflict,
                "rows_updated": result.get('updates', {}).get('updatedRows', 0)
            }
        
        except Exception as e:
            logger.error(f"Error appending conflict: {e}")
            return {"status": "error", "message": str(e)}
    
    def _fallback_audit(self, sheet_name: str, reason: str) -> Dict[str, Any]:
        """Fallback pour audit en cas d'erreur"""
        logger.warning(f"Using fallback audit for {sheet_name}: {reason}")
        return {
            "status": "fallback",
            "timestamp": iapf_config.get_timestamp(),
            "sheet_name": sheet_name,
            "message": reason,
            "risks": [{
                "level": "medium",
                "type": f"{sheet_name.lower()}_audit_failed",
                "message": f"Could not audit {sheet_name}: {reason}",
                "recommendation": "Check service account permissions and Sheets API setup"
            }]
        }
    
    def _fallback_sync(self, reason: str) -> Dict[str, Any]:
        """Fallback pour sync en cas d'erreur"""
        logger.warning(f"Using fallback sync: {reason}")
        return {
            "status": "fallback",
            "timestamp": iapf_config.get_timestamp(),
            "message": reason,
            "risks": [{
                "level": "high",
                "type": "hub_sync_failed",
                "message": f"Could not sync to HUB ORION: {reason}",
                "recommendation": "Check HUB ORION is shared with Editor access to service account"
            }]
        }


def get_sheets_tool() -> SheetsTool:
    """Factory pour obtenir le Sheets Tool"""
    return SheetsTool()
