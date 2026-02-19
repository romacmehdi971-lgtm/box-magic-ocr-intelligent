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
from datetime import datetime, timezone
import io
import uuid
import traceback

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
    
    def get_sheet_data(self, sheet_name: str, include_headers: bool = True, limit: Optional[int] = None) -> List[List[Any]]:
        """Get data from a sheet with optional limit
        
        Args:
            sheet_name: Name of the sheet to read
            include_headers: Whether to include the header row
            limit: Maximum number of data rows to return (excluding headers)
        
        Returns:
            List of rows, where each row is a list of cell values
        
        Raises:
            HttpError: If the API request fails
        """
        correlation_id = str(uuid.uuid4())
        try:
            # If limit is specified, use a bounded range
            if limit is not None and limit > 0:
                # +1 for header row, read a bit more to ensure we get enough data
                max_row = limit + 1
                range_name = f"{sheet_name}!A1:Z{max_row}"
                logger.info(f"[{correlation_id}] Reading {sheet_name} with limit={limit}, range={range_name}")
            else:
                range_name = f"{sheet_name}!A:Z"
                logger.info(f"[{correlation_id}] Reading entire sheet {sheet_name}")
            
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                majorDimension='ROWS'
            ).execute()
            
            values = result.get('values', [])
            logger.info(f"[{correlation_id}] Retrieved {len(values)} total rows from {sheet_name}")
            
            # Handle include_headers and limit
            if not values:
                return []
            
            if include_headers:
                # Return headers + limited data rows
                if limit is not None and limit > 0 and len(values) > 1:
                    # Header row + limit data rows
                    result_rows = values[:limit + 1]
                    logger.info(f"[{correlation_id}] Returning {len(result_rows)} rows (1 header + {len(result_rows)-1} data rows)")
                    return result_rows
                else:
                    return values
            else:
                # Exclude headers, return only data rows with limit
                data_rows = values[1:] if len(values) > 1 else []
                if limit is not None and limit > 0:
                    limited_data = data_rows[:limit]
                    logger.info(f"[{correlation_id}] Returning {len(limited_data)} data rows (no headers)")
                    return limited_data
                return data_rows
        except HttpError as e:
            # Extract error message from Google API
            error_message = str(e)
            if hasattr(e, 'error_details'):
                error_message = str(e.error_details)
            
            # Detect 404 cases (sheet not found or invalid range)
            is_not_found = any([
                "Unable to parse range" in error_message,
                "Requested entity was not found" in error_message,
                "not found" in error_message.lower()
            ])
            
            http_status = 404 if is_not_found else (e.resp.status if hasattr(e, 'resp') else 400)
            
            error_details = {
                "correlation_id": correlation_id,
                "sheet_name": sheet_name,
                "range": range_name if 'range_name' in locals() else 'unknown',
                "limit": limit,
                "http_status": http_status,
                "error_reason": error_message,
                "stack_trace": traceback.format_exc()
            }
            logger.error(f"[{correlation_id}] Failed to get data from {sheet_name}: {error_details}")
            # Store error details as an attribute for upstream handling
            e.proxy_error_details = error_details
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
    
    def insert_row_at_top(self, sheet_name: str, values: List[Any]) -> int:
        """Insert a row at position 2 (below headers) and push existing rows down
        
        This ensures new entries appear at the top of the sheet (reverse chronological order)
        
        Args:
            sheet_name: Name of the sheet
            values: List of cell values for the new row
        
        Returns:
            Row number where the row was inserted (always 2)
        """
        try:
            # Insert at row 2 (below header row 1)
            range_name = f"{sheet_name}!A2:Z2"
            
            # First, insert a blank row at position 2
            requests = [{
                "insertDimension": {
                    "range": {
                        "sheetId": self._get_sheet_id(sheet_name),
                        "dimension": "ROWS",
                        "startIndex": 1,  # 0-indexed, so 1 = row 2
                        "endIndex": 2
                    },
                    "inheritFromBefore": False
                }
            }]
            
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={"requests": requests}
            ).execute()
            
            # Then, write values to the newly inserted row 2
            body = {
                'values': [values]
            }
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=range_name,
                valueInputOption='USER_ENTERED',
                body=body
            ).execute()
            
            logger.info(f"Inserted row at top (row 2) in {sheet_name}")
            return 2
        except HttpError as e:
            logger.error(f"Failed to insert row at top of {sheet_name}: {e}")
            raise
    
    def append_row(self, sheet_name: str, values: List[Any]) -> int:
        """Append a row to a sheet and return the row number (legacy method)
        
        NOTE: For MEMORY_LOG, use insert_row_at_top() instead to maintain reverse chronological order
        """
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
    
    def _get_sheet_id(self, sheet_name: str) -> int:
        """Get the internal sheet ID for a sheet name"""
        try:
            result = self.service.spreadsheets().get(
                spreadsheetId=self.spreadsheet_id
            ).execute()
            
            for sheet in result.get('sheets', []):
                properties = sheet.get('properties', {})
                if properties.get('title') == sheet_name:
                    return properties.get('sheetId')
            
            raise ValueError(f"Sheet '{sheet_name}' not found")
        except Exception as e:
            logger.error(f"Failed to get sheet ID for {sheet_name}: {e}")
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
    
    @staticmethod
    def get_utc_timestamp() -> str:
        """Get current UTC timestamp in ISO 8601 format
        
        Returns:
            ISO 8601 timestamp string (e.g., '2026-02-17T04:30:15.123456Z')
        """
        return datetime.now(timezone.utc).isoformat()


# Global instance
_sheets_client: Optional[SheetsClient] = None


def get_sheets_client() -> SheetsClient:
    """Get or create the global SheetsClient instance"""
    global _sheets_client
    if _sheets_client is None:
        _sheets_client = SheetsClient()
    return _sheets_client
