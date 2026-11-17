
import argparse

from app.database.connection import init_db
from app.ingestion.pipeline import ingest_file, reindex_document
from app.database.chunk_repository import delete_document
from app.retrieval.similarity_search import search_chunks
from app.generation.answerer import (
    AnswerGenerationError,
    generate_answer,
)
from app.observability import (
    configure_observability,
    flush_observability,
    observation_span,
    set_span_output,
)
from app.evaluation.ragas_eval import DEFAULT_DATASET, DEFAULT_OUTPUT_DIR, run_ragas_evaluation
from app.evaluation.collect_data import collect_evaluation_data

def main():

    parser = argparse.ArgumentParser(
        description="Basic RAG Pipeline"
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True
    )

    # Initialize database
    subparsers.add_parser("init-db")

    # Ingest document
    ingest_parser = subparsers.add_parser("ingest")

    ingest_parser.add_argument(
        "file",
        help="Path to a PDF, TXT, DOCX, MD, or Markdown document"
    )
    ingest_parser.add_argument("--title", help="Human readable document title")
    ingest_parser.add_argument("--department", help="Department metadata value")
    ingest_parser.add_argument("--version", help="Document version metadata value")
    ingest_parser.add_argument("--effective-date", help="Date the document takes effect (YYYY-MM-DD)")
    ingest_parser.add_argument("--expiry-date", help="Last date the document is effective (YYYY-MM-DD)")
    ingest_parser.add_argument(
        "--permission", action="append", dest="permissions",
        help="Permission label metadata; repeat to add multiple labels (not access control)",
    )
    ingest_parser.add_argument("--chunk-size", type=int, help="Chunk size in characters; default from RAG_CHUNK_SIZE or 200")
    ingest_parser.add_argument("--chunk-overlap", type=int, help="Chunk overlap in characters; default from RAG_CHUNK_OVERLAP or 40")

    reindex_parser = subparsers.add_parser("reindex", help="Re-extract and re-embed a stored document")
    reindex_parser.add_argument("document_id", help="Document UUID returned by ingest")
    reindex_parser.add_argument("--chunk-size", type=int)
    reindex_parser.add_argument("--chunk-overlap", type=int)

    delete_parser = subparsers.add_parser("delete", help="Delete a document and its chunks")
    delete_parser.add_argument("document_id", help="Document UUID returned by ingest")

    # Search document
    search_parser = subparsers.add_parser("search")

    answer_parser = subparsers.add_parser(
        "answer",
        help="Retrieve context and generate an answer"
    )
    answer_parser.add_argument(
    "question",
    help="Question to answer"
    )

    answer_parser.add_argument(
        "--top-k",
        type=int,
        default=5
    )
    answer_parser.add_argument(
        "--search-mode", choices=("vector", "full-text", "hybrid"), default="hybrid",
        help="Retrieval method to use",
    )

    search_parser.add_argument(
        "question",
        help="Question to search"
    )

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Evaluate a RAG dataset with Ragas and link scores to Langfuse traces",
    )
    evaluate_parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET),
        help="JSON dataset with user_input, retrieved_contexts, response, and reference fields",
    )
    evaluate_parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for per-sample CSV scores and the summary JSON",
    )
    evaluate_parser.add_argument(
        "--save-baseline", action="store_true",
        help="Save this run as immutable output_dir/baseline.json (fails if one already exists)",
    )
    evaluate_parser.add_argument(
        "--enforce-quality-gate", action="store_true",
        help="Exit with an error after saving the report if any quality gate fails",
    )
    subparsers.add_parser(
        "collect-evaluation-data",
        help="Run the policy question set through retrieval and generation to refresh the evaluation dataset",
    )

    search_parser.add_argument(
        "--top-k",
        type=int,
        default=5
    )
    search_parser.add_argument(
        "--search-mode", choices=("vector", "full-text", "hybrid"), default="hybrid",
        help="Retrieval method to use",
    )

    args = parser.parse_args()
    configure_observability()

    try:
        if args.command == "init-db":

            init_db()

        elif args.command == "ingest":

            init_db()

            with observation_span("rag.ingest", input_value={"file": args.file}) as span:
                metadata = {
                    key: value for key, value in {
                        "title": args.title,
                        "department": args.department,
                        "version": args.version,
                        "effective_date": args.effective_date,
                        "expiry_date": args.expiry_date,
                        "permissions": args.permissions,
                    }.items() if value is not None
                }
                document_id = ingest_file(
                    args.file,
                    metadata=metadata,
                    chunk_size=args.chunk_size,
                    overlap=args.chunk_overlap,
                )
                set_span_output(span, {"document_id": document_id})

            print(f"Document ID: {document_id}")

        elif args.command == "reindex":
            init_db()
            document_id = reindex_document(
                args.document_id, chunk_size=args.chunk_size, overlap=args.chunk_overlap
            )
            print(f"Reindexed document: {document_id}")

        elif args.command == "delete":
            init_db()
            if delete_document(args.document_id):
                print(f"Deleted document and its chunks: {args.document_id}")
            else:
                parser.error(f"Document not found: {args.document_id}")

        elif args.command == "search":

            with observation_span("rag.search_request", input_value=args.question) as span:
                results = search_chunks(args.question, args.top_k, args.search_mode)
                set_span_output(span, results)

            print("\nRetrieved Context:\n")
            for index, result in enumerate(results, 1):

                print(f"Result {index}")
                print("File:", result["filename"])
                print("Page:", result["page"])
                print("Chunk:", result["chunk_index"])
                print("Source status:", result.get("source_freshness", "unknown"))
                if result.get("has_competing_versions"):
                    print("Competing versions:", ", ".join(result["competing_versions"]))
                score = result.get("similarity", result.get("score"))
                score_label = {
                    "vector": "Similarity",
                    "full-text": "Full-text rank",
                    "hybrid": "Reranker score" if result.get("reranked") else "RRF rank score",
                }[args.search_mode]
                print(f"{score_label}:", round(score, 4) if score is not None else "n/a")
                print("Content:", result["content"])
                print("-" * 50)

        elif args.command == "answer":
            with observation_span("rag.answer_request", input_value=args.question) as span:
                chunks = search_chunks(args.question, args.top_k, args.search_mode)

                try:
                    answer = generate_answer(args.question, chunks, search_mode=args.search_mode)
                except AnswerGenerationError as exc:
                    parser.error(str(exc))
                set_span_output(span, answer)

            print("\nQuestion::\n")
            print(args.question)
            print("\nAnswer:\n")
            print(answer["answer"])
            if answer["citations"]:
                print("\nCitations:")
                for citation in answer["citations"]:
                    location = []
                    if citation.get("page") is not None:
                        location.append(f"page {citation['page']}")
                    if citation.get("chunk_index") is not None:
                        location.append(f"chunk {citation['chunk_index']}")
                    if citation.get("version") is not None:
                        location.append(f"version {citation['version']}")
                    if citation.get("source_freshness"):
                        location.append(citation["source_freshness"])
                    if citation.get("effective_date"):
                        location.append(f"effective {citation['effective_date']}")
                    if citation.get("expiry_date"):
                        location.append(f"expires {citation['expiry_date']}")
                    if citation.get("as_of_date"):
                        location.append(f"checked {citation['as_of_date']}")
                    suffix = f" ({', '.join(location)})" if location else ""
                    print(f"[{citation['source_id']}] {citation['title']}{suffix}")
                    if citation.get("has_competing_versions"):
                        print("  Competing versions:", ", ".join(citation["competing_versions"]))
        elif args.command == "evaluate":
            run_ragas_evaluation(
                args.dataset,
                args.output_dir,
                save_baseline=args.save_baseline,
                enforce_quality_gate=args.enforce_quality_gate,
            )
        elif args.command == "collect-evaluation-data":
            init_db()
            collect_evaluation_data()
    finally:
        flush_observability()

if __name__ == "__main__":
    main()
