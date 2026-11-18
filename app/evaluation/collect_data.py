
import json
from pathlib import Path

from app.retrieval.similarity_search import search_chunks
from app.generation.answerer import generate_answer


ROOT_DIR = Path(__file__).resolve().parents[2]

QUESTIONS_FILE = ROOT_DIR / "app" / "evaluation_data" / "policy_questions.json"
OUTPUT_FILE = ROOT_DIR / "evaluation_data" / "ragas_dataset.json"


def collect_evaluation_data():

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as file:
        evaluation_data = json.load(file)

    questions = evaluation_data["questions"]

    dataset = []

    for index, item in enumerate(questions, start=1):

        question = item["question"]

        print(f"\nQuestion {index}/{len(questions)}")
        print(f"ID: {item['id']}")
        print(f"Question: {question}")

        # 1. Retrieve chunks
        chunks = search_chunks(
            question,
            top_k=5,
            mode="hybrid",
        )

        # 2. Extract retrieved contexts
        retrieved_contexts = [
            chunk["content"]
            for chunk in chunks
        ]

        # 3. Generate answer
        generated = generate_answer(
            question,
            chunks,
            search_mode="hybrid",
        )
        response = generated["answer"]

        # 4. Prepare evaluation record
        dataset.append({
            "id": item["id"],
            "topic": item.get("category", item.get("topic", "uncategorized")),
            "category": item.get("category", item.get("topic", "uncategorized")),
            "user_input": question,
            "retrieved_contexts": retrieved_contexts,
            "retrieved_chunks": [
                {
                    "document_id": chunk.get("document_id"),
                    "filename": chunk.get("filename"),
                    "page": chunk.get("page"),
                    "chunk_index": chunk.get("chunk_index"),
                }
                for chunk in chunks
            ],
            "response": response,
            "citations": generated["citations"],
            "abstained": generated["abstained"],
            "should_abstain": item.get("should_abstain", False),
            "reference": item["expected_answer"],
            "relevant_pages": item["relevant_pages"],
            "retrieved_pages": [
                chunk["page"]
                for chunk in chunks
                if chunk["page"] is not None
            ]
        })
        if "forbidden_document_ids" in item:
            dataset[-1]["forbidden_document_ids"] = item["forbidden_document_ids"]

        print(f"Retrieved chunks: {len(retrieved_contexts)}")
        print(f"Expected pages: {item['relevant_pages']}")
        print(f"Retrieved pages: {dataset[-1]['retrieved_pages']}")
        print(f"Generated answer: {response}")
        print(f"Validated citations: {generated['citations']}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            dataset,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(f"\nDataset saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    collect_evaluation_data()
