
import json
from pathlib import Path

from app.retrieval.similarity_search import search_similar_chunks
from app.generation.answerer import generate_answer


ROOT_DIR = Path(__file__).resolve().parents[2]

QUESTIONS_FILE = ROOT_DIR / "app" / "evaluation_data" / "policy_questions.json"
OUTPUT_FILE = ROOT_DIR / "evaluation_data" / "ragas_dataset.json"


def collect_evaluation_data(top_k=5):

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
        chunks = search_similar_chunks(
            question,
            top_k=top_k
        )

        # 2. Extract retrieved contexts
        retrieved_contexts = [
            chunk["content"]
            for chunk in chunks
        ]

        # 3. Generate answer
        response = generate_answer(
            question,
            chunks
        )

        # 4. Prepare evaluation record
        dataset.append({
            "id": item["id"],
            "topic": item["topic"],
            "user_input": question,
            "retrieved_contexts": retrieved_contexts,
            "response": response,
            "reference": item["expected_answer"],
            "relevant_pages": item["relevant_pages"],
            "retrieved_pages": [
                chunk["page"]
                for chunk in chunks
                if chunk["page"] is not None
            ]
        })

        print(f"Retrieved chunks: {len(retrieved_contexts)}")
        print(f"Expected pages: {item['relevant_pages']}")
        print(f"Retrieved pages: {dataset[-1]['retrieved_pages']}")
        print(f"Generated answer: {response}")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:
        json.dump(
            dataset,
            file,
            indent=4,
            ensure_ascii=False
        )

    print(f"\nDataset saved to: {OUTPUT_FILE}")
    return dataset


if __name__ == "__main__":
    collect_evaluation_data()
