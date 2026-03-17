"""File management routes."""

import os
import time
from typing import Optional

from fastapi import APIRouter, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import Response

from src.models.file import (
    FileDeleteResponse,
    FileListItem,
    FileListResponse,
    FileMetadata,
    FileUploadResponse,
)
from src.services.aleph_aggregates import (
    delete_metadata,
    get_metadata,
    list_metadata,
    store_metadata,
)
from src.services.aleph_storage import delete_file, download_file, upload_file
from src.services.auth_service import verify_signature

router = APIRouter(prefix="/files", tags=["Files"])

# Config from env
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_BYTES", str(2 * 1024 * 1024 * 1024)))
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


@router.post("/upload", response_model=FileUploadResponse, status_code=201)
async def upload(
    file: UploadFile = File(...),
    public: bool = Form(True),
    filename_override: Optional[str] = Form(None),
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
    }

    # Store metadata
    await store_metadata(file_hash, metadata)

    share_url = f"{APP_URL}/d/{file_hash}"

    return FileUploadResponse(
        hash=file_hash,
        filename=filename,
        mime_type=mime_type,
        size_bytes=len(content),
        public=public,
        share_url=share_url,
        uploaded_at=uploaded_at,
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


@router.get("/{hash}", response_model=FileMetadata)
async def get_file_metadata(
    hash: str,
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    x_wallet_signature: Optional[str] = Header(None, alias="X-Wallet-Signature"),
    x_wallet_nonce: Optional[str] = Header(None, alias="X-Wallet-Nonce"),
) -> FileMetadata:
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

    return FileMetadata(**metadata)


@router.get("/{hash}/download")
async def download(
    hash: str,
    x_wallet_address: Optional[str] = Header(None, alias="X-Wallet-Address"),
    x_wallet_signature: Optional[str] = Header(None, alias="X-Wallet-Signature"),
    x_wallet_nonce: Optional[str] = Header(None, alias="X-Wallet-Nonce"),
) -> Response:
    """Download a file by hash."""
    metadata = await get_metadata(hash)
    if not metadata:
        raise HTTPException(status_code=404, detail="File not found.")

    # Check access for private files
    if not metadata.get("public", True):
        if not x_wallet_address or not x_wallet_signature or not x_wallet_nonce:
            raise HTTPException(status_code=403, detail="File is private.")
        if not verify_signature(x_wallet_address, x_wallet_signature, x_wallet_nonce):
            raise HTTPException(status_code=403, detail="File is private.")
        if x_wallet_address.lower() != metadata.get("uploader", "").lower():
            raise HTTPException(status_code=403, detail="File is private and you are not the owner.")

    # Check scan status
    if metadata.get("scan_status") == "flagged":
        raise HTTPException(status_code=451, detail="File has been flagged and is unavailable.")

    file_content = await download_file(hash)
    if not file_content:
        raise HTTPException(status_code=404, detail="File not found on storage.")

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


@router.delete("/{hash}", response_model=FileDeleteResponse)
async def delete(
    hash: str,
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

    return FileDeleteResponse(
        message="File forget message submitted.",
        hash=hash,
    )


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
        )
        for item in items
    ]

    return FileListResponse(total=total, limit=limit, offset=offset, files=files)
