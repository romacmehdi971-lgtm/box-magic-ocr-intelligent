"""
MCP Memory Proxy - Google Drive API v3 Client
Date: 2026-02-20
Purpose: Real Google Drive API integration (Phase 2 - CRITICAL FIX)

Service Account: mcp-cockpit@box-magique-gp-prod.iam.gserviceaccount.com
Root Folder: 1LwUZ67zVstl2tuogcdYYihPilUAXQai3 (ARCHIVES)

Endpoints:
- get_file_metadata(file_id) → dict with real metadata
- list_folder_tree(folder_id, max_depth, limit) → recursive tree structure
- search_files(query, folder_id, limit) → list of matching files
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from typing import Dict, List, Optional, Any
import os
from datetime import datetime

# Service account configuration
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/app/sa-key.json")
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly'
]

# Default root folder (ARCHIVES)
DEFAULT_ROOT_FOLDER = "1LwUZ67zVstl2tuogcdYYihPilUAXQai3"

def get_drive_service():
    """
    Create authenticated Drive API v3 service
    """
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    service = build('drive', 'v3', credentials=credentials)
    return service


def get_file_metadata(file_id: str) -> Dict[str, Any]:
    """
    Get real metadata for a Drive file or folder
    
    Args:
        file_id: Google Drive file/folder ID
        
    Returns:
        Dict with file metadata (name, mimeType, size, dates, owners, capabilities)
        
    Raises:
        Exception if file not found or access denied
    """
    service = get_drive_service()
    
    # Fields to retrieve (comprehensive)
    fields = (
        "id,name,mimeType,size,createdTime,modifiedTime,"
        "owners,permissions,capabilities,webViewLink,iconLink,"
        "trashed,parents,shared,sharingUser"
    )
    
    try:
        file = service.files().get(
            fileId=file_id,
            fields=fields,
            supportsAllDrives=True
        ).execute()
        
        # Format response
        metadata = {
            "id": file.get("id"),
            "name": file.get("name"),
            "mimeType": file.get("mimeType"),
            "size": int(file.get("size", 0)) if file.get("size") else 0,
            "createdTime": file.get("createdTime"),
            "modifiedTime": file.get("modifiedTime"),
            "owners": [
                {
                    "email": owner.get("emailAddress", "[REDACTED]"),
                    "displayName": owner.get("displayName", "[REDACTED]")
                }
                for owner in file.get("owners", [])
            ],
            "capabilities": file.get("capabilities", {}),
            "webViewLink": file.get("webViewLink"),
            "iconLink": file.get("iconLink"),
            "trashed": file.get("trashed", False),
            "parents": file.get("parents", []),
            "shared": file.get("shared", False)
        }
        
        return metadata
        
    except Exception as e:
        raise Exception(f"Drive API error for file {file_id}: {str(e)}")


def list_folder_tree(
    folder_id: str,
    max_depth: int = 3,
    limit: int = 100,
    current_depth: int = 0
) -> Dict[str, Any]:
    """
    Recursively list folder structure (tree)
    
    Args:
        folder_id: Root folder ID to scan
        max_depth: Maximum recursion depth (default 3)
        limit: Max items per folder (default 100)
        current_depth: Internal counter for recursion
        
    Returns:
        Dict with folder tree structure
    """
    service = get_drive_service()
    
    # Get folder metadata
    try:
        folder_meta = get_file_metadata(folder_id)
    except Exception as e:
        return {
            "folder_id": folder_id,
            "error": str(e),
            "total_items": 0,
            "tree": []
        }
    
    # Query children
    query = f"'{folder_id}' in parents and trashed=false"
    
    try:
        results = service.files().list(
            q=query,
            pageSize=min(limit, 1000),  # Drive API max is 1000
            fields="files(id,name,mimeType,size,modifiedTime,owners)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            orderBy="folder,name"
        ).execute()
        
        files = results.get("files", [])
        
        # Build tree
        tree = []
        for file in files:
            item = {
                "id": file.get("id"),
                "name": file.get("name"),
                "mimeType": file.get("mimeType"),
                "size": int(file.get("size", 0)) if file.get("size") else 0,
                "modifiedTime": file.get("modifiedTime"),
                "type": "folder" if file.get("mimeType") == "application/vnd.google-apps.folder" else "file"
            }
            
            # Recursive call for folders (if depth allows)
            if (item["type"] == "folder" and 
                current_depth < max_depth and 
                len(tree) < limit):
                
                subtree = list_folder_tree(
                    file.get("id"),
                    max_depth=max_depth,
                    limit=limit,
                    current_depth=current_depth + 1
                )
                item["children"] = subtree.get("tree", [])
                item["children_count"] = len(item["children"])
            
            tree.append(item)
        
        return {
            "folder_id": folder_id,
            "folder_name": folder_meta.get("name"),
            "total_items": len(tree),
            "tree": tree,
            "depth": current_depth
        }
        
    except Exception as e:
        return {
            "folder_id": folder_id,
            "error": f"Drive API list error: {str(e)}",
            "total_items": 0,
            "tree": []
        }


def search_files(
    query: str,
    folder_id: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search files in Drive (optionally scoped to folder)
    
    Args:
        query: Search query (name contains, fullText contains, etc.)
        folder_id: Optional folder to scope search
        limit: Max results (default 10)
        
    Returns:
        Dict with search results
    """
    service = get_drive_service()
    
    # Build Drive API query
    # Format: name contains 'query' or fullText contains 'query'
    drive_query = f"name contains '{query}' and trashed=false"
    
    if folder_id:
        drive_query = f"'{folder_id}' in parents and " + drive_query
    
    try:
        results = service.files().list(
            q=drive_query,
            pageSize=min(limit, 1000),
            fields="files(id,name,mimeType,size,modifiedTime,owners,webViewLink)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            orderBy="modifiedTime desc"
        ).execute()
        
        files = results.get("files", [])
        
        # Format results
        formatted_files = [
            {
                "id": f.get("id"),
                "name": f.get("name"),
                "mimeType": f.get("mimeType"),
                "size": int(f.get("size", 0)) if f.get("size") else 0,
                "modifiedTime": f.get("modifiedTime"),
                "webViewLink": f.get("webViewLink"),
                "type": "folder" if f.get("mimeType") == "application/vnd.google-apps.folder" else "file"
            }
            for f in files
        ]
        
        return {
            "query": query,
            "folder_id": folder_id,
            "total_results": len(formatted_files),
            "files": formatted_files,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
    except Exception as e:
        return {
            "query": query,
            "folder_id": folder_id,
            "error": f"Drive API search error: {str(e)}",
            "total_results": 0,
            "files": []
        }


def read_file_text(file_id: str, max_bytes: int = 10000) -> Dict[str, Any]:
    """
    Read text content from a Drive file (bounded)
    
    Args:
        file_id: Google Drive file ID
        max_bytes: Maximum bytes to read (default 10KB)
        
    Returns:
        Dict with text content (or error)
    """
    service = get_drive_service()
    
    try:
        # Get file metadata first
        metadata = get_file_metadata(file_id)
        mime_type = metadata.get("mimeType")
        
        # Check if it's a text-readable type
        text_types = [
            "text/plain",
            "text/html",
            "text/csv",
            "application/json",
            "application/javascript",
            "application/xml"
        ]
        
        if mime_type not in text_types and not mime_type.startswith("text/"):
            return {
                "file_id": file_id,
                "error": f"Cannot read text from mimeType: {mime_type}",
                "text": None
            }
        
        # Export/download content
        request = service.files().get_media(fileId=file_id)
        content = request.execute()
        
        # Decode and truncate
        text = content.decode("utf-8", errors="replace")
        if len(text) > max_bytes:
            text = text[:max_bytes] + f"\n\n[TRUNCATED - {len(text)} total bytes]"
        
        return {
            "file_id": file_id,
            "name": metadata.get("name"),
            "mimeType": mime_type,
            "size": len(content),
            "text": text,
            "truncated": len(content) > max_bytes
        }
        
    except Exception as e:
        return {
            "file_id": file_id,
            "error": f"Drive API read error: {str(e)}",
            "text": None
        }
