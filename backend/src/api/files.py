"""File management routes."""

import json
import os
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import bcrypt
from fastapi import APIRouter, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response

from pydantic import BaseModel as _BaseModel

from src.models.file import (
    AccessLogEntry,
    FileDeleteResponse,
    FileListItem,
    FileListResponse,
    FileMetadataPublic,
    FileUploadResponse,
)
from src.services.access_log import get_access_log, log_access
from src.services.aleph_aggregates import (
    delete_metadata,
    get_metadata,
    list_metadata,
    store_metadata,
)
from src.services.aleph_storage import delete_file, download_file, upload_file
from src.services.auth_service import verify_signature


class _LinkPatchBody(_BaseModel):
    link_enabled: bool


router = APIRouter(prefix="/files", tags=["Files"])

# Config from env
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_BYTES", str(2 * 1024 * 1024 * 1024)))

# --- Per-file password attempt limiter ---
PASSWORD_MAX_ATTEMPTS = int(os.getenv("PASSWORD_MAX_ATTEMPTS", "5"))
PASSWORD_LOCKOUT_SECONDS = int(os.getenv("PASSWORD_LOCKOUT_SECONDS", "300"))


def _pw_attempts_dir() -> Path:
    return Path(os.getenv("LOCAL_DATA_DIR", "/tmp/aleph-fileshare")) / "pw_attempts"


def _check_password_lockout(file_hash: str, client_ip: str) -> None:
    """Raise 429 if too many failed password attempts for this file+IP."""
    safe_key = f"{file_hash}_{client_ip.replace(':', '_').replace('.', '_')}"
    path = _pw_attempts_dir() / f"{safe_key}.json"

    if not path.exists():
        return

    try:
        data = json.loads(path.read_text())
        attempts = data.get("attempts", 0)
        last_attempt = data.get("last_attempt", 0)

        # Reset after lockout period
        if time.time() - last_attempt > PASSWORD_LOCKOUT_SECONDS:
            path.unlink(missing_ok=True)
            return

        if attempts >= PASSWORD_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=429,
                detail=f"Too many password attempts. Try again in {PASSWORD_LOCKOUT_SECONDS} seconds.",
            )
    except (json.JSONDecodeError, OSError):
        return


def _record_password_failure(file_hash: str, client_ip: str) -> None:
    """Record a failed password attempt."""
    pw_dir = _pw_attempts_dir()
    pw_dir.mkdir(parents=True, exist_ok=True)
    safe_key = f"{file_hash}_{client_ip.replace(':', '_').replace('.', '_')}"
    path = pw_dir / f"{safe_key}.json"

    attempts = 0
    if path.exists():
        try:
            data = json.loads(path.read_text())
            attempts = data.get("attempts", 0)
        except (json.JSONDecodeError, OSError):
            pass

    try:
        path.write_text(json.dumps({"attempts": attempts + 1, "last_attempt": time.time()}))
    except OSError:
        pass


def _clear_password_attempts(file_hash: str, client_ip: str) -> None:
    """Clear failed attempts after successful password entry."""
    safe_key = f"{file_hash}_{client_ip.replace(':', '_').replace('.', '_')}"
    path = _pw_attempts_dir() / f"{safe_key}.json"
    path.unlink(missing_ok=True)
ALLOWED_MIME_TYPES_STR = os.getenv("ALLOWED_MIME_TYPES", "")
ALLOWED_MIME_TYPES: set[str] = (
    set(ALLOWED_MIME_TYPES_STR.split(",")) if ALLOWED_MIME_TYPES_STR else set()
)
APP_URL = os.getenv("NEXT_PUBLIC_API_URL", "http://localhost:3000")


def _verify_auth(
    wallet_address: Optional[str],
    wallet_signature: Optional[str],
    wallet_nonce: Optional[str],
) -> str:
    """Verify wallet auth headers and return the verified address.

    Raises HTTPException 401 if invalid.
    """
    if not wallet_address or not wallet_signature or not wallet_nonce:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication headers.",
        )

    if not verify_signature(wallet_address, wallet_signature, wallet_nonce):
        raise HTTPException(
            status_code=401,
            detail="Invalid wallet signature or expired nonce.",
        )

    return wallet_address


