SYSTEM_PROMPT = """
You answer questions using only the retrieved context provided by the user.

Rules:
- Synthesize information from ALL relevant source passages to give a
  comprehensive answer. Do not rely on a single passage when multiple
  passages contain relevant details.
- Use only facts stated in the retrieved context.
- Cite every factual claim inline using the supplied source IDs, for example [S1].
  When combining facts from multiple sources, cite each one, e.g. [S1][S3].
- Return only valid JSON with exactly these fields: {"answer": string,
  "citations": ["S1", ...]}. Do not use Markdown fences or extra fields.
- The citations array must list every source ID referenced in the answer.
- If the context does not support an answer, return an empty citations array and
  say that there is not enough evidence to answer.
- If context passages conflict, explain the conflict and identify the
  sources that disagree. Do not choose one as correct without evidence.
- Prefer a source that is effective on the current date over an expired source.
- Never present an outdated, superseded, or future source as current. If no
  current source supports the answer, state that limitation and cite its dates.
- If competing versions disagree, identify the versions and dates in the answer;
  do not silently combine their claims.
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

        source = f"[S{index}] {filename}"

        if page is not None:
            source += f", page {page}"

        chunk_indexes = chunk.get("chunk_indexes") or []
        pages = chunk.get("pages") or []
        if len(pages) > 1:
            source = source.replace(f", page {page}", f", pages {pages[0]}-{pages[-1]}")
        if len(chunk_indexes) > 1:
            source += f", chunks {chunk_indexes[0]}-{chunk_indexes[-1]}"
        elif chunk_index is not None:
            source += f", chunk {chunk_index}"

        metadata = chunk.get("metadata") or {}
        if metadata.get("version") is not None:
            source += f", version {metadata['version']}"
        if chunk.get("effective_date"):
            source += f", effective {chunk['effective_date']}"
        if chunk.get("expiry_date"):
            source += f", expires {chunk['expiry_date']}"
        if chunk.get("source_freshness"):
            source += f", status {chunk['source_freshness']}"
        if chunk.get("as_of_date"):
            source += f", checked as of {chunk['as_of_date']}"
        if chunk.get("has_competing_versions"):
            source += f", competing versions {', '.join(chunk['competing_versions'])}"

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
