
import argparse

from app.database.connection import init_db
from app.ingestion.pipeline import ingest_file
from app.retrieval.similarity_search import search_similar_chunks
from app.generation.answerer import (
    AnswerGenerationError,
    generate_answer,
)

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

    evaluate_parser = subparsers.add_parser(
        "evaluate",
        help="Run Ragas metrics against the RAG pipeline"
    )
    evaluate_parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of chunks to retrieve per question"
    )
    evaluate_parser.add_argument(
        "--dataset",
        help="Score an existing evaluation JSON file instead of rerunning the pipeline"
    )

    search_parser.add_argument(
        "question",
        help="Question to search"
    )

    search_parser.add_argument(
        "--top-k",
        type=int,
        default=5
    )

    args = parser.parse_args()

    if args.command == "init-db":

        init_db()

    elif args.command == "ingest":

        init_db()

        document_id = ingest_file(args.file)

        print(f"Document ID: {document_id}")

    elif args.command == "search":

        results = search_similar_chunks(
            args.question,
            args.top_k
        )

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
        chunks = search_similar_chunks(
            args.question,
            args.top_k
        )

        try:
            answer = generate_answer(args.question, chunks)
        except AnswerGenerationError as exc:
            parser.error(str(exc))

        print("\nQuestion::\n")
        print(args.question)
        print("\nAnswer:\n")
        print(answer)

    elif args.command == "evaluate":
        from pathlib import Path
        from app.evaluation.evaluate import run_evaluation

        try:
            run_evaluation(
                dataset_path=Path(args.dataset) if args.dataset else None,
                top_k=args.top_k,
            )
        except (RuntimeError, ValueError) as exc:
            parser.error(str(exc))

if __name__ == "__main__":
    main()
