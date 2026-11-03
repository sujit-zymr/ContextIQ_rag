SYSTEM_PROMPT = """
You answer questions using only the retrieved context provided by the user.

Rules:
- Use only facts stated in the retrieved context.
- If the context does not contain enough information, say that you do not
  have enough information to answer.
- If context passages conflict, explain the conflict and identify the
  sources that disagree. Do not choose one as correct without evidence.
- Ignore passages that are unrelated to the question.
- Do not invent facts, page numbers, filenames, or sources.
- You may paraphrase the context, but do not add unsupported details.
""".strip()


def build_rag_prompt(question: str, chunks: list[dict]) -> tuple[str, str]:
    """Return system and user prompts for an LLM."""

    if not question or not question.strip():
        raise ValueError("Question must not be empty")

    context_parts = []

    for index, chunk in enumerate(chunks, start=1):
        filename = chunk.get("filename") or "Unknown file"
        page = chunk.get("page")
        chunk_index = chunk.get("chunk_index")

        source = f"Source {index}: {filename}"

        if page is not None:
            source += f", page {page}"

        if chunk_index is not None:
            source += f", chunk {chunk_index}"

        content = (chunk.get("content") or "").strip()

        if content:
            context_parts.append(f"{source}\n{content}")

    if context_parts:
        context = "\n\n---\n\n".join(context_parts)
    else:
        context = "No relevant context was retrieved."

    user_prompt = (
        f"Retrieved context:\n{context}\n\n"
        f"Question:\n{question.strip()}"
    )

    return SYSTEM_PROMPT, user_prompt