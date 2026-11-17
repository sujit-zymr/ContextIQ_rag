"""Run Ragas metrics and associate each result with a Langfuse trace."""

import asyncio
import csv
import hashlib
import importlib.util
import json
import logging
import os
import subprocess
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from app.observability import (
    configure_observability,
    observation_span,
    record_score,
    redact_sensitive_text,
    set_span_output,
    span_trace_id,
    valid_trace_id,
)
from app.evaluation.quality_metrics import QUALITY_METRIC_NAMES, score_quality_row, summarize_metric_rows

logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT_DIR / "evaluation_data" / "ragas_dataset.json"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "evaluation_data" / "ragas_results"
METRIC_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
    "answer_correctness",
)
ALL_METRIC_NAMES = (*METRIC_NAMES, *QUALITY_METRIC_NAMES)


def _create_pipeline_embeddings():
    """Create Ragas's modern embedding interface around the app's model."""
    from ragas.embeddings.base import BaseRagasEmbedding

    class PipelineRagasEmbeddings(BaseRagasEmbedding):
        """Reuse the project's local sentence-transformer model for Ragas."""

        def embed_text(self, text: str, **kwargs) -> list[float]:
            from app.ingestion.embedder import generate_query_embedding

            return generate_query_embedding(text).tolist()

        async def aembed_text(self, text: str, **kwargs) -> list[float]:
            return await asyncio.to_thread(self.embed_text, text)

        def embed_texts(self, texts: list[str], **kwargs) -> list[list[float]]:
            from app.ingestion.embedder import generate_embeddings

            return generate_embeddings(texts).tolist()

        async def aembed_texts(self, texts: list[str], **kwargs) -> list[list[float]]:
            return await asyncio.to_thread(self.embed_texts, texts)

    return PipelineRagasEmbeddings()


