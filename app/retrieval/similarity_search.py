
from app.database.connection import get_connection
from app.ingestion.embedder import generate_query_embedding


def search_similar_chunks(question, top_k=5):

    # Step 1: Convert question into embedding
    query_embedding = generate_query_embedding(question)

    # Step 2: Search PostgreSQL
    with get_connection() as conn:

        results = conn.execute(
            """
            SELECT
                d.filename,
                c.content,
                c.chunk_index,
                c.metadata,
                1 - (c.embedding <=> %s) AS similarity

            FROM document_chunks c

            JOIN documents d
                ON d.id = c.document_id

            WHERE c.embedding IS NOT NULL

            ORDER BY c.embedding <=> %s

            LIMIT %s
            """,
            (
                query_embedding,
                query_embedding,
                top_k
            )
        ).fetchall()

    return [
        {
            "filename": row[0],
            "content": row[1],
            "chunk_index": row[2],
            "metadata": row[3],
            "page": (
                row[3].get("page") + 1
                if row[3].get("page") is not None
                else None
            ),
            "similarity": float(row[4])
        }
        for row in results
    ]
