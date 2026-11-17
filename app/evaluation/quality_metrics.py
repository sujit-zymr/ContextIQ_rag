"""Deterministic retrieval, citation, abstention, and ACL evaluation metrics."""

from math import log2
from typing import Any


QUALITY_METRIC_NAMES = (
    "precision_at_5",
    "recall_at_5",
    "hit_rate_at_5",
    "mrr",
    "ndcg_at_5",
    "citation_presence",
    "citation_correctness",
    "citation_filename_validity",
    "citation_page_validity",
    "missing_citation_rate",
    "abstention_quality",
    "correct_abstention_rate",
    "false_abstention_rate",
    "unsupported_answer_rate",
    "acl_leakage",
)


def _page_number(item: Any) -> int | None:
    value = item.get("page") if isinstance(item, dict) else item
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _source_key(source: dict) -> tuple[str, int | None, Any]:
    return (
        str(source.get("document_id") or source.get("filename") or ""),
        _page_number(source),
        source.get("chunk_index"),
    )


# ---------------------------------------------------------------------------
# 7.2 Retrieval Evaluation Metrics (Configurable K)
# ---------------------------------------------------------------------------

def compute_retrieval_metrics(row: dict, k: int = 5) -> dict[str, float | None]:
    """Compute Precision@K, Recall@K, Hit Rate@K, MRR, and NDCG@K.

    Handles:
    - Empty retrieval results (returns 0.0 or 1.0 depending on relevant ground truth)
    - Questions with no relevant chunks (e.g. unanswerable questions)
    - Unlabeled rows (missing relevant_pages returns None for all metrics)
    - Configurable K values
    """
    if "relevant_pages" not in row or row.get("relevant_pages") is None:
        return {
            f"precision_at_{k}": None,
            f"recall_at_{k}": None,
            f"hit_rate_at_{k}": None,
            "mrr": None,
            f"ndcg_at_{k}": None,
        }

    relevant = {_page_number(page) for page in row.get("relevant_pages", [])}
    relevant.discard(None)

    ranked_sources = row.get("retrieved_chunks")
    if isinstance(ranked_sources, list):
        ranked_pages = [_page_number(item) for item in ranked_sources]
    else:
        ranked_pages = [_page_number(item) for item in row.get("retrieved_pages", [])]
    ranked_pages = [page for page in ranked_pages if page is not None]

    top_pages = ranked_pages[:k]

    # Handle questions with no relevant chunks in the ground truth
    if not relevant:
        # If no relevant chunks exist in the corpus:
        # - Hit rate is 0.0 (no relevant item was found)
        # - Precision@K is 0.0 if items were retrieved (false alarms), 1.0 if empty
        # - Recall@K is 1.0 (zero relevant chunks existed, so none were missed)
        # - MRR and NDCG are 0.0
        return {
            f"precision_at_{k}": 1.0 if not top_pages else 0.0,
            f"recall_at_{k}": 1.0,
            f"hit_rate_at_{k}": 0.0,
            "mrr": 0.0,
            f"ndcg_at_{k}": 0.0,
        }

    hits = [page in relevant for page in top_pages]
    hit_count = len(set(top_pages) & relevant)

    precision = hit_count / len(top_pages) if top_pages else 0.0
    recall = hit_count / len(relevant)
    hit_rate = 1.0 if any(hits) else 0.0

    first_hit = next((rank for rank, hit in enumerate(hits, start=1) if hit), None)
    mrr = 1.0 / first_hit if first_hit else 0.0

    dcg = sum(1.0 / log2(rank + 1) for rank, hit in enumerate(hits, start=1) if hit)
    ideal_hits = min(len(relevant), k)
    idcg = sum(1.0 / log2(rank + 1) for rank in range(1, ideal_hits + 1))
    ndcg = dcg / idcg if idcg else 0.0

    return {
        f"precision_at_{k}": precision,
        f"recall_at_{k}": recall,
        f"hit_rate_at_{k}": hit_rate,
        "mrr": mrr,
        f"ndcg_at_{k}": ndcg,
    }


