"""Run Ragas metrics and associate each result with a Langfuse trace."""

import asyncio
import csv
import importlib.util
import json
import logging
import os
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

logger = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT_DIR / "evaluation_data" / "ragas_dataset.json"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "evaluation_data" / "ragas_results"
METRIC_NAMES = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)


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
    }

    for name in METRIC_NAMES:
        if row["reference"] is None and name in {"context_precision", "context_recall"}:
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
) -> dict:
    """Evaluate a prepared dataset, save results, and publish linked trace scores."""
    configure_observability()
    dataset_path = Path(dataset_path)
    output_dir = Path(output_dir)
    rows = _load_rows(dataset_path)
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
                set_span_output(sample_span, {"scores": scores, "metric_errors": errors})
            evaluated.append({
                "id": row["_sample_id"],
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

    fieldnames = ["id", "langfuse_trace_id", *METRIC_NAMES, "metric_errors"]
    with details_path.open("w", newline="", encoding="utf-8") as output_file:
        writer = csv.DictWriter(output_file, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow({
                "id": result["id"],
                "langfuse_trace_id": result["langfuse_trace_id"] or "",
                **result["scores"],
                "metric_errors": json.dumps(result["metric_errors"], ensure_ascii=False),
            })

    averages = {}
    for name in METRIC_NAMES:
        values = [item["scores"][name] for item in results if item["scores"][name] is not None]
        averages[name] = sum(values) / len(values) if values else None

    summary = {
        "run_id": run_id,
        "dataset": str(dataset_path),
        "sample_count": len(results),
        "trace_linked_count": sum(bool(item["langfuse_trace_id"]) for item in results),
        "metric_averages": averages,
        "details_file": str(details_path),
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Ragas CSV: {details_path}")
    print(f"Ragas summary: {summary_path}")
    print(f"Langfuse-linked evaluation samples: {summary['trace_linked_count']}/{summary['sample_count']}")
    return summary
