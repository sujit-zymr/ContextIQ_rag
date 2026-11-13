
import argparse

from app.database.connection import init_db
from app.ingestion.pipeline import ingest_file
from app.retrieval.similarity_search import search_similar_chunks
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
        help="Path to the text document"
    )

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

    search_parser.add_argument(
        "--top-k",
        type=int,
        default=5
    )

    args = parser.parse_args()
    configure_observability()

    try:
        if args.command == "init-db":

            init_db()

        elif args.command == "ingest":

            init_db()

            with observation_span("rag.ingest", input_value={"file": args.file}) as span:
                document_id = ingest_file(args.file)
                set_span_output(span, {"document_id": document_id})

            print(f"Document ID: {document_id}")

        elif args.command == "search":

            with observation_span("rag.search_request", input_value=args.question) as span:
                results = search_similar_chunks(args.question, args.top_k)
                set_span_output(span, results)

            print("\nRetrieved Context:\n")
            for index, result in enumerate(results, 1):

                print(f"Result {index}")
                print("File:", result["filename"])
                print("Page:", result["page"])
                print("Chunk:", result["chunk_index"])
                print("Similarity:", round(result["similarity"], 4))
                print("Content:", result["content"])
                print("-" * 50)

        elif args.command == "answer":
            with observation_span("rag.answer_request", input_value=args.question) as span:
                chunks = search_similar_chunks(args.question, args.top_k)

                try:
                    answer = generate_answer(args.question, chunks)
                except AnswerGenerationError as exc:
                    parser.error(str(exc))
                set_span_output(span, {"answer": answer})

            print("\nQuestion::\n")
            print(args.question)
            print("\nAnswer:\n")
            print(answer)
        elif args.command == "evaluate":
            run_ragas_evaluation(args.dataset, args.output_dir)
    finally:
        flush_observability()

if __name__ == "__main__":
    main()
