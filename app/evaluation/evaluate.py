"""Run Ragas metrics against this project's RAG evaluation questions."""

import csv
import importlib
import importlib.metadata
import importlib.util
import json
import math
import os
import sys
import types
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_openai import ChatOpenAI

from app.evaluation.collect_data import collect_evaluation_data
from app.ingestion.embedder import get_model


ROOT_DIR = Path(__file__).resolve().parents[2]
RESULTS_DIR = ROOT_DIR / "evaluation_data" / "ragas_results"


class PipelineEmbeddings(Embeddings):
    """Expose the RAG pipeline's existing sentence-transformer to Ragas."""

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        vectors = get_model().encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        vector = get_model().encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return vector.tolist()


def _make_evaluator():
    load_dotenv()
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise ValueError("NVIDIA_API_KEY is not set. Add it to .env to run Ragas evaluation.")

    model_name = (
        os.getenv("RAGAS_MODEL")
        or os.getenv("NVIDIA_MODEL")
        or "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    ).strip()
    chat_model = ChatOpenAI(
        model=model_name,
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key,
        temperature=0,
        max_tokens=4096,
    )

    # These wrappers let Ragas reuse the project's NVIDIA compatible chat
    # endpoint and its local sentence-transformer embeddings. No OpenAI key or
    # second embedding service is needed.
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper

    from ragas.run_config import RunConfig

    run_config = RunConfig(
        timeout=int(os.getenv("RAGAS_TIMEOUT_SECONDS", "300")),
        max_retries=3,
        max_wait=10,
        max_workers=int(os.getenv("RAGAS_MAX_WORKERS", "4")),
    )
    return (
        LangchainLLMWrapper(chat_model, run_config=run_config),
        LangchainEmbeddingsWrapper(PipelineEmbeddings()),
        run_config,
    )


def _install_ragas_optional_vertexai_compatibility() -> None:
    """Work around Ragas 0.3.9 importing an optional, moved Vertex AI class.

    This application evaluates with NVIDIA/OpenAI-compatible models. Ragas only
    uses this class in an `isinstance` check to detect Vertex AI clients, so a
    placeholder is safe when the old LangChain module path is unavailable.
    """
    module_name = "langchain_community.chat_models.vertexai"
    try:
        importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        if exc.name != module_name:
            raise
        compatibility_module = types.ModuleType(module_name)

        class _UnavailableChatVertexAI:
            pass

        compatibility_module.ChatVertexAI = _UnavailableChatVertexAI
        sys.modules[module_name] = compatibility_module


def _load_dataset(dataset_path: Path | None, top_k: int) -> list[dict]:
    if dataset_path is None:
        return collect_evaluation_data(top_k=top_k)

    with dataset_path.open("r", encoding="utf-8") as file:
        dataset = json.load(file)
    if not isinstance(dataset, list) or not dataset:
        raise ValueError(f"Evaluation dataset must be a non-empty JSON list: {dataset_path}")
    return dataset


def _write_results(records: list[dict], scores: list[dict]) -> tuple[Path, Path]:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    per_question_path = RESULTS_DIR / f"ragas_scores_{run_id}.csv"
    summary_path = RESULTS_DIR / f"ragas_summary_{run_id}.json"

    metric_names = list(scores[0]) if scores else []
    fieldnames = ["id", "topic", "user_input", *metric_names]
    with per_question_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for record, row_scores in zip(records, scores):
            writer.writerow({
                "id": record.get("id", ""),
                "topic": record.get("topic", ""),
                "user_input": record["user_input"],
                **row_scores,
            })

    summary = {}
    valid_score_counts = {}
    for name in metric_names:
        values = [
            float(row[name]) for row in scores
            if row.get(name) is not None and math.isfinite(float(row[name]))
        ]
        summary[name] = sum(values) / len(values) if values else None
        valid_score_counts[name] = len(values)

    with summary_path.open("w", encoding="utf-8") as file:
        json.dump(
            {
                "run_id": run_id,
                "dataset_size": len(records),
                "average_scores": summary,
                "valid_score_counts": valid_score_counts,
                "per_question_scores": str(per_question_path.relative_to(ROOT_DIR)),
            },
            file,
            indent=2,
        )

    return per_question_path, summary_path


def run_evaluation(dataset_path: Path | None = None, top_k: int = 5) -> tuple[Path, Path]:
    """Collect (unless supplied), score, and save a Ragas evaluation run."""
    if importlib.util.find_spec("ragas") is None:
        raise RuntimeError(
            "Ragas is not installed in this Python environment. Activate the project venv and run: "
            "python -m pip install -r requirements.txt"
        )

    try:
        _install_ragas_optional_vertexai_compatibility()
        import ragas
        from ragas import EvaluationDataset, evaluate
        from ragas.metrics import (
            Faithfulness,
            FactualCorrectness,
            ContextEntityRecall,
            LLMContextPrecisionWithReference,
            LLMContextRecall,
            NoiseSensitivity,
            ResponseRelevancy,
            SemanticSimilarity,
        )
    except ImportError as exc:
        ragas_version = importlib.metadata.version("ragas")
        raise RuntimeError(
            f"Ragas {ragas_version} is installed, but one of its imports is incompatible with this "
            f"environment: {exc}. This project requires ragas>=0.3.9,<0.4."
        ) from exc

    records = _load_dataset(dataset_path, top_k)
    required_fields = {"user_input", "retrieved_contexts", "response", "reference"}
    for index, record in enumerate(records, start=1):
        missing = required_fields - record.keys()
        if missing:
            raise ValueError(f"Evaluation record {index} is missing fields: {', '.join(sorted(missing))}")

    evaluator_llm, evaluator_embeddings, run_config = _make_evaluator()
    metrics = [
        LLMContextPrecisionWithReference(),
        LLMContextRecall(),
        ContextEntityRecall(),
        Faithfulness(),
        NoiseSensitivity(),
        ResponseRelevancy(),
        FactualCorrectness(),
        SemanticSimilarity(),
    ]
    result = evaluate(
        dataset=EvaluationDataset.from_list(records),
        metrics=metrics,
        llm=evaluator_llm,
        embeddings=evaluator_embeddings,
        run_config=run_config,
        # Keep the run and save successful metric scores if an individual
        # evaluator request times out; failed cells are recorded as NaN.
        raise_exceptions=False,
    )
    scores = result.scores
    per_question_path, summary_path = _write_results(records, scores)

    with summary_path.open("r", encoding="utf-8") as file:
        summary = json.load(file)
    averages = summary["average_scores"]
    valid_counts = summary["valid_score_counts"]
    print("\nAverage Ragas scores:")
    for metric, score in averages.items():
        rendered_score = f"{score:.4f}" if score is not None else "n/a"
        print(f"  {metric}: {rendered_score} ({valid_counts[metric]}/{len(records)} scored)")
    print(f"\nPer-question scores: {per_question_path}")
    print(f"Summary: {summary_path}")
    return per_question_path, summary_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Evaluate the RAG pipeline with Ragas")
    parser.add_argument("--dataset", type=Path, help="Score an existing ragas_dataset.json")
    parser.add_argument("--top-k", type=int, default=5, help="Retrieved chunks per question")
    args = parser.parse_args()
    run_evaluation(dataset_path=args.dataset, top_k=args.top_k)
