import json
import os
import re

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.generation.prompt import build_rag_prompt
from app.retrieval.evidence import INSUFFICIENT_EVIDENCE_RESPONSE, assess_evidence
from app.observability import (
    langchain_callbacks,
    observation_span,
    redact_sensitive_text,
    set_span_metadata,
    set_span_output,
)


class AnswerGenerationError(Exception):
    """Raised when the answer cannot be generated."""


_CITATION_MARKER = re.compile(r"\[(S\d+)\]")


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


def _abstention(reason: str) -> dict:
    return {
        "answer": INSUFFICIENT_EVIDENCE_RESPONSE,
        "citations": [],
        "abstained": True,
        "reason": reason,
    }


def _parse_structured_answer(response_text: str) -> dict | None:
    candidate = response_text.strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(candidate[start:end + 1])
        except json.JSONDecodeError:
            return None
    if not isinstance(parsed, dict):
        return None
    if not isinstance(parsed.get("answer"), str) or not isinstance(parsed.get("citations"), list):
        return None
    if not all(isinstance(source_id, str) for source_id in parsed["citations"]):
        return None
    return parsed


def _validate_citations(answer_payload: dict, chunks: list[dict]) -> dict:
    source_chunks = {f"S{index}": chunk for index, chunk in enumerate(chunks, start=1)}
    answer_text = answer_payload["answer"].strip()
    declared_ids = set(answer_payload["citations"])
    inline_ids = set(_CITATION_MARKER.findall(answer_text))
    valid_ids = [
        source_id for source_id in source_chunks
        if source_id in declared_ids and source_id in inline_ids
    ]
    # Strip every unverified or undeclared marker from the model's answer.
    answer_text = _CITATION_MARKER.sub(
        lambda match: match.group(0) if match.group(1) in valid_ids else "",
        answer_text,
    ).strip()
    if not answer_text or not valid_ids:
        return _abstention("The generated response did not cite a retrieved source.")

    citations = []
    for source_id in valid_ids:
        chunk = source_chunks[source_id]
        metadata = chunk.get("metadata") or {}
        citations.append({
            "source_id": source_id,
            "document_id": chunk.get("document_id"),
            "title": metadata.get("title") or chunk.get("filename") or "Unknown document",
            "filename": chunk.get("filename"),
            "page": chunk.get("page"),
            "chunk_index": chunk.get("chunk_index"),
            "section": metadata.get("section"),
            "version": metadata.get("version"),
            "effective_date": chunk.get("effective_date"),
            "expiry_date": chunk.get("expiry_date"),
            "as_of_date": chunk.get("as_of_date"),
            "source_freshness": chunk.get("source_freshness"),
            "has_competing_versions": chunk.get("has_competing_versions", False),
            "competing_versions": chunk.get("competing_versions", []),
        })
    return {"answer": answer_text, "citations": citations, "abstained": False, "reason": None}


def generate_answer(
    question: str,
    chunks: list[dict],
    search_mode: str | None = None,
) -> dict:
    load_dotenv()

    usable_chunks = [
        chunk for chunk in chunks
        if chunk.get("content") and chunk["content"].strip()
    ]

    try:
        evidence = assess_evidence(usable_chunks, search_mode)
    except ValueError as exc:
        raise AnswerGenerationError(f"Invalid evidence threshold configuration: {exc}") from exc
    with observation_span(
        "rag.evidence_gate",
        input_value={
            "retrieval_mode": evidence["mode"],
            "retrieved_count": len(usable_chunks),
            "best_score": evidence["best_score"],
            "threshold": evidence["threshold"],
        },
    ) as evidence_span:
        set_span_output(evidence_span, evidence)
    if not evidence["sufficient"]:
        return _abstention(evidence["reason"])

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

    with observation_span(
        "rag.answer_generation",
        input_value={"question": question, "model": model_name},
        as_type="chain",
    ) as span:
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

            response = model.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=user_prompt),
                ],
                config={"callbacks": langchain_callbacks()},
            )
        except Exception as exc:
            # Include the underlying error while ensuring the API key is not shown.
            error_detail = redact_sensitive_text(str(exc).replace(api_key, "[REDACTED]"))
            raise AnswerGenerationError(
                f"NVIDIA request failed for model '{model_name}': {error_detail}"
            ) from exc

        raw_answer = _response_text(response.content)
        parsed_answer = _parse_structured_answer(raw_answer)
        if parsed_answer is None:
            answer_result = _abstention("The model response was not valid citation JSON.")
        else:
            answer_result = _validate_citations(parsed_answer, usable_chunks)

        set_span_output(span, answer_result)
        usage = getattr(response, "usage_metadata", None)
        response_metadata = getattr(response, "response_metadata", None)
        if not usage and isinstance(response_metadata, dict):
            usage = response_metadata.get("token_usage")
        if isinstance(usage, dict):
            # Langfuse's callback captures generation data; preserve an explicit
            # token count on this span when NVIDIA returns usage metadata.
            set_span_metadata(span, {"model_usage": usage})
        return answer_result
