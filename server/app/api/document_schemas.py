"""Document Management API – Pydantic schemas.

These models are appended by the documents feature and imported into the
router.  They follow the same style as the existing schemas in schemas.py.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared / embedded
# ---------------------------------------------------------------------------

class DocumentSummary(BaseModel):
    """Lightweight representation returned by GET /documents."""

    id: UUID
    filename: str
    status: str
    status_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0


class DocumentDetail(BaseModel):
    """Full representation returned by GET /documents/{document_id}."""

    id: UUID
    filename: str
    file_hash: str
    source_path: str | None = None
    status: str
    status_message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
    chunk_count: int = 0
    total_chars: int = 0


# ---------------------------------------------------------------------------
# List response (paginated)
# ---------------------------------------------------------------------------

class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    total: int
    limit: int
    offset: int
    items: list[DocumentSummary]


# ---------------------------------------------------------------------------
# Upload response
# ---------------------------------------------------------------------------

class DocumentUploadResponse(BaseModel):
    """Returned after a successful POST /documents/upload."""

    document_id: UUID
    filename: str
    status: str
    chunk_count: int
    message: str


# ---------------------------------------------------------------------------
# Delete response
# ---------------------------------------------------------------------------

class DocumentDeleteResponse(BaseModel):
    """Returned after a successful DELETE /documents/{document_id}."""

    document_id: UUID
    deleted: bool
    message: str
