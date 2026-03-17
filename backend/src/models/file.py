"""Pydantic models for file operations."""


from typing import Optional

from pydantic import BaseModel, Field


class FileMetadata(BaseModel):
    """Full file metadata as stored in aggregates."""

    hash: str
    filename: str
    mime_type: str
    size_bytes: int
    public: bool = True
    uploader: str
    uploaded_at: str
    scan_status: str = "pending"
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    expires_at: Optional[str] = None
    password_hash: Optional[str] = None


class FileMetadataPublic(BaseModel):
    """Public file metadata (hides password_hash, adds computed fields)."""

    hash: str
    filename: str
    mime_type: str
    size_bytes: int
    public: bool = True
    uploader: str
    uploaded_at: str
    scan_status: str = "pending"
    tags: list[str] = Field(default_factory=list)
    description: str = ""
    expires_at: Optional[str] = None
    password_protected: bool = False
    is_expired: bool = False


class FileUploadResponse(BaseModel):
    """Response from POST /files/upload."""

    hash: str
    filename: str
    mime_type: str
    size_bytes: int
    public: bool
    share_url: str
    uploaded_at: str
    expires_at: Optional[str] = None


class FileListItem(BaseModel):
    """Abbreviated file info for list responses."""

    hash: str
    filename: str
    size_bytes: int
    uploaded_at: str
    scan_status: str = "pending"
    tags: list[str] = Field(default_factory=list)
    expires_at: Optional[str] = None
    password_protected: bool = False
    is_expired: bool = False


class FileListResponse(BaseModel):
    """Paginated file list response."""

    total: int
    limit: int
    offset: int
    files: list[FileListItem]


class FileDeleteResponse(BaseModel):
    """Response from DELETE /files/{hash}."""

    message: str
    hash: str


class ErrorResponse(BaseModel):
    """Standard error response."""

    detail: str
    code: str


class AccessLogEntry(BaseModel):
    """Single entry in the access log."""

    file_hash: str
    action: str
    actor: str
    ip: str
    timestamp: str
