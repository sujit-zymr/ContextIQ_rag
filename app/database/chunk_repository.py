
from app.database.connection import get_connection
from psycopg.types.json import Jsonb


def save_document(
    filename,
    file_hash,
    chunks,
    embeddings,
    chunk_metadata
):

    if not (
        len(chunks) == len(embeddings) == len(chunk_metadata)
    ):
        raise ValueError(
            "Chunks, embeddings, and metadata must have equal lengths"
        )

    with get_connection() as conn:

        # Save original document
        document = conn.execute(
            """
            INSERT INTO documents (filename, file_hash)
            VALUES (%s, %s)
            RETURNING id
            """,
            (filename, file_hash)
        ).fetchone()

        document_id = document[0]

        # Prepare chunk records
        records = [
            (
                document_id,
                index,
                chunk,
                embedding,
                Jsonb(metadata)
            )
            for index, (chunk, embedding, metadata)
            in enumerate(zip(chunks, embeddings, chunk_metadata))
        ]

        # Save chunks and their vectors
        with conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO document_chunks
                (document_id, chunk_index, content, embedding, metadata)
                VALUES (%s, %s, %s, %s, %s)
                """,
                records
            )

    return document_id


def document_exists(file_hash):
    with get_connection() as conn:
        result = conn.execute(
            """
            SELECT id
            FROM documents
            WHERE file_hash = %s
            LIMIT 1
            """,
            (file_hash,)
        ).fetchone()

    return result is not None