def _is_expired(expires_at: Optional[str]) -> bool:
    """Check if an expiry timestamp has passed."""
    if not expires_at:
        return False
    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= expiry
    except (ValueError, TypeError):
        return False


def _client_ip(request: Request) -> str:
    """Extract client IP from request."""
    return request.client.host if request.client else "unknown"


@router.post("/upload", response_model=FileUploadResponse, status_code=201)
async def upload(
    request: Request,
    file: UploadFile = File(...),
    public: bool = Form(True),
    filename_override: Optional[str] = Form(None),
    expires_in_hours: Optional[int] = Form(None),
    password: Optional[str] = Form(None),
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    x_wallet_signature: Optional[str] = Header(None, alias="X-Wallet-Signature"),
    x_wallet_nonce: Optional[str] = Header(None, alias="X-Wallet-Nonce"),
) -> FileUploadResponse:
    """Upload a file to IPFS and store metadata."""
    address = _verify_auth(x_wallet_address, x_wallet_signature, x_wallet_nonce)

    # Read file content
    content = await file.read()

    # Validate file size
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size is {MAX_FILE_SIZE} bytes.",
        )

    # Determine MIME type
    mime_type = file.content_type or "application/octet-stream"
    if ALLOWED_MIME_TYPES and mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"MIME type '{mime_type}' is not allowed.",
        )

    filename = filename_override or file.filename or "untitled"

    # Upload to storage
    file_hash = await upload_file(content, filename)

    # Compute expiry
    expires_at: Optional[str] = None
    if expires_in_hours and expires_in_hours > 0:
        expiry_ts = time.time() + (expires_in_hours * 3600)
        expires_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(expiry_ts))

    # Hash password if provided
    pw_hash: Optional[str] = None
    if password:
        pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    # Build metadata
    uploaded_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    metadata = {
        "hash": file_hash,
        "filename": filename,
        "mime_type": mime_type,
        "size_bytes": len(content),
        "public": public,
        "uploader": address,
        "uploaded_at": uploaded_at,
        "scan_status": "pending",
        "tags": [],
        "description": "",
        "expires_at": expires_at,
        "password_hash": pw_hash,
    }

    # Store metadata
    await store_metadata(file_hash, metadata)

    # Log access
    await log_access(file_hash, "upload", address, _client_ip(request))

    share_url = f"{APP_URL}/d/{file_hash}"

    return FileUploadResponse(
        hash=file_hash,
        filename=filename,
        mime_type=mime_type,
        size_bytes=len(content),
        public=public,
        share_url=share_url,
        uploaded_at=uploaded_at,
        expires_at=expires_at,
    )


@router.get("/{hash}/scan-status")
async def get_scan_status(hash: str) -> dict:
    """Quick check on a file's scan status and tags."""
    metadata = await get_metadata(hash)
    if not metadata:
        raise HTTPException(status_code=404, detail="File not found.")
    return {
        "hash": hash,
        "scan_status": metadata.get("scan_status", "pending"),
        "tags": metadata.get("tags", []),
        "description": metadata.get("description", ""),
    }