def _retrieval_metrics(row: dict) -> dict[str, float | None]:
    """Compatibility wrapper returning metrics with default k=5."""
    if "relevant_pages" not in row or row.get("relevant_pages") is None:
        return {
            "precision_at_5": None,
            "recall_at_5": None,
            "hit_rate_at_5": None,
            "mrr": None,
            "ndcg_at_5": None,
        }

    relevant = {_page_number(page) for page in row.get("relevant_pages", [])}
    relevant.discard(None)
    if not relevant:
        return {
            "precision_at_5": None,
            "recall_at_5": None,
            "hit_rate_at_5": None,
            "mrr": None,
            "ndcg_at_5": None,
        }

    return compute_retrieval_metrics(row, k=5)


# ---------------------------------------------------------------------------
# 7.3 Citation Evaluation Metrics
# ---------------------------------------------------------------------------

def _citation_presence(row: dict) -> float | None:
    """Evaluate whether citations are provided when required.

    Returns 1.0 if citations exist, or if the question was correctly abstained.
    Returns 0.0 if an answer was generated without citations.
    """
    citations = row.get("citations")
    if not isinstance(citations, list):
        return None
    if citations:
        return 1.0
    if row.get("abstained") and row.get("should_abstain") is True:
        return 1.0
    if row.get("should_abstain") is not None and not row.get("abstained"):
        return 0.0
    return None


def _citation_correctness(row: dict) -> float | None:
    """Check citation correctness against retrieved chunks and abstention requirements."""
    citations = row.get("citations")
    retrieved = row.get("retrieved_chunks")
    if not isinstance(citations, list) or not isinstance(retrieved, list):
        return None
    if not citations:
        expected_abstention = row.get("should_abstain")
        if expected_abstention is None:
            return None
        return 1.0 if row.get("abstained") and expected_abstention is True else 0.0

    retrieved_keys = {_source_key(item) for item in retrieved if isinstance(item, dict)}
    valid = sum(
        1 for citation in citations
        if isinstance(citation, dict) and _source_key(citation) in retrieved_keys
    )
    return valid / len(citations)


def _citation_filename_validity(row: dict) -> float | None:
    """Evaluate whether cited filenames match retrieved chunk filenames."""
    citations = row.get("citations")
    retrieved = row.get("retrieved_chunks")
    if not isinstance(citations, list) or not isinstance(retrieved, list):
        return None
    if not citations:
        return 1.0 if row.get("abstained") and row.get("should_abstain") is True else 0.0

    retrieved_filenames = {
        str(c.get("filename")) for c in retrieved if isinstance(c, dict) and c.get("filename")
    }
    valid = sum(
        1 for citation in citations
        if isinstance(citation, dict) and str(citation.get("filename")) in retrieved_filenames
    )
    return valid / len(citations)


def _citation_page_validity(row: dict) -> float | None:
    """Evaluate whether cited page numbers match retrieved chunk pages."""
    citations = row.get("citations")
    retrieved = row.get("retrieved_chunks")
    if not isinstance(citations, list) or not isinstance(retrieved, list):
        return None
    if not citations:
        return 1.0 if row.get("abstained") and row.get("should_abstain") is True else 0.0

    retrieved_pages = {_page_number(c) for c in retrieved if isinstance(c, dict)}
    retrieved_pages.discard(None)
    valid = sum(
        1 for citation in citations
        if isinstance(citation, dict) and _page_number(citation) in retrieved_pages
    )
    return valid / len(citations)


def _missing_citation_rate(row: dict) -> float | None:
    """Evaluate whether factual claims lack citations.

    Returns 1.0 if an answer was produced without any citations.
    Returns 0.0 if citations were provided, or if the system correctly abstained.
    """
    citations = row.get("citations")
    if not isinstance(citations, list):
        return None
    if row.get("abstained"):
        return 0.0
    return 1.0 if not citations else 0.0