def _load_rows(dataset_path: Path) -> list[dict]:
    try:
        data = json.loads(dataset_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read Ragas dataset at {dataset_path}: {exc}") from exc

    if isinstance(data, dict):
        data = data.get("data", data.get("samples"))
    if not isinstance(data, list) or not data:
        raise ValueError("The Ragas dataset must be a non-empty JSON array of records.")

    rows = []
    for index, row in enumerate(data, start=1):
        if not isinstance(row, dict):
            raise ValueError(f"Dataset record {index} must be a JSON object.")
        question = row.get("user_input", row.get("question"))
        contexts = row.get("retrieved_contexts", row.get("contexts"))
        response = row.get("response", row.get("answer"))
        reference = row.get("reference", row.get("expected_answer"))
        if not isinstance(question, str) or not question.strip() or not isinstance(response, str):
            raise ValueError(f"Dataset record {index} needs string user_input and response fields.")
        if not isinstance(contexts, list) or not all(isinstance(item, str) for item in contexts):
            raise ValueError(f"Dataset record {index} needs a retrieved_contexts list of strings.")

        rows.append({
            **row,
            "user_input": question,
            "retrieved_contexts": contexts,
            "response": response,
            "reference": reference if isinstance(reference, str) else None,
            "_sample_id": str(row.get("id", index)),
        })
    return rows


def _create_metrics():
    """Build current Ragas collections metrics using the configured NVIDIA judge."""
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise RuntimeError("NVIDIA_API_KEY is required to run Ragas LLM metrics.")

    try:
        _ensure_ragas_vertexai_compatibility()
        from openai import AsyncOpenAI
        from ragas.llms import llm_factory
        from ragas.metrics.collections import (
            AnswerCorrectness,
            AnswerRelevancy,
            ContextPrecision,
            ContextRecall,
            Faithfulness,
        )
    except ImportError as exc:
        if importlib.util.find_spec("ragas") is None:
            raise RuntimeError(
                "Ragas is not installed. Activate the project venv and run: "
                "python -m pip install -r requirements.txt"
            ) from exc
        raise RuntimeError(
            f"Ragas is installed but its metric modules could not be imported: {exc}"
        ) from exc

    model_name = (
        os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
        or "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    ).strip()
    judge_client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://integrate.api.nvidia.com/v1",
        timeout=90,
        max_retries=2,
    )
    evaluator_llm = llm_factory(
        model=model_name,
        client=judge_client,
        temperature=0,
        max_tokens=4096,
    )
    evaluator_embeddings = _create_pipeline_embeddings()

    return {
        "faithfulness": Faithfulness(llm=evaluator_llm),
        "answer_relevancy": AnswerRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
        "context_precision": ContextPrecision(llm=evaluator_llm),
        "context_recall": ContextRecall(llm=evaluator_llm),
        "answer_correctness": AnswerCorrectness(
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        ),
    }


def _ensure_ragas_vertexai_compatibility() -> None:
    """Work around Ragas 0.4.3's eager import of a removed optional module.

    This RAG app uses NVIDIA through LangChain, not Vertex AI. Ragas imports
    ChatVertexAI unconditionally while loading any metric, even when Vertex AI
    is unused. Provide an inert type for that optional provider when its old
    import path is absent. Remove this shim once the installed Ragas release
    makes the provider import optional.
    """
    module_name = "langchain_community.chat_models.vertexai"
    try:
        __import__(module_name)
        return
    except ModuleNotFoundError as exc:
        if exc.name != module_name:
            raise

    compatibility_module = types.ModuleType(module_name)

    class _UnusedChatVertexAI:
        """Marker type for Ragas provider detection; never used by this app."""

    compatibility_module.ChatVertexAI = _UnusedChatVertexAI
    sys.modules[module_name] = compatibility_module


async def _score_row(row: dict, metrics: dict, trace_id: str | None) -> tuple[dict, dict]:
    scores = {}
    errors = {}
    metric_inputs = {
        "faithfulness": {
            "user_input": row["user_input"],
            "response": row["response"],
            "retrieved_contexts": row["retrieved_contexts"],
        },
        "answer_relevancy": {
            "user_input": row["user_input"],
            "response": row["response"],
        },
        "context_precision": {
            "user_input": row["user_input"],
            "reference": row["reference"],
            "retrieved_contexts": row["retrieved_contexts"],
        },
        "context_recall": {
            "user_input": row["user_input"],
            "reference": row["reference"],
            "retrieved_contexts": row["retrieved_contexts"],
        },
        "answer_correctness": {
            "user_input": row["user_input"],
            "response": row["response"],
            "reference": row["reference"],
        },
    }

    for name in METRIC_NAMES:
        if row["reference"] is None and name in {"context_precision", "context_recall", "answer_correctness"}:
            scores[name] = None
            errors[name] = "A reference answer is required for this metric."
            continue

        with observation_span(
            f"ragas.metric.{name}",
            input_value={"sample_id": row["_sample_id"], "metric": name},
            as_type="evaluator",
        ) as metric_span:
            try:
                result = await metrics[name].ascore(**metric_inputs[name])
                value = float(getattr(result, "value", result))
                scores[name] = value
                set_span_output(metric_span, {"score": value})
                record_score(
                    name=f"ragas_{name}",
                    value=value,
                    trace_id=trace_id,
                    comment=f"Ragas metric: {name}",
                )
            except Exception as exc:
                scores[name] = None
                # Keep exception details out of traces; local output includes a
                # sanitized message to help identify the failed metric.
                errors[name] = redact_sensitive_text(str(exc))
                logger.warning("Ragas metric %s failed for sample %s: %s", name, row["_sample_id"], errors[name])
                set_span_output(metric_span, {"error": errors[name]})
    return scores, errors


def run_ragas_evaluation(
    dataset_path: str | Path = DEFAULT_DATASET,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    save_baseline: bool = False,
    enforce_quality_gate: bool = False,
) -> dict:
    """Evaluate a prepared dataset, save results, and publish linked trace scores."""
    configure_observability()
    dataset_path = Path(dataset_path)
    output_dir = Path(output_dir)
    rows = _load_rows(dataset_path)
    dataset_sha256 = hashlib.sha256(dataset_path.read_bytes()).hexdigest()
    baseline_path = output_dir / "baseline.json"
    if save_baseline and baseline_path.exists():
        raise FileExistsError(
            f"Evaluation baseline already exists at {baseline_path}; preserve it and use a new output directory."
        )
    metrics = _create_metrics()

    async def evaluate_all() -> list[dict]:
        evaluated = []
        for row in rows:
            existing_trace_id = valid_trace_id(row.get("langfuse_trace_id") or row.get("trace_id"))
            trace_input = {
                "sample_id": row["_sample_id"],
                "user_input": row["user_input"],
                "retrieved_contexts": row["retrieved_contexts"],
                "response": row["response"],
                "reference": row["reference"],
            }
            with observation_span(
                "ragas.evaluation_sample",
                input_value=trace_input,
                trace_id=existing_trace_id,
            ) as sample_span:
                trace_id = existing_trace_id or span_trace_id(sample_span)
                scores, errors = await _score_row(row, metrics, trace_id)
                quality_scores = score_quality_row(row)
                scores.update(quality_scores)
                for name, value in quality_scores.items():
                    if value is not None:
                        record_score(
                            name=f"quality_{name}",
                            value=float(value),
                            trace_id=trace_id,
                            comment=f"Deterministic evaluation metric: {name}",
                        )
                set_span_output(sample_span, {"scores": scores, "metric_errors": errors})
            evaluated.append({
                "id": row["_sample_id"],
                "category": row.get("category", row.get("topic", "uncategorized")),
                "langfuse_trace_id": trace_id,
                "scores": scores,
                "metric_errors": errors,
            })
            print(f"Evaluated sample {row['_sample_id']}: {scores}")
        return evaluated

    results = asyncio.run(evaluate_all())
    output_dir.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    details_path = output_dir / f"ragas_scores_{run_id}.csv"
    summary_path = output_dir / f"ragas_summary_{run_id}.json"

    fieldnames = ["id", "category", "langfuse_trace_id", *ALL_METRIC_NAMES, "metric_errors"]
    with details_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow({
                "id": result["id"],
                "category": result["category"],
                "langfuse_trace_id": result["langfuse_trace_id"] or "",
                **result["scores"],
                "metric_errors": json.dumps(result["metric_errors"], ensure_ascii=False),
            })

    all_scores = [item["scores"] for item in results]
    metric_summary = summarize_metric_rows(all_scores, ALL_METRIC_NAMES)
    averages = {name: detail["mean"] for name, detail in metric_summary.items()}
    categories = {}
    for item in results:
        categories.setdefault(item["category"], []).append(item["scores"])
    category_summary = {
        category: {
            "sample_count": len(category_rows),
            "metric_averages": {
                name: summarize_metric_rows(category_rows, ALL_METRIC_NAMES)[name]["mean"]
                for name in ALL_METRIC_NAMES
            },
        }
        for category, category_rows in sorted(categories.items())
    }

    quality_gate = _build_quality_gate(len(results), category_summary, metric_summary)
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT_DIR, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        git_commit = None

    failed_questions = [
        item["id"] for item in results
        if any(item.get("metric_errors", {}).values())
        or (item["scores"].get("citation_correctness") == 0.0)
        or (item["scores"].get("acl_leakage") == 1.0)
    ]

    summary = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_type": "baseline" if save_baseline else "evaluation",
        "dataset": str(dataset_path),
        "dataset_sha256": dataset_sha256,
        "git_commit": git_commit,
        "model_information": (
            os.getenv("NVIDIA_MODEL", "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning")
        ),
        "embedding_model": "all-MiniLM-L6-v2",
        "chunking_configuration": {
            "chunk_size": int(os.getenv("RAG_CHUNK_SIZE", "200")),
            "chunk_overlap": int(os.getenv("RAG_CHUNK_OVERLAP", "40")),
        },
        "retrieval_configuration": {
            "default_top_k": 5,
            "search_mode": "hybrid",
            "reranker_model": os.getenv("RAG_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
        },
        "sample_count": len(results),
        "category_count": len(category_summary),
        "categories": category_summary,
        "trace_linked_count": sum(bool(item["langfuse_trace_id"]) for item in results),
        "metric_averages": averages,
        "metric_coverage": metric_summary,
        "failed_questions": failed_questions,
        "quality_gate": quality_gate,
        "details_file": str(details_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    # Generate human-readable summary text report
    readable_lines = [
        f"ContextIQ RAG Evaluation Report — Run {run_id}",
        "=" * 60,
        f"Timestamp:        {summary['timestamp']}",
        f"Dataset:          {summary['dataset']} (SHA-256: {dataset_sha256[:12]}...)",
        f"Samples Scored:   {summary['sample_count']} across {summary['category_count']} categories",
        f"Model:            {summary['model_information']}",
        f"Embedding Model:  {summary['embedding_model']}",
        f"Gate Status:      {'PASS' if quality_gate['passed'] else 'FAIL'}",
        "",
        "Aggregate Metric Scores:",
        "-" * 60,
    ]
    for metric_name in ALL_METRIC_NAMES:
        mean_val = averages.get(metric_name)
        val_str = f"{mean_val:.4f}" if mean_val is not None else "N/A (unscored)"
        cov = metric_summary.get(metric_name, {})
        readable_lines.append(f"  {metric_name:<28}: {val_str:<12} (coverage: {cov.get('scored_count', 0)}/{summary['sample_count']})")

    readable_lines.extend([
        "",
        "Quality Gate Checks:",
        "-" * 60,
    ])
    for check_name, check_passed in quality_gate["checks"].items():
        status_sym = "✓ PASS" if check_passed else "✗ FAIL"
        readable_lines.append(f"  [{status_sym}] {check_name}")

    if failed_questions:
        readable_lines.extend([
            "",
            f"Failed / Flagged Question IDs ({len(failed_questions)}):",
            f"  {', '.join(failed_questions[:20])}" + ("..." if len(failed_questions) > 20 else ""),
        ])

    human_summary_path = output_dir / f"ragas_summary_{run_id}.txt"
    human_summary_path.write_text("\n".join(readable_lines) + "\n", encoding="utf-8")

    if save_baseline:
        baseline_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Ragas CSV: {details_path}")
    print(f"Ragas summary JSON: {summary_path}")
    print(f"Ragas summary TXT:  {human_summary_path}")
    print(f"Langfuse-linked evaluation samples: {summary['trace_linked_count']}/{summary['sample_count']}")
    print(f"Quality gate: {'PASS' if quality_gate['passed'] else 'NOT PASSED'}")
    if enforce_quality_gate and not quality_gate["passed"]:
        raise RuntimeError(f"Evaluation quality gates did not pass; see {summary_path}")
    return summary


def _build_quality_gate(sample_count, categories, metric_summary):
    checks = {
        "at_least_100_questions": sample_count >= 100,
        "multiple_categories": len(categories) >= 3,
    }
    required_metrics = (
        *METRIC_NAMES,
        "recall_at_5",
        "precision_at_5",
        "hit_rate_at_5",
        "mrr",
        "ndcg_at_5",
        "citation_correctness",
        "abstention_quality",
    )
    checks["all_metrics_have_coverage"] = all(
        metric_summary[name]["scored_count"] > 0 for name in required_metrics
    )
    checks["citation_correctness_acceptable"] = (
        metric_summary["citation_correctness"]["mean"] is not None
        and metric_summary["citation_correctness"]["mean"] >= float(os.getenv("RAG_EVAL_MIN_CITATION_CORRECTNESS", "0.90"))
    )
    acl_mean = metric_summary["acl_leakage"]["mean"]
    checks["no_observed_acl_leakage"] = acl_mean == 0.0 if acl_mean is not None else True
    checks["acl_evaluation_cases_exist"] = metric_summary["acl_leakage"]["scored_count"] > 0

    configured_thresholds = {
        "recall_at_5": ("RAG_EVAL_MIN_RECALL_AT_5", 0.75),
        "precision_at_5": ("RAG_EVAL_MIN_PRECISION_AT_5", 0.50),
        "hit_rate_at_5": ("RAG_EVAL_MIN_HIT_RATE_AT_5", 0.80),
        "mrr": ("RAG_EVAL_MIN_MRR", 0.50),
        "ndcg_at_5": ("RAG_EVAL_MIN_NDCG_AT_5", 0.60),
        "faithfulness": ("RAG_EVAL_MIN_FAITHFULNESS", 0.75),
        "answer_correctness": ("RAG_EVAL_MIN_ANSWER_CORRECTNESS", 0.75),
        "abstention_quality": ("RAG_EVAL_MIN_ABSTENTION_QUALITY", 0.90),
    }
    thresholds = {}
    for metric, (env_name, default_value) in configured_thresholds.items():
        threshold = float(os.getenv(env_name, str(default_value)))
        thresholds[metric] = {"minimum": threshold, "environment_variable": env_name}
        value = metric_summary[metric]["mean"]
        checks[f"{metric}_meets_threshold"] = value is not None and value >= threshold
    max_acl = float(os.getenv("RAG_EVAL_MAX_ACL_LEAKAGE", "0.0"))
    thresholds["acl_leakage"] = {
        "maximum": max_acl,
        "environment_variable": "RAG_EVAL_MAX_ACL_LEAKAGE",
    }
    checks["acl_leakage_within_threshold"] = acl_mean is not None and acl_mean <= max_acl

    return {
        "passed": all(checks.values()),
        "checks": checks,
        "thresholds": thresholds,
    }
