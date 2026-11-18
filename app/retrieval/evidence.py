"""Configurable relevance gates for retrieved evidence."""

import os


INSUFFICIENT_EVIDENCE_RESPONSE = (
    "I don't have enough evidence in the retrieved documents to answer that question."
)

DEFAULT_THRESHOLDS = {
    "vector": ("RAG_MIN_VECTOR_SIMILARITY", 0.35, "similarity"),
    "full-text": ("RAG_MIN_FULL_TEXT_SCORE", 0.02, "score"),
    "hybrid-reranked": ("RAG_MIN_RERANK_SCORE", -6.0, "rerank_score"),
    "hybrid-rrf": ("RAG_MIN_RRF_SCORE", 0.032, "score"),
}


def _infer_mode(chunks, requested_mode=None):
    if requested_mode:
        return requested_mode
    if any(chunk.get("retrieval_method") == "hybrid" for chunk in chunks):
        return "hybrid"
    if any(chunk.get("retrieval_method") == "full_text" for chunk in chunks):
        return "full-text"
    if any("similarity" in chunk for chunk in chunks):
        return "vector"
    return "unknown"


def assess_evidence(chunks, search_mode=None):
    """Return whether the strongest retrieved result clears its mode threshold."""
    mode = _infer_mode(chunks, search_mode)
    reranked = mode == "hybrid" and any(chunk.get("reranked") for chunk in chunks)
    threshold_key = "hybrid-reranked" if reranked else "hybrid-rrf" if mode == "hybrid" else mode

    if threshold_key not in DEFAULT_THRESHOLDS:
        return {
            "sufficient": False,
            "mode": mode,
            "threshold": None,
            "best_score": None,
            "reason": "No supported retrieval score is available.",
        }

    env_name, default_threshold, score_key = DEFAULT_THRESHOLDS[threshold_key]
    try:
        threshold = float(os.getenv(env_name, str(default_threshold)))
    except ValueError as exc:
        raise ValueError(f"{env_name} must be a number") from exc

    scores = []
    for chunk in chunks:
        value = chunk.get(score_key)
        if value is not None:
            try:
                scores.append(float(value))
            except (TypeError, ValueError):
                continue
    best_score = max(scores) if scores else None
    sufficient = bool(chunks) and best_score is not None and best_score >= threshold

    return {
        "sufficient": sufficient,
        "mode": mode,
        "threshold": threshold,
        "threshold_env": env_name,
        "best_score": best_score,
        "reason": "Evidence score meets threshold." if sufficient else "Evidence score is below threshold.",
    }
