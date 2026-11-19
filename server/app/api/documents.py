"""Document Management API router.

Endpoints
---------
GET  /documents
    List all indexed documents with pagination and optional status filter.

GET  /documents/{document_id}
    Retrieve full detail for a single document (chunk count, metadata, etc.).

POST /documents/upload
    Upload a new document (PDF, DOCX, TXT, MD) and trigger the ingestion
    pipeline.  Duplicate files (same SHA-256 hash) are re-ingested rather
    than rejected so a user can re-upload a corrected version.

DELETE /documents/{document_id}
    Remove a document and all associated vector/full-text chunks from the
    database.  The original file on disk is left intact.

All endpoints require a valid Bearer token (same JWT auth used by the
sessions API).
"""

import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from app.api.auth import get_current_user
from app.api.document_schemas import (
    DocumentDeleteResponse,
    DocumentDetail,
    DocumentListResponse,
    DocumentSummary,
    DocumentUploadResponse,
)
from app.database.chunk_repository import delete_document, get_document
from app.database.document_repository import (
    count_documents,
    get_document_detail,
    list_documents,
)
from app.ingestion.pipeline import ingest_file
from app.observability import observation_span, set_span_output

router = APIRouter(prefix="/documents", tags=["documents"])

# Supported upload extensions
_ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".markdown"}

# Default directory for storing uploaded files (relative to CWD or via env var)
_UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "storage/uploads"))


def _resolve_upload_dir() -> Path:
    upload_dir = _UPLOAD_DIR.expanduser().resolve()
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def _validate_extension(filename: str) -> str:
    """Return the lower-case extension or raise 422 for unsupported types."""
    ext = Path(filename).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Unsupported file type '{ext}'. "
                f"Allowed: {', '.join(sorted(_ALLOWED_EXTENSIONS))}"
            ),
        )
    return ext


# ---------------------------------------------------------------------------
# GET /documents
# ---------------------------------------------------------------------------

@router.get("", response_model=DocumentListResponse)
def list_all_documents(
    _user: Annotated[dict, Depends(get_current_user)],
    doc_status: Annotated[str | None, Query(alias="status", description="Filter by document status")] = None,
    limit: Annotated[int, Query(ge=1, le=200, description="Max results to return")] = 50,
    offset: Annotated[int, Query(ge=0, description="Number of results to skip")] = 0,
):
    """Return a paginated list of all indexed documents."""
    with observation_span(
        "rag.api.documents.list",
        input_value={"status_filter": doc_status, "limit": limit, "offset": offset},
    ) as span:
        docs = list_documents(status=doc_status, limit=limit, offset=offset)
        total = count_documents(status=doc_status)
        set_span_output(span, {"total": total, "returned": len(docs)})

    return DocumentListResponse(
        total=total,
        limit=limit,
        offset=offset,
        items=[DocumentSummary(**doc) for doc in docs],
    )


# ---------------------------------------------------------------------------
# GET /documents/{document_id}
# ---------------------------------------------------------------------------

@router.get("/{document_id}", response_model=DocumentDetail)
def get_single_document(
    document_id: UUID,
    _user: Annotated[dict, Depends(get_current_user)],
):
    """Return full detail for a single document."""
    with observation_span(
        "rag.api.documents.get",
        input_value={"document_id": str(document_id)},
    ) as span:
        doc = get_document_detail(document_id)
        if doc is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found.",
            )
        set_span_output(span, {"status": doc["status"], "chunks": doc["chunk_count"]})

    return DocumentDetail(**doc)


# ---------------------------------------------------------------------------
# POST /documents/upload
# ---------------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    _user: Annotated[dict, Depends(get_current_user)],
    file: Annotated[UploadFile, File(description="Document file (PDF, DOCX, TXT, MD)")],
):
    """Upload and ingest a new document into the RAG knowledge base.

    * Allowed types: ``.pdf``, ``.docx``, ``.txt``, ``.md`` / ``.markdown``
    * Duplicate uploads (same file hash) **re-ingest** the document, allowing
      users to push an updated version without deleting the old one first.
    * The uploaded file is stored in ``UPLOAD_DIR`` (default: ``storage/uploads/``)
      so the document can be re-indexed later via the CLI ``reindex`` command.
    """
    _validate_extension(file.filename or "")

    upload_dir = _resolve_upload_dir()

    # Read the full file content once so we can:
    #  1. compute a SHA-256 hash for deduplication
    #  2. persist it to disk for the ingestion pipeline
    content = file.file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty.",
        )

    file_hash = hashlib.sha256(content).hexdigest()
    safe_filename = Path(file.filename or "upload").name  # strip any directory components
    dest_path = upload_dir / safe_filename

    # If a file with the same name already exists, keep both by adding the
    # hash prefix only when names collide and hashes differ.
    if dest_path.exists():
        existing_hash = hashlib.sha256(dest_path.read_bytes()).hexdigest()
        if existing_hash != file_hash:
            dest_path = upload_dir / f"{file_hash[:8]}_{safe_filename}"

    with observation_span(
        "rag.api.documents.upload",
        input_value={"filename": safe_filename, "size_bytes": len(content)},
    ) as span:
        # Write to a temp file first; rename atomically on success.
        try:
            with tempfile.NamedTemporaryFile(dir=upload_dir, delete=False) as tmp:
                tmp.write(content)
                tmp_path = Path(tmp.name)
            shutil.move(str(tmp_path), str(dest_path))
        except OSError as exc:
            # Clean up temp file if something went wrong
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save uploaded file: {exc}",
            ) from exc

        # Trigger the ingestion pipeline (extract → chunk → embed → store)
        try:
            document_id = ingest_file(dest_path)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ingestion failed: {exc}",
            ) from exc

        # Fetch the final chunk count for the response
        doc_record = get_document(document_id)
        doc_detail = get_document_detail(document_id)
        chunk_count = doc_detail["chunk_count"] if doc_detail else 0

        set_span_output(span, {
            "document_id": str(document_id),
            "chunk_count": chunk_count,
            "dest_path": str(dest_path),
        })

    return DocumentUploadResponse(
        document_id=document_id,
        filename=safe_filename,
        status=doc_record["status"] if doc_record else "completed",
        chunk_count=chunk_count,
        message=f"Document '{safe_filename}' ingested successfully with {chunk_count} chunks.",
    )


# ---------------------------------------------------------------------------
# DELETE /documents/{document_id}
# ---------------------------------------------------------------------------

@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
def remove_document(
    document_id: UUID,
    _user: Annotated[dict, Depends(get_current_user)],
):
    """Delete a document and all its indexed chunks from the knowledge base.

    The original file on disk is **not** removed – only the database records
    (document row + all associated ``document_chunks`` rows, including their
    vector embeddings and full-text search vectors) are deleted.
    """
    with observation_span(
        "rag.api.documents.delete",
        input_value={"document_id": str(document_id)},
    ) as span:
        # Verify the document exists before attempting deletion
        existing = get_document(document_id)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document '{document_id}' not found.",
            )

        deleted = delete_document(document_id)
        set_span_output(span, {"deleted": deleted})

    return DocumentDeleteResponse(
        document_id=document_id,
        deleted=deleted,
        message=(
            f"Document '{existing['filename']}' and all its chunks have been removed."
            if deleted
            else "Delete operation returned no rows – document may have already been removed."
        ),
    )
