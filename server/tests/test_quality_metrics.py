from app.evaluation.quality_metrics import (
    compute_retrieval_metrics,
    score_quality_row,
    summarize_metric_rows,
)


def test_quality_metrics_score_retrieval_citations_abstention_and_acl():
    row = {
        "relevant_pages": [2, 4],
        "retrieved_chunks": [
            {"document_id": "allowed", "filename": "policy.pdf", "page": 4, "chunk_index": 3},
            {"document_id": "allowed", "filename": "policy.pdf", "page": 2, "chunk_index": 1},
            {"document_id": "blocked", "filename": "private.pdf", "page": 1, "chunk_index": 0},
        ],
        "citations": [{"document_id": "allowed", "filename": "policy.pdf", "page": 4, "chunk_index": 3}],
        "abstained": False,
        "should_abstain": False,
        "forbidden_document_ids": ["blocked"],
        "response": "Here is the answer based on policy.pdf.",
    }

    scores = score_quality_row(row)

    assert scores["recall_at_5"] == 1.0
    assert scores["mrr"] == 1.0
    assert scores["ndcg_at_5"] > 0.9
    assert scores["precision_at_5"] == 2.0 / 3.0
    assert scores["hit_rate_at_5"] == 1.0
    assert scores["citation_presence"] == 1.0
    assert scores["citation_correctness"] == 1.0
    assert scores["citation_filename_validity"] == 1.0
    assert scores["citation_page_validity"] == 1.0
    assert scores["missing_citation_rate"] == 0.0
    assert scores["abstention_quality"] == 1.0
    assert scores["false_abstention_rate"] == 0.0
    assert scores["acl_leakage"] == 1.0


def test_quality_metrics_leave_unlabeled_values_missing():
    scores = score_quality_row({"retrieved_pages": [1], "citations": [], "retrieved_chunks": []})

    assert scores["recall_at_5"] is None
    assert scores["citation_correctness"] is None
    assert scores["abstention_quality"] is None
    assert scores["acl_leakage"] is None


def test_metric_summary_reports_missing_coverage():
    summary = summarize_metric_rows([{"recall_at_5": 1.0}, {"recall_at_5": None}], ["recall_at_5"])

    assert summary["recall_at_5"] == {"mean": 1.0, "scored_count": 1, "missing_count": 1}


def test_compute_retrieval_metrics_configurable_k():
    row = {
        "relevant_pages": [10, 20],
        "retrieved_chunks": [
            {"page": 5},
            {"page": 10},
            {"page": 15},
            {"page": 20},
        ],
    }
    # At k=1: page 5 is not relevant
    at_1 = compute_retrieval_metrics(row, k=1)
    assert at_1["precision_at_1"] == 0.0
    assert at_1["recall_at_1"] == 0.0
    assert at_1["hit_rate_at_1"] == 0.0

    # At k=2: page 5 and 10 -> 1 hit
    at_2 = compute_retrieval_metrics(row, k=2)
    assert at_2["precision_at_2"] == 0.5
    assert at_2["recall_at_2"] == 0.5
    assert at_2["hit_rate_at_2"] == 1.0
    assert at_2["mrr"] == 0.5


def test_retrieval_metrics_empty_and_no_relevant_chunks():
    # Question with no relevant chunks (unanswerable)
    row_unanswerable = {
        "relevant_pages": [],
        "retrieved_chunks": [],
    }
    scores = compute_retrieval_metrics(row_unanswerable, k=5)
    assert scores["precision_at_5"] == 1.0
    assert scores["recall_at_5"] == 1.0
    assert scores["hit_rate_at_5"] == 0.0

    # Question with relevant chunks, but retrieval returned empty
    row_empty_retrieval = {
        "relevant_pages": [3],
        "retrieved_chunks": [],
    }
    scores_empty = compute_retrieval_metrics(row_empty_retrieval, k=5)
    assert scores_empty["precision_at_5"] == 0.0
    assert scores_empty["recall_at_5"] == 0.0
    assert scores_empty["hit_rate_at_5"] == 0.0
    assert scores_empty["mrr"] == 0.0


def test_abstention_rates():
    # Correct abstention
    row_correct_abstain = {
        "should_abstain": True,
        "abstained": True,
        "citations": [],
        "retrieved_chunks": [],
    }
    scores = score_quality_row(row_correct_abstain)
    assert scores["abstention_quality"] == 1.0
    assert scores["correct_abstention_rate"] == 1.0
    assert scores["unsupported_answer_rate"] == 0.0

    # False abstention
    row_false_abstain = {
        "should_abstain": False,
        "abstained": True,
        "citations": [],
        "retrieved_chunks": [],
    }
    scores_false = score_quality_row(row_false_abstain)
    assert scores_false["abstention_quality"] == 0.0
    assert scores_false["false_abstention_rate"] == 1.0

    # Unsupported answer (answered when should have abstained)
    row_unsupported = {
        "should_abstain": True,
        "abstained": False,
        "citations": [],
        "retrieved_chunks": [],
    }
    scores_unsupp = score_quality_row(row_unsupported)
    assert scores_unsupp["abstention_quality"] == 0.0
    assert scores_unsupp["unsupported_answer_rate"] == 1.0
    assert scores_unsupp["missing_citation_rate"] == 1.0


def test_acl_leakage_citation_and_response():
    # Leakage via citation
    row_cit_leak = {
        "forbidden_document_ids": ["private-123"],
        "retrieved_chunks": [{"document_id": "public-1"}],
        "citations": [{"document_id": "private-123"}],
        "response": "General public summary",
    }
    assert score_quality_row(row_cit_leak)["acl_leakage"] == 1.0

    # Leakage via response content
    row_resp_leak = {
        "forbidden_document_ids": ["secret-doc-xyz"],
        "retrieved_chunks": [{"document_id": "public-1"}],
        "citations": [],
        "response": "Information obtained from secret-doc-xyz confirms that...",
    }
    assert score_quality_row(row_resp_leak)["acl_leakage"] == 1.0

    # Clean / no leakage
    row_clean = {
        "forbidden_document_ids": ["secret-doc-xyz"],
        "retrieved_chunks": [{"document_id": "public-1"}],
        "citations": [{"document_id": "public-1"}],
        "response": "General clean response.",
    }
    assert score_quality_row(row_clean)["acl_leakage"] == 0.0
