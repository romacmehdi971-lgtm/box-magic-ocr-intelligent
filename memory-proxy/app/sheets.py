"""
MCP Memory Proxy - Google Sheets Integration
Date: 2026-02-15
Purpose: Google Sheets API wrapper for reading/writing Hub data
"""
import logging
from typing import List, Dict, Any, Optional
from google.oauth2 import service_account
from google.auth import default
import os
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from datetime import datetime
import io

from .config import (
    GOOGLE_SHEET_ID,
    SERVICE_ACCOUNT_KEY_PATH,
    EXPECTED_TABS,
    MEMORY_LOG_SHEET,
    PROPOSITIONS_PENDING_SHEET,
    SETTINGS_SHEET,
    SNAPSHOT_SHEET
)

logger = logging.getLogger(__name__)

# Google Sheets API scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.file'
]


class SheetsClient:
    """Google Sheets API client"""
    
    def __init__(self):
        """Initialize the Sheets client with service account credentials"""
        try:
            # Try to use service account key file if provided (for local dev)
            if os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
                logger.info(f"Using service account key file: {SERVICE_ACCOUNT_KEY_PATH}")
                self.credentials = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_KEY_PATH,
                    scopes=SCOPES
                )
            else:
                # Use Application Default Credentials (for Cloud Run)
                logger.info("Using Application Default Credentials")
                credentials, project = default(scopes=SCOPES)
                self.credentials = credentials
            
            self.service = build('sheets', 'v4', credentials=self.credentials)
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            self.spreadsheet_id = GOOGLE_SHEET_ID
            logger.info(f"Sheets client initialized for spreadsheet {GOOGLE_SHEET_ID}")
        except Exception as e:
            logger.error(f"Failed to initialize Sheets client: {e}")
            raise
    
    def test_connection(self) -> bool:
        """Test connection to Google Sheets"""
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            logger.info(f"Successfully connected to sheet: {result.get('properties', {}).get('title')}")
            return True
        except HttpError as e:
            logger.error(f"Failed to connect to Google Sheets: {e}")
            return False
    
    def list_sheets(self) -> List[Dict[str, Any]]:
        """List all sheets in the spreadsheet"""
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            sheets = result.get('sheets', [])
            
            sheet_info = []
            for sheet in sheets:
                properties = sheet.get('properties', {})
                sheet_name = properties.get('title')
                
                # Get row/column count
                grid_properties = properties.get('gridProperties', {})
                row_count = grid_properties.get('rowCount', 0)
                column_count = grid_properties.get('columnCount', 0)
                
                # Get headers
                headers = self.get_headers(sheet_name)
                
                sheet_info.append({
                    'name': sheet_name,
                    'row_count': row_count,
                    'column_count': column_count,
                    'headers': headers
                })
            
            logger.info(f"Listed {len(sheet_info)} sheets")
            return sheet_info
        except HttpError as e:
            logger.error(f"Failed to list sheets: {e}")
            raise
    
    def get_headers(self, sheet_name: str) -> List[str]:
        """Get header row from a sheet"""
        try:
            range_name = f"{sheet_name}!A1:ZZ1"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if values:
                return values[0]
            return []
        except HttpError as e:
            logger.warning(f"Failed to get headers for {sheet_name}: {e}")
            return []
    
    def get_sheet_data(self, sheet_name: str, include_headers: bool = True) -> List[List[Any]]:
        """Get all data from a sheet"""
        try:
            range_name = f"{sheet_name}!A:ZZ"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            
            if not include_headers and values:
                return values[1:]
            
            return values
        except HttpError as e:
            logger.error(f"Failed to get data from {sheet_name}: {e}")
            raise
    
    def get_sheet_as_dict(self, sheet_name: str) -> List[Dict[str, Any]]:
        """Get sheet data as list of dictionaries"""
        data = self.get_sheet_data(sheet_name, include_headers=True)
        
        if not data or len(data) < 1:
            return []
        
        headers = data[0]
        rows = data[1:]
        
        result = []
        for row in rows:
            # Pad row to match headers length
            padded_row = row + [''] * (len(headers) - len(row))
            row_dict = dict(zip(headers, padded_row))
            result.append(row_dict)
        
        return result
    
    def append_row(self, sheet_name: str, values: List[Any]) -> int:
        """Append a row to a sheet and return the row number"""
        try:
            range_name = f"{sheet_name}!A:A"
            
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
            
            # Extract row number from update range (e.g., "MEMORY_LOG!A157:F157")
            updated_range = result.get('updates', {}).get('updatedRange', '')
            if '!' in updated_range:
                range_part = updated_range.split('!')[1]
                if ':' in range_part:
                    row_num = int(range_part.split(':')[0][1:])  # Extract number from "A157"
                    logger.info(f"Appended row {row_num} to {sheet_name}")
                    return row_num
            
            logger.warning(f"Could not determine row number for append to {sheet_name}")
            return -1
        except HttpError as e:
            logger.error(f"Failed to append row to {sheet_name}: {e}")
            raise
    
    def update_row(self, sheet_name: str, row_number: int, values: List[Any]) -> bool:
        """Update a specific row in a sheet"""
        try:
            range_name = f"{sheet_name}!A{row_number}:ZZ{row_number}"
            
            body = {
                'values': [values]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logger.info(f"Updated row {row_number} in {sheet_name}")
            return True
        except HttpError as e:
            logger.error(f"Failed to update row {row_number} in {sheet_name}: {e}")
            raise
    
    def get_row(self, sheet_name: str, row_number: int) -> List[Any]:
        """Get a specific row from a sheet"""
        try:
            range_name = f"{sheet_name}!A{row_number}:ZZ{row_number}"
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if values:
                return values[0]
            return []
        except HttpError as e:
            logger.error(f"Failed to get row {row_number} from {sheet_name}: {e}")
            raise
    
    def export_sheet_as_xlsx(self, output_path: str) -> bool:
        """Export entire spreadsheet as XLSX file"""
        try:
            # Use Drive API to export as XLSX
            request = self.drive_service.files().export_media(
                fileId=self.spreadsheet_id,
                mimeType='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            
            # Write to output file
            with open(output_path, 'wb') as f:
                f.write(fh.getvalue())
            
            logger.info(f"Exported spreadsheet to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export spreadsheet: {e}")
            return False
    
    def upload_to_drive(self, file_path: str, file_name: str, folder_id: Optional[str] = None) -> str:
        """Upload a file to Google Drive and return the file ID"""
        try:
            file_metadata = {
                'name': file_name
            }
            
            if folder_id:
                file_metadata['parents'] = [folder_id]
            
            media = MediaFileUpload(file_path, resumable=True)
            
            file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file.get('id')
            logger.info(f"Uploaded file {file_name} to Drive with ID {file_id}")
            return file_id
        except Exception as e:
            logger.error(f"Failed to upload file to Drive: {e}")
            raise
    
    def get_settings(self) -> Dict[str, str]:
        """Get settings from SETTINGS sheet"""
        try:
            data = self.get_sheet_as_dict(SETTINGS_SHEET)
            settings = {}
            for row in data:
                key = row.get('key', '')
                value = row.get('value', '')
                if key:
                    settings[key] = value
            return settings
        except Exception as e:
            logger.error(f"Failed to get settings: {e}")
            return {}


# Global instance
_sheets_client: Optional[SheetsClient] = None


def get_sheets_client() -> SheetsClient:
    """Get or create the global SheetsClient instance"""
    global _sheets_client
    if _sheets_client is None:
        _sheets_client = SheetsClient()
    return _sheets_client