@router.get("/{hash}", response_model=FileMetadataPublic)
async def get_file_metadata(
    hash: str,
    request: Request,
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    x_wallet_signature: Optional[str] = Header(None, alias="X-Wallet-Signature"),
    x_wallet_nonce: Optional[str] = Header(None, alias="X-Wallet-Nonce"),
) -> FileMetadataPublic:
    """Get file metadata by hash."""
    metadata = await get_metadata(hash)
    if not metadata:
        raise HTTPException(status_code=404, detail="File not found.")

    # Private files require auth from the owner
    if not metadata.get("public", True):
        if not x_wallet_address or not x_wallet_signature or not x_wallet_nonce:
            raise HTTPException(status_code=403, detail="File is private.")
        if not verify_signature(x_wallet_address, x_wallet_signature, x_wallet_nonce):
            raise HTTPException(status_code=403, detail="File is private.")
        if x_wallet_address.lower() != metadata.get("uploader", "").lower():
            raise HTTPException(status_code=403, detail="File is private and you are not the owner.")

    # Log view access
    actor = x_wallet_address or "anonymous"
    await log_access(hash, "view", actor, _client_ip(request))

    # Build public response (no password_hash exposed)
    return FileMetadataPublic(
        hash=metadata["hash"],
        filename=metadata["filename"],
        mime_type=metadata["mime_type"],
        size_bytes=metadata["size_bytes"],
        public=metadata.get("public", True),
        uploader=metadata["uploader"],
        uploaded_at=metadata["uploaded_at"],
        scan_status=metadata.get("scan_status", "pending"),
        tags=metadata.get("tags", []),
        description=metadata.get("description", ""),
        expires_at=metadata.get("expires_at"),
        password_protected=bool(metadata.get("password_hash")),
        is_expired=_is_expired(metadata.get("expires_at")),
        link_enabled=metadata.get("link_enabled", True),
    )


@router.get("/{hash}/download")
async def download(
    hash: str,
    request: Request,
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    x_wallet_signature: Optional[str] = Header(None, alias="X-Wallet-Signature"),
    x_wallet_nonce: Optional[str] = Header(None, alias="X-Wallet-Nonce"),
    x_download_password: Optional[str] = Header(None, alias="X-Download-Password"),
) -> Response:
    """Download a file by hash."""
    metadata = await get_metadata(hash)
    if not metadata:
        raise HTTPException(status_code=404, detail="File not found.")

    # Check expiry
    if _is_expired(metadata.get("expires_at")):
        raise HTTPException(status_code=410, detail="This link has expired.")

    # Check if shared link has been revoked
    if not metadata.get("link_enabled", True):
        raise HTTPException(status_code=403, detail="This shared link has been revoked.")

    # Check access for private files
    if not metadata.get("public", True):
        if not x_wallet_address or not x_wallet_signature or not x_wallet_nonce:
            raise HTTPException(status_code=403, detail="File is private.")
        if not verify_signature(x_wallet_address, x_wallet_signature, x_wallet_nonce):
            raise HTTPException(status_code=403, detail="File is private.")
        if x_wallet_address.lower() != metadata.get("uploader", "").lower():
            raise HTTPException(status_code=403, detail="File is private and you are not the owner.")

    # Check password (with brute-force protection)
    stored_hash = metadata.get("password_hash")
    if stored_hash:
        ip = _client_ip(request)
        _check_password_lockout(hash, ip)

        if not x_download_password:
            raise HTTPException(status_code=401, detail="Password required.")
        if not bcrypt.checkpw(x_download_password.encode("utf-8"), stored_hash.encode("utf-8")):
            _record_password_failure(hash, ip)
            raise HTTPException(status_code=401, detail="Invalid password.")

        _clear_password_attempts(hash, ip)

    # Check scan status
    if metadata.get("scan_status") == "flagged":
        raise HTTPException(status_code=451, detail="File has been flagged and is unavailable.")

    file_content = await download_file(hash)
    if not file_content:
        raise HTTPException(status_code=404, detail="File not found on storage.")

    # Log download access
    actor = x_wallet_address or "anonymous"
    await log_access(hash, "download", actor, _client_ip(request))

    filename = metadata.get("filename", "download")
    mime_type = metadata.get("mime_type", "application/octet-stream")

    return Response(
        content=file_content,
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Length": str(len(file_content)),
        },
    )


