"""Cross-encoder reranking for hybrid retrieval candidates."""

import logging
import os
from functools import lru_cache

from app.observability import observation_span, redact_sensitive_text, set_span_output

logger = logging.getLogger(__name__)
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


@lru_cache(maxsize=2)
def _load_cross_encoder(model_name):
    import torch
    from sentence_transformers import CrossEncoder

    device = os.getenv("RAG_DEVICE", os.getenv("RAG_RERANKER_DEVICE"))
    if not device:
        if torch.cuda.is_available():
            try:
                cc = torch.cuda.get_device_capability(0)
                # Compute capability 7.0+ is required by modern PyTorch CUDA wheels
                device = "cuda" if (cc[0] > 7 or (cc[0] == 7 and cc[1] >= 0)) else "cpu"
            except Exception:
                device = "cpu"
        else:
            device = "cpu"

    return CrossEncoder(model_name, max_length=512, device=device)


def rerank_chunks(question, chunks):
    """Rerank candidates by cross-encoder relevance, failing open to input order."""
    if not chunks:
        return []

    model_name = os.getenv("RAG_RERANKER_MODEL", DEFAULT_RERANKER_MODEL).strip()
    try:
        with observation_span(
            "rag.retrieval.reranking",
            input_value={"candidate_count": len(chunks), "model": model_name},
            as_type="span",
        ) as span:
            model = _load_cross_encoder(model_name)
            pairs = [(question, chunk["content"]) for chunk in chunks]
            scores = model.predict(pairs, show_progress_bar=False, convert_to_numpy=True)
            scores = list(scores)
            if len(scores) != len(chunks):
                raise ValueError("Reranker returned a different number of scores than candidates")

            ranked = []
            for chunk, raw_score in zip(chunks, scores):
                score = float(raw_score)
                ranked.append({
                    **chunk,
                    "rrf_score": chunk.get("score"),
                    "score": score,
                    "rerank_score": score,
                    "score_type": "cross_encoder",
                    "retrieval_method": "hybrid",
                    "reranker_model": model_name,
                    "reranked": True,
                })
            ranked.sort(key=lambda item: item["rerank_score"], reverse=True)
            set_span_output(span, {
                "reranked": True,
                "candidate_count": len(ranked),
                "top_scores": [item["rerank_score"] for item in ranked[:5]],
            })
            return ranked
    except Exception as exc:
        safe_error = redact_sensitive_text(str(exc))
        logger.warning("Cross-encoder reranking failed; retaining RRF order: %s", safe_error)
        fallback = [
            {
                **chunk,
                "rrf_score": chunk.get("score"),
                "score_type": "rrf",
                "retrieval_method": "hybrid",
                "reranker_model": model_name,
                "reranked": False,
            }
            for chunk in chunks
        ]
        return fallback
