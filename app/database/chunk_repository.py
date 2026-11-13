from uuid import UUID

from psycopg.types.json import Jsonb

from app.database.connection import get_connection


def start_document_ingestion(filename, file_hash, source_path, metadata=None, document_id=None):
    """Create or reset a document record and mark it as processing."""
    metadata = metadata or {}
    with get_connection() as conn:
        if document_id:
            row = conn.execute(
                "SELECT id FROM documents WHERE id = %s", (UUID(str(document_id)),)
            ).fetchone()
            if row is None:
                raise ValueError(f"Document not found: {document_id}")
            resolved_id = row[0]
            conn.execute(
                """UPDATE documents SET status='processing', status_message=NULL, updated_at=NOW()
                   WHERE id=%s""",
                (resolved_id,),
            )
        else:
            row = conn.execute(
                "SELECT id FROM documents WHERE file_hash=%s ORDER BY created_at LIMIT 1",
                (file_hash,),
            ).fetchone()
            if row:
                resolved_id = row[0]
                conn.execute(
                    """UPDATE documents SET status='processing', status_message=NULL, updated_at=NOW()
                       WHERE id=%s""",
                    (resolved_id,),
                )
            else:
                resolved_id = conn.execute(
                    """INSERT INTO documents
                       (filename, file_hash, source_path, metadata, status, status_message)
                       VALUES (%s, %s, %s, %s, 'queued', NULL) RETURNING id""",
                    (filename, file_hash, source_path, Jsonb(metadata)),
                ).fetchone()[0]
    # Commit the queued row before transitioning so status is observable even
    # though the CLI currently processes documents synchronously.
    with get_connection() as conn:
        conn.execute(
            "UPDATE documents SET status='processing', updated_at=NOW() WHERE id=%s",
            (resolved_id,),
        )
    return resolved_id


def complete_document_ingestion(
    document_id, chunks, embeddings, chunk_metadata, *,
    filename=None, file_hash=None, source_path=None, metadata=None,
):
    if not (len(chunks) == len(embeddings) == len(chunk_metadata)):
        raise ValueError("Chunks, embeddings, and metadata must have equal lengths")

    records = [
        (document_id, index, chunk, embedding, Jsonb(metadata))
        for index, (chunk, embedding, metadata) in enumerate(zip(chunks, embeddings, chunk_metadata))
    ]
    with get_connection() as conn:
        # Replace the indexed content and its metadata in one transaction. A
        # failed insertion rolls back the deletion and preserves the old index.
        conn.execute("DELETE FROM document_chunks WHERE document_id=%s", (document_id,))
        if records:
            with conn.cursor() as cursor:
                cursor.executemany(
                    """INSERT INTO document_chunks
                       (document_id, chunk_index, content, embedding, metadata)
                       VALUES (%s, %s, %s, %s, %s)""",
                    records,
                )
        conn.execute(
            """UPDATE documents SET
               filename=COALESCE(%s, filename),
               file_hash=COALESCE(%s, file_hash),
               source_path=COALESCE(%s, source_path),
               metadata=COALESCE(%s, metadata),
               status='completed', status_message=NULL,
               updated_at=NOW() WHERE id=%s""",
            (filename, file_hash, source_path, Jsonb(metadata) if metadata is not None else None, document_id),
        )


def fail_document_ingestion(document_id, message):
    with get_connection() as conn:
        conn.execute(
            """UPDATE documents SET status='failed', status_message=%s,
               updated_at=NOW() WHERE id=%s""",
            (str(message)[:1000], document_id),
        )


def get_document(document_id):
    with get_connection() as conn:
        row = conn.execute(
            """SELECT id, filename, file_hash, source_path, metadata, status
               FROM documents WHERE id=%s""",
            (UUID(str(document_id)),),
        ).fetchone()
    if row is None:
        return None
    return {
        "id": row[0], "filename": row[1], "file_hash": row[2], "source_path": row[3],
        "metadata": row[4] or {}, "status": row[5],
    }


def delete_document(document_id):
    with get_connection() as conn:
        result = conn.execute(
            "DELETE FROM documents WHERE id=%s RETURNING id", (UUID(str(document_id)),)
        ).fetchone()
    return result is not None


def save_document(filename, file_hash, chunks, embeddings, chunk_metadata):
    """Backward-compatible helper used by older callers."""
    document_id = start_document_ingestion(filename, file_hash, filename)
    complete_document_ingestion(document_id, chunks, embeddings, chunk_metadata)
    return document_id


def document_exists(file_hash):
    with get_connection() as conn:
        result = conn.execute(
            "SELECT id FROM documents WHERE file_hash = %s LIMIT 1", (file_hash,)
        ).fetchone()
    return result is not None
