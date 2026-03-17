"""Pydantic models for file operations."""


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


class FileUploadResponse(BaseModel):
    """Response from POST /files/upload."""

    hash: str
    filename: str
    mime_type: str
    size_bytes: int
    public: bool
    share_url: str
    uploaded_at: str


class FileListItem(BaseModel):
    """Abbreviated file info for list responses."""

    hash: str
    filename: str
    size_bytes: int
    uploaded_at: str
    scan_status: str = "pending"
    tags: list[str] = Field(default_factory=list)


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
