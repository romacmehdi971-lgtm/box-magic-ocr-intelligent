"""
Drive Markdown governed write helper
Adds append_end / replace_section with SHA-256 guard and optional dry_run.
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from typing import Dict, Any, Optional
import google.auth
import os
import io
import hashlib

SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "/app/sa-key.json")
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]

ALLOWED_MIME_TYPES = {"text/markdown", "text/x-markdown"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


def get_drive_service():
    """Create authenticated Drive API v3 service with write scope."""
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
    else:
        credentials, _ = google.auth.default(scopes=SCOPES)

    return build("drive", "v3", credentials=credentials)


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _read_markdown(service, file_id: str) -> Dict[str, Any]:
    metadata = service.files().get(
        fileId=file_id,
        fields="id,name,mimeType,size,modifiedTime",
        supportsAllDrives=True
    ).execute()

    mime_type = metadata.get("mimeType", "")
    size = int(metadata.get("size", 0) or 0)

    if mime_type not in ALLOWED_MIME_TYPES:
        return {
            "ok": False,
            "status_code": 403,
            "error": f"Forbidden mimeType: {mime_type}. Allowed: {sorted(ALLOWED_MIME_TYPES)}",
            "file": metadata,
        }

    if size > MAX_FILE_SIZE_BYTES:
        return {
            "ok": False,
            "status_code": 413,
            "error": f"File too large: {size} bytes. Max: {MAX_FILE_SIZE_BYTES}",
            "file": metadata,
        }

    request = service.files().get_media(fileId=file_id)
    content_bytes = request.execute()
    try:
        content_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        content_text = content_bytes.decode("latin-1")

    return {
        "ok": True,
        "status_code": 200,
        "file": metadata,
        "content_text": content_text,
        "sha256": _sha256_text(content_text),
    }


def _apply_replace_section(content_text: str, new_section: str, section_start_marker: str, section_end_marker: str) -> str:
    start_idx = content_text.find(section_start_marker)
    end_idx = content_text.find(section_end_marker)

    if start_idx == -1 or end_idx == -1:
        raise ValueError("Section markers not found")

    end_idx = end_idx + len(section_end_marker)
    return content_text[:start_idx] + new_section + content_text[end_idx:]


def markdown_upsert(
    file_id: str,
    mode: str,
    content: str,
    expected_sha256: Optional[str] = None,
    section_start_marker: Optional[str] = None,
    section_end_marker: Optional[str] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """
    Governed markdown upsert for a Drive file.

    Modes:
    - append_end
    - replace_section
    """
    service = get_drive_service()
    current = _read_markdown(service, file_id)

    if not current.get("ok"):
        return current

    metadata = current["file"]
    old_text = current["content_text"]
    previous_sha256 = current["sha256"]

    if expected_sha256 and expected_sha256 != previous_sha256:
        return {
            "ok": False,
            "status_code": 409,
            "error": f"SHA256 mismatch: expected {expected_sha256}, got {previous_sha256}",
            "file": metadata,
            "previous_sha256": previous_sha256,
        }

    replaced_section = False

    if mode == "append_end":
        new_text = old_text + content
    elif mode == "replace_section":
        if not section_start_marker or not section_end_marker:
            return {
                "ok": False,
                "status_code": 400,
                "error": "replace_section requires section_start_marker and section_end_marker",
                "file": metadata,
                "previous_sha256": previous_sha256,
            }
        new_text = _apply_replace_section(
            content_text=old_text,
            new_section=content,
            section_start_marker=section_start_marker,
            section_end_marker=section_end_marker,
        )
        replaced_section = True
    else:
        return {
            "ok": False,
            "status_code": 400,
            "error": f"Unsupported mode: {mode}",
            "file": metadata,
            "previous_sha256": previous_sha256,
        }

    new_sha256 = _sha256_text(new_text)
    bytes_written = len(new_text.encode("utf-8"))

    if dry_run:
        return {
            "ok": True,
            "status_code": 200,
            "file": metadata,
            "previous_sha256": previous_sha256,
            "new_sha256": new_sha256,
            "bytes_written": bytes_written,
            "replaced_section": replaced_section,
            "applied": False,
            "message": "DRY_RUN: markdown upsert simulated"
        }

    media = MediaIoBaseUpload(
        io.BytesIO(new_text.encode("utf-8")),
        mimetype=metadata.get("mimeType") or "text/markdown",
        resumable=False
    )

    updated = service.files().update(
        fileId=file_id,
        media_body=media,
        supportsAllDrives=True,
        fields="id,name,mimeType,modifiedTime,size"
    ).execute()

    return {
        "ok": True,
        "status_code": 200,
        "file": updated,
        "previous_sha256": previous_sha256,
        "new_sha256": new_sha256,
        "bytes_written": bytes_written,
        "replaced_section": replaced_section,
        "applied": True,
        "message": "Markdown upsert applied"
    }

