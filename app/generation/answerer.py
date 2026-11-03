import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.generation.prompt import build_rag_prompt


class AnswerGenerationError(Exception):
    """Raised when the answer cannot be generated."""


def _response_text(content) -> str:
    if isinstance(content, str):
        return content.strip()

    # Some models return content blocks instead of one string.
    if isinstance(content, list):
        text_blocks = [
            block["text"]
            for block in content
            if isinstance(block, dict)
            and isinstance(block.get("text"), str)
        ]
        return "\n".join(text_blocks).strip()

    return ""

def generate_answer(question: str, chunks: list[dict]) -> str:
    load_dotenv()

    usable_chunks = [
        chunk for chunk in chunks
        if chunk.get("content") and chunk["content"].strip()
    ]

    if not usable_chunks:
        return "I don't have enough information to answer from the retrieved context."

    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise AnswerGenerationError(
            "NVIDIA_API_KEY is not set. Add your NVIDIA API key to .env."
        )

    model_name = (
        os.getenv(
            "NVIDIA_MODEL",
            "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
        )
        or "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
    ).strip()
    system_prompt, user_prompt = build_rag_prompt(question, usable_chunks)

    try:
        model = ChatOpenAI(
            model=model_name,
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key,
            temperature=0.6,
            top_p=0.95,
            max_tokens=4096,
            extra_body={"reasoning_budget": 1024},
        )

        response = model.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ])
    except Exception as exc:
        # Include the underlying error while ensuring the API key is not shown.
        error_detail = str(exc).replace(api_key, "[REDACTED]")
        raise AnswerGenerationError(
            f"NVIDIA request failed for model '{model_name}': {error_detail}"
        ) from exc

    answer = _response_text(response.content)
    if not answer:
        raise AnswerGenerationError("NVIDIA returned an empty response.")

    return answer
