"""
Connecteur Google Sheets

Écrit dans les feuilles existantes :
- INDEX GLOBAL
- CRM
- COMPTABILITÉ
- LOG SYSTEM
"""

import logging
from typing import Optional, List
from datetime import datetime

logger = logging.getLogger("OCREngine.Sheets")


class GoogleSheetsConnector:
    """
    Connecteur pour Google Sheets
    
    Écrit les résultats OCR dans les différentes feuilles du tableur BOX MAGIC
    """
    
    def __init__(self, credentials_path: Optional[str] = None, spreadsheet_id: Optional[str] = None):
        """
        Initialise le connecteur Google Sheets
        
        Args:
            credentials_path: Chemin vers les credentials Google API
            spreadsheet_id: ID du tableur Google Sheets
        """
        self.credentials_path = credentials_path
        self.spreadsheet_id = spreadsheet_id
        self.service = None
        
        if credentials_path and spreadsheet_id:
            self._init_service()
        else:
            logger.warning("Google Sheets connector initialized without credentials (dry-run mode)")
    
    def _init_service(self):
        """
        Initialise le service Google Sheets API
        
        Note : Implémentation à compléter avec google-api-python-client
        """
        try:
            # Import conditionnel (dépendance optionnelle)
            from googleapiclient.discovery import build
            from google.oauth2.service_account import Credentials
            
            # Scopes nécessaires
            SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
            
            # Authentification
            creds = Credentials.from_service_account_file(
                self.credentials_path,
                scopes=SCOPES
            )
            
            # Service
            self.service = build('sheets', 'v4', credentials=creds)
            
            logger.info("Google Sheets service initialized")
            
        except ImportError:
            logger.error("google-api-python-client not installed. Run: pip install google-api-python-client google-auth")
            self.service = None
        
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets service: {e}")
            self.service = None
    
    def _append_row(self, sheet_name: str, values: List) -> bool:
        """
        Ajoute une ligne dans une feuille
        
        Args:
            sheet_name: Nom de la feuille (ex: "INDEX GLOBAL")
            values: Liste des valeurs à ajouter
        
        Returns:
            True si succès
        """
        if not self.service:
            logger.debug(f"[DRY-RUN] Would append to {sheet_name}: {values}")
            return True
        
        try:
            range_name = f"{sheet_name}!A:Z"
            
            body = {
                'values': [values]
            }
            
            result = self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()
            
            logger.debug(f"Appended {result.get('updates', {}).get('updatedRows', 0)} rows to {sheet_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to append row to {sheet_name}: {e}")
            return False
    
    def write_to_index_global(self, ocr_result: 'OCRResult') -> bool:
        """
        Écrit dans la feuille INDEX GLOBAL
        
        Colonnes :
        - ID Document
        - Type
        - Date traitement
        - Entreprise source
        - Client/Fournisseur
        - Montant TTC
        - Statut OCR (niveau)
        - Confiance
        """
        client_fournisseur = ''
        if 'client' in ocr_result.fields:
            client_fournisseur = ocr_result.fields['client'].value
        elif 'fournisseur' in ocr_result.fields:
            client_fournisseur = ocr_result.fields['fournisseur'].value
        
        total_ttc = ocr_result.fields.get('total_ttc')
        total_ttc_value = total_ttc.value if total_ttc else None
        
        row = [
            ocr_result.document_id,
            ocr_result.document_type,
            ocr_result.processing_date.strftime("%Y-%m-%d %H:%M:%S"),
            ocr_result.entreprise_source,
            client_fournisseur,
            total_ttc_value,
            f"OCR Level {ocr_result.level}",
            f"{ocr_result.confidence:.2%}"
        ]
        
        success = self._append_row('INDEX GLOBAL', row)
        
        if success:
            logger.info(f"Written to INDEX GLOBAL: {ocr_result.document_id}")
        
        return success
    
    def write_to_crm(self, ocr_result: 'OCRResult') -> bool:
        """
        Écrit dans la feuille CRM (si nouveau client détecté)
        
        Colonnes :
        - Nom
        - SIRET
        - Adresse
        - Téléphone
        - Source détection
        - Date détection
        """
        client = ocr_result.fields.get('client')
        if not client:
            return False
        
        client_name = client.value
        
        # Vérifier si client déjà connu (simplifié)
        if self._is_new_client(client_name):
            client_siret = ocr_result.fields.get('client_siret')
            client_address = ocr_result.fields.get('client_address')
            client_phone = ocr_result.fields.get('client_phone')
            
            row = [
                client_name,
                client_siret.value if client_siret else '',
                client_address.value if client_address else '',
                client_phone.value if client_phone else '',
                f"OCR Detection - {ocr_result.document_id}",
                ocr_result.processing_date.strftime("%Y-%m-%d")
            ]
            
            success = self._append_row('CRM', row)
            
            if success:
                logger.info(f"New client added to CRM: {client_name}")
            
            return success
        
        return False
    
    def _is_new_client(self, client_name: str) -> bool:
        """
        Vérifie si le client est nouveau (pas déjà dans CRM)
        
        Note : Implémentation simplifiée
        Dans la vraie version, interroger le CRM existant
        """
        # Pour l'instant, considérer tous comme nouveaux
        # Dans la vraie implem : requête sur feuille CRM
        return True
    
    def write_to_comptabilite(self, ocr_result: 'OCRResult') -> bool:
        """
        Écrit dans la feuille COMPTABILITÉ
        
        Colonnes :
        - Référence
        - Type document
        - Date
        - Montant HT
        - Montant TVA
        - Montant TTC
        - Entreprise
        - Client/Fournisseur
        """
        reference = ocr_result.fields.get('reference')
        date_emission = ocr_result.fields.get('date_emission')
        total_ht = ocr_result.fields.get('total_ht')
        montant_tva = ocr_result.fields.get('montant_tva')
        total_ttc = ocr_result.fields.get('total_ttc')
        
        client_fournisseur = ''
        if 'client' in ocr_result.fields:
            client_fournisseur = ocr_result.fields['client'].value
        elif 'fournisseur' in ocr_result.fields:
            client_fournisseur = ocr_result.fields['fournisseur'].value
        
        row = [
            reference.value if reference else '',
            ocr_result.document_type,
            date_emission.value if date_emission else '',
            total_ht.value if total_ht else '',
            montant_tva.value if montant_tva else '',
            total_ttc.value if total_ttc else '',
            ocr_result.entreprise_source,
            client_fournisseur
        ]
        
        success = self._append_row('COMPTABILITÉ', row)
        
        if success:
            logger.info(f"Written to COMPTABILITÉ: {ocr_result.document_id}")
        
        return success
    
    def write_to_log_system(self, log_entry: dict) -> bool:
        """
        Écrit dans la feuille LOG SYSTEM
        
        Colonnes :
        - Timestamp
        - Level (INFO, WARNING, ERROR)
        - Document ID
        - OCR Level
        - Message
        - Décisions
        - Erreurs
        """
        row = [
            log_entry.get('timestamp', datetime.now().isoformat()),
            log_entry.get('level', 'INFO'),
            log_entry.get('document_id', ''),
            log_entry.get('ocr_level', ''),
            log_entry.get('message', ''),
            log_entry.get('decisions', ''),
            log_entry.get('errors', '')
        ]
        
        success = self._append_row('LOG SYSTEM', row)
        
        if success:
            logger.debug(f"Written to LOG SYSTEM: {log_entry.get('message', '')}")
        
        return success
    
    def get_config(self, key: str) -> Optional[str]:
        """
        Lit une valeur depuis la feuille CONFIG
        
        Args:
            key: Clé de configuration
        
        Returns:
            Valeur ou None
        """
        if not self.service:
            logger.debug(f"[DRY-RUN] Would read config: {key}")
            return None
        
        try:
            range_name = "CONFIG!A:B"
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            for row in values:
                if len(row) >= 2 and row[0] == key:
                    return row[1]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to read config {key}: {e}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test de connexion au tableur
        
        Returns:
            True si connexion OK
        """
        if not self.service:
            logger.warning("No service initialized (dry-run mode)")
            return False
        
        try:
            # Tenter de lire les métadonnées du tableur
            sheet_metadata = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            logger.info(f"Connected to spreadsheet: {sheet_metadata.get('properties', {}).get('title', 'Unknown')}")
            return True
            
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
