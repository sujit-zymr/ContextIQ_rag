
from app.database.connection import get_connection
from app.ingestion.embedder import generate_query_embedding
from app.observability import observation_span, set_span_output
from app.retrieval.query_preprocessor import normalize_query
from app.retrieval.reranker import rerank_chunks
from app.retrieval.versioning import annotate_source_versions

RRF_K = 60


def search_similar_chunks(question, top_k=5):
    normalized_question = normalize_query(question)
    with observation_span(
        "rag.retrieval",
        input_value={"question": question, "normalized_question": normalized_question, "top_k": top_k},
    ) as span:
        with observation_span(
            "rag.retrieval.query_embedding",
            input_value={"question": normalized_question, "model": "all-MiniLM-L6-v2"},
            as_type="embedding",
        ) as embedding_span:
            query_embedding = generate_query_embedding(normalized_question)
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
                        d.id,
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
            chunks = annotate_source_versions([
                {
                    "document_id": str(row[0]),
                    "filename": row[1],
                    "content": row[2],
                    "chunk_index": row[3],
                    "metadata": row[4] or {},
                    "page": (row[4] or {}).get("page") + 1 if (row[4] or {}).get("page") is not None else None,
                    "similarity": float(row[5]),
                    "retrieval_method": "vector",
                    "score_type": "cosine_similarity",
                }
                for row in results
            ])
            set_span_output(search_span, chunks)

        set_span_output(span, {"retrieved_count": len(chunks), "chunks": chunks})
        return chunks


def search_full_text_chunks(question, top_k=5):
    """Retrieve chunks using PostgreSQL's English full-text search ranking."""
    if top_k <= 0:
        raise ValueError("top_k must be positive")

    normalized_question = normalize_query(question)
    with observation_span(
        "rag.retrieval.full_text_search",
        input_value={"question": question, "normalized_question": normalized_question, "top_k": top_k, "configuration": "english"},
        as_type="retriever",
    ) as span:
        with get_connection() as conn:
            results = conn.execute(
                """
                WITH query AS (
                    SELECT websearch_to_tsquery('english', %s) AS terms
                )
                SELECT
                    d.id,
                    d.filename,
                    c.content,
                    c.chunk_index,
                    c.metadata,
                    ts_rank_cd(c.search_vector, query.terms) AS score
                FROM document_chunks c
                JOIN documents d ON d.id = c.document_id
                CROSS JOIN query
                WHERE c.search_vector @@ query.terms
                ORDER BY score DESC, c.document_id, c.chunk_index
                LIMIT %s
                """,
                (normalized_question, top_k),
            ).fetchall()

        chunks = annotate_source_versions([
            {
                "document_id": str(row[0]),
                "filename": row[1],
                "content": row[2],
                "chunk_index": row[3],
                "metadata": row[4] or {},
                "page": (row[4] or {}).get("page") + 1 if (row[4] or {}).get("page") is not None else None,
                "score": float(row[5]),
                "retrieval_method": "full_text",
                "score_type": "full_text_rank",
            }
            for row in results
        ])
        set_span_output(span, {"retrieved_count": len(chunks), "chunks": chunks})
        return chunks


def _fuse_ranked_results(vector_results, full_text_results, top_k, rrf_k=RRF_K):
    """Combine ranked lists with Reciprocal Rank Fusion (RRF)."""
    combined = {}

    def key_for(chunk):
        document_id = chunk.get("document_id") or chunk.get("filename")
        return str(document_id), chunk.get("chunk_index"), chunk.get("content")

    for method, results in (("vector", vector_results), ("full_text", full_text_results)):
        for rank, chunk in enumerate(results, start=1):
            key = key_for(chunk)
            fused = combined.setdefault(
                key,
                {
                    **chunk,
                    "score": 0.0,
                    "retrieval_methods": [],
                    "vector_similarity": None,
                    "full_text_score": None,
                },
            )
            fused["score"] += 1.0 / (rrf_k + rank)
            if method not in fused["retrieval_methods"]:
                fused["retrieval_methods"].append(method)
            if method == "vector":
                fused["vector_similarity"] = chunk.get("similarity")
                fused["similarity"] = chunk.get("similarity")
            else:
                fused["full_text_score"] = chunk.get("score")

    ranked = sorted(
        combined.values(),
        key=lambda item: (
            -item["score"],
            -(item["vector_similarity"] or 0.0),
            -(item["full_text_score"] or 0.0),
        ),
    )
    for item in ranked:
        item["retrieval_method"] = "hybrid"
    return ranked[:top_k]


def search_chunks(question, top_k=5, mode="hybrid"):
    """Search with vector, full-text, or RRF-fused hybrid retrieval."""
    if top_k <= 0:
        raise ValueError("top_k must be positive")
    normalized_question = normalize_query(question)
    if mode == "vector":
        return search_similar_chunks(normalized_question, top_k)
    if mode == "full-text":
        return search_full_text_chunks(normalized_question, top_k)
    if mode == "hybrid":
        candidate_k = max(top_k * 5, 50)
        with observation_span(
            "rag.retrieval.hybrid_fusion",
            input_value={
                "question": question,
                "normalized_question": normalized_question,
                "top_k": top_k,
                "candidate_k": candidate_k,
                "algorithm": "rrf",
                "rrf_k": RRF_K,
            },
            as_type="retriever",
        ) as span:
            vector_results = search_similar_chunks(normalized_question, candidate_k)
            full_text_results = search_full_text_chunks(normalized_question, candidate_k)
            fused_candidates = _fuse_ranked_results(vector_results, full_text_results, candidate_k)
            reranked = rerank_chunks(normalized_question, fused_candidates)
            results = annotate_source_versions(reranked[:top_k])
            set_span_output(span, {
                "retrieved_count": len(results),
                "candidate_count": len(fused_candidates),
                "reranked": bool(results) and all(item.get("reranked") for item in results),
                "chunks": results,
            })
            return results
    raise ValueError("mode must be 'vector', 'full-text', or 'hybrid'")