# ---------------------------------------------------------------------------
# 7.5 Abstention Evaluation Metrics
# ---------------------------------------------------------------------------

def _abstention_quality(row: dict) -> float | None:
    """Overall abstention correctness: whether expected abstention equals actual."""
    expected = row.get("should_abstain")
    actual = row.get("abstained")
    if not isinstance(expected, bool) or not isinstance(actual, bool):
        return None
    return float(expected == actual)


def _correct_abstention_rate(row: dict) -> float | None:
    """1.0 if unanswerable question was correctly abstained, 0.0 if answered, None if answerable."""
    expected = row.get("should_abstain")
    actual = row.get("abstained")
    if expected is True and isinstance(actual, bool):
        return 1.0 if actual is True else 0.0
    return None


def _false_abstention_rate(row: dict) -> float | None:
    """1.0 if answerable question was incorrectly abstained, 0.0 if answered, None if unanswerable."""
    expected = row.get("should_abstain")
    actual = row.get("abstained")
    if expected is False and isinstance(actual, bool):
        return 1.0 if actual is True else 0.0
    return None


def _unsupported_answer_rate(row: dict) -> float | None:
    """1.0 if unanswerable question received an unsupported answer, 0.0 if abstained."""
    expected = row.get("should_abstain")
    actual = row.get("abstained")
    if expected is True and isinstance(actual, bool):
        return 1.0 if actual is False else 0.0
    return None


# ---------------------------------------------------------------------------
# 7.6 ACL Leakage Evaluation
# ---------------------------------------------------------------------------

def _acl_leakage(row: dict) -> float | None:
    """Evaluate unauthorized retrieval, citation, or content leakage."""
    forbidden = row.get("forbidden_document_ids")
    retrieved = row.get("retrieved_chunks")
    if not isinstance(forbidden, list) or not isinstance(retrieved, list):
        return None
    forbidden_ids = {str(value) for value in forbidden}

    # 1. Retrieval leakage
    retrieval_leaked = any(
        isinstance(chunk, dict) and str(chunk.get("document_id")) in forbidden_ids
        for chunk in retrieved
    )

    # 2. Citation leakage
    citations = row.get("citations", [])
    citation_leaked = any(
        isinstance(cit, dict) and str(cit.get("document_id")) in forbidden_ids
        for cit in citations
    ) if isinstance(citations, list) else False

    # 3. Response leakage (forbidden document identifier mentioned in response)
    response_text = str(row.get("response", ""))
    response_leaked = any(fid in response_text for fid in forbidden_ids)

    return float(retrieval_leaked or citation_leaked or response_leaked)


# ---------------------------------------------------------------------------
# Per-Row Scoring & Aggregation
# ---------------------------------------------------------------------------

def score_quality_row(row: dict) -> dict[str, float | None]:
    """Score all deterministic quality metrics for a single evaluation row."""
    scores = _retrieval_metrics(row)
    scores["citation_presence"] = _citation_presence(row)
    scores["citation_correctness"] = _citation_correctness(row)
    scores["citation_filename_validity"] = _citation_filename_validity(row)
    scores["citation_page_validity"] = _citation_page_validity(row)
    scores["missing_citation_rate"] = _missing_citation_rate(row)
    scores["abstention_quality"] = _abstention_quality(row)
    scores["correct_abstention_rate"] = _correct_abstention_rate(row)
    scores["false_abstention_rate"] = _false_abstention_rate(row)
    scores["unsupported_answer_rate"] = _unsupported_answer_rate(row)
    scores["acl_leakage"] = _acl_leakage(row)
    return scores


def summarize_metric_rows(rows: list[dict], metrics: tuple | list) -> dict[str, dict]:
    """Aggregate individual metric scores across all rows."""
    summary = {}
    for name in metrics:
        values = [row.get(name) for row in rows if row.get(name) is not None]
        summary[name] = {
            "mean": sum(values) / len(values) if values else None,
            "scored_count": len(values),
            "missing_count": len(rows) - len(values),
        }
    return summary
