
from app.database.connection import get_connection
from app.ingestion.embedder import generate_query_embedding
from app.observability import observation_span, set_span_output


def search_similar_chunks(question, top_k=5):
    with observation_span(
        "rag.retrieval",
        input_value={"question": question, "top_k": top_k},
    ) as span:
        with observation_span(
            "rag.retrieval.query_embedding",
            input_value={"question": question, "model": "all-MiniLM-L6-v2"},
            as_type="embedding",
        ) as embedding_span:
            query_embedding = generate_query_embedding(question)
            set_span_output(embedding_span, {"dimensions": len(query_embedding)})

        with observation_span(
            "rag.retrieval.vector_search",
            input_value={"top_k": top_k, "distance_metric": "cosine"},
            as_type="retriever",
        ) as search_span:
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
                    JOIN documents d ON d.id = c.document_id
                    WHERE c.embedding IS NOT NULL
                    ORDER BY c.embedding <=> %s
                    LIMIT %s
                    """,
                    (query_embedding, query_embedding, top_k),
                ).fetchall()
            chunks = [
                {
                    "filename": row[0],
                    "content": row[1],
                    "chunk_index": row[2],
                    "metadata": row[3],
                    "page": row[3].get("page") + 1 if row[3].get("page") is not None else None,
                    "similarity": float(row[4]),
                }
                for row in results
            ]
            set_span_output(search_span, chunks)

        set_span_output(span, {"retrieved_count": len(chunks), "chunks": chunks})
        return chunks
