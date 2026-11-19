"""Document-level database queries for the Document Management API.

These functions are intentionally separate from chunk_repository.py so that
the API layer can query document-level metadata without having to know about
chunk internals.
"""

from uuid import UUID

from app.database.connection import get_connection


def list_documents(
    *,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """Return a paginated list of documents ordered by most-recently updated.

    Args:
        status: Optional filter – only return documents whose status matches
                (e.g. ``'completed'``, ``'processing'``, ``'failed'``).
        limit:  Maximum number of rows to return (1–200).
        offset: Row offset for pagination.

    Returns:
        A list of dicts with document summary information.
    """
    with get_connection() as conn:
        if status:
            rows = conn.execute(
                """
                SELECT
                    d.id,
                    d.filename,
                    d.status,
                    d.status_message,
                    d.metadata,
                    d.created_at,
                    d.updated_at,
                    COUNT(dc.id) AS chunk_count
                FROM documents d
                LEFT JOIN document_chunks dc ON dc.document_id = d.id
                WHERE d.status = %s
                GROUP BY d.id
                ORDER BY d.updated_at DESC
                LIMIT %s OFFSET %s
                """,
                (status, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT
                    d.id,
                    d.filename,
                    d.status,
                    d.status_message,
                    d.metadata,
                    d.created_at,
                    d.updated_at,
                    COUNT(dc.id) AS chunk_count
                FROM documents d
                LEFT JOIN document_chunks dc ON dc.document_id = d.id
                GROUP BY d.id
                ORDER BY d.updated_at DESC
                LIMIT %s OFFSET %s
                """,
                (limit, offset),
            ).fetchall()

    return [_row_to_summary(row) for row in rows]


def count_documents(*, status: str | None = None) -> int:
    """Return the total number of documents (optionally filtered by status)."""
    with get_connection() as conn:
        if status:
            result = conn.execute(
                "SELECT COUNT(*) FROM documents WHERE status = %s", (status,)
            ).fetchone()
        else:
            result = conn.execute("SELECT COUNT(*) FROM documents").fetchone()
    return int(result[0]) if result else 0


def get_document_detail(document_id) -> dict | None:
    """Return full detail for a single document, including chunk-level stats."""
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT
                d.id,
                d.filename,
                d.file_hash,
                d.source_path,
                d.status,
                d.status_message,
                d.metadata,
                d.created_at,
                d.updated_at,
                COUNT(dc.id)             AS chunk_count,
                SUM(LENGTH(dc.content))  AS total_chars
            FROM documents d
            LEFT JOIN document_chunks dc ON dc.document_id = d.id
            WHERE d.id = %s
            GROUP BY d.id
            """,
            (UUID(str(document_id)),),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "filename": row[1],
        "file_hash": row[2],
        "source_path": row[3],
        "status": row[4],
        "status_message": row[5],
        "metadata": row[6] or {},
        "created_at": row[7],
        "updated_at": row[8],
        "chunk_count": int(row[9]) if row[9] else 0,
        "total_chars": int(row[10]) if row[10] else 0,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _row_to_summary(row) -> dict:
    return {
        "id": row[0],
        "filename": row[1],
        "status": row[2],
        "status_message": row[3],
        "metadata": row[4] or {},
        "created_at": row[5],
        "updated_at": row[6],
        "chunk_count": int(row[7]) if row[7] else 0,
    }