@router.patch("/{hash}/link")
async def update_link(
    hash: str,
    body: _LinkPatchBody,
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    x_wallet_signature: Optional[str] = Header(None, alias="X-Wallet-Signature"),
    x_wallet_nonce: Optional[str] = Header(None, alias="X-Wallet-Nonce"),
) -> dict:
    """Enable or disable the shared link for a file (owner only)."""
    address = _verify_auth(x_wallet_address, x_wallet_signature, x_wallet_nonce)

    metadata = await get_metadata(hash)
    if not metadata:
        raise HTTPException(status_code=404, detail="File not found.")

    if metadata.get("uploader", "").lower() != address.lower():
        raise HTTPException(status_code=403, detail="Only the file owner can update link settings.")

    metadata["link_enabled"] = body.link_enabled
    await store_metadata(hash, metadata)

    return {"hash": hash, "link_enabled": body.link_enabled}


@router.delete("/{hash}", response_model=FileDeleteResponse)
async def delete(
    hash: str,
    request: Request,
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    x_wallet_signature: Optional[str] = Header(None, alias="X-Wallet-Signature"),
    x_wallet_nonce: Optional[str] = Header(None, alias="X-Wallet-Nonce"),
) -> FileDeleteResponse:
    """Delete a file (sends FORGET message)."""
    address = _verify_auth(x_wallet_address, x_wallet_signature, x_wallet_nonce)

    metadata = await get_metadata(hash)
    if not metadata:
        raise HTTPException(status_code=404, detail="File not found.")

    if metadata.get("uploader", "").lower() != address.lower():
        raise HTTPException(status_code=403, detail="Only the file owner can delete.")

    await delete_file(hash)
    await delete_metadata(hash)

    # Log delete access
    await log_access(hash, "delete", address, _client_ip(request))

    return FileDeleteResponse(
        message="File forget message submitted.",
        hash=hash,
    )


@router.get("/{hash}/access-log", response_model=list[AccessLogEntry])
async def file_access_log(
    hash: str,
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    x_wallet_signature: Optional[str] = Header(None, alias="X-Wallet-Signature"),
    x_wallet_nonce: Optional[str] = Header(None, alias="X-Wallet-Nonce"),
) -> list[AccessLogEntry]:
    """Get access log for a file (owner only)."""
    address = _verify_auth(x_wallet_address, x_wallet_signature, x_wallet_nonce)

    metadata = await get_metadata(hash)
    if not metadata:
        raise HTTPException(status_code=404, detail="File not found.")

    if metadata.get("uploader", "").lower() != address.lower():
        raise HTTPException(status_code=403, detail="Only the file owner can view access logs.")

    entries = await get_access_log(hash, limit=50)
    return [AccessLogEntry(**entry) for entry in entries]


@router.get("", response_model=FileListResponse)
async def list_files(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort: str = Query("uploaded_at_desc"),
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    x_wallet_signature: Optional[str] = Header(None, alias="X-Wallet-Signature"),
    x_wallet_nonce: Optional[str] = Header(None, alias="X-Wallet-Nonce"),
) -> FileListResponse:
    """List the authenticated user's files."""
    address = _verify_auth(x_wallet_address, x_wallet_signature, x_wallet_nonce)

    valid_sorts = {"uploaded_at_asc", "uploaded_at_desc", "size_asc", "size_desc"}
    if sort not in valid_sorts:
        raise HTTPException(status_code=400, detail=f"Invalid sort. Use one of: {valid_sorts}")

    items, total = await list_metadata(address, limit, offset, sort)

    files = [
        FileListItem(
            hash=item["hash"],
            filename=item["filename"],
            size_bytes=item["size_bytes"],
            uploaded_at=item["uploaded_at"],
            scan_status=item.get("scan_status", "pending"),
            tags=item.get("tags", []),
            expires_at=item.get("expires_at"),
            password_protected=bool(item.get("password_hash")),
            is_expired=_is_expired(item.get("expires_at")),
            link_enabled=item.get("link_enabled", True),
        )
        for item in items
    ]

    return FileListResponse(total=total, limit=limit, offset=offset, files=files)
