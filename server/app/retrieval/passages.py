"""Turn reranked chunk hits into context passages for the answer prompt.

A single chunk is often only part of what answers a question (the rest of a
list, the sentence before a number). For every hit we add its neighbouring
chunks from the same document and merge hits whose windows touch, so the
prompt gets whole passages instead of fragments, and near-duplicate hits
(overlapping chunks) collapse into one source.
"""

import os

DEFAULT_CONTEXT_WINDOW = 1
MAX_OVERLAP_CHARS = 1000


def context_window() -> int:
    """Neighbouring chunks added on each side of a hit (RAG_CONTEXT_WINDOW, default 1)."""
    raw = os.getenv("RAG_CONTEXT_WINDOW", str(DEFAULT_CONTEXT_WINDOW))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError("RAG_CONTEXT_WINDOW must be an integer") from exc
    if value < 0:
        raise ValueError("RAG_CONTEXT_WINDOW must be zero or positive")
    return value


def _reach(window: int) -> int:
    """How far (in chunks) from a passage's best hit the passage may extend."""
    return 2 * window if window > 0 else 1


def select_hits(hits: list[dict], top_k: int, window: int) -> list[list[dict]]:
    """Group hits (best first) into at most `top_k` groups of nearby chunks.

    A hit within `_reach(window)` chunks of a group's *best* hit (same document)
    joins that group instead of taking a new slot; measuring from the best hit,
    not from any member, stops groups from chaining across a document.
    """
    groups: list[list[dict]] = []
    reach = _reach(window)
    for hit in hits:
        document_id = hit.get("document_id")
        index = hit.get("chunk_index")
        target = None
        if index is not None:
            for group in groups:
                best = group[0]
                if (
                    best.get("document_id") == document_id
                    and best.get("chunk_index") is not None
                    and abs(best["chunk_index"] - index) <= reach
                ):
                    target = group
                    break
        if target is not None:
            target.append(hit)
        elif len(groups) < top_k:
            groups.append([hit])
    return groups


def window_indexes(group: list[dict], window: int) -> list[int]:
    """Chunk indexes covering the group's hits plus `window` on each side,
    limited to `_reach(window)` chunks either side of the best hit (so a passage
    is at most 2 * reach + 1 chunks long)."""
    best_index = group[0].get("chunk_index")
    if best_index is None:
        return []
    reach = _reach(window)
    low, high = max(best_index - reach, 0), best_index + reach
    indexes = set()
    for hit in group:
        index = hit.get("chunk_index")
        if index is None:
            continue
        for offset in range(-window, window + 1):
            if low <= index + offset <= high:
                indexes.add(index + offset)
    return sorted(indexes)


def join_overlapping(first: str, second: str, max_overlap: int = MAX_OVERLAP_CHARS) -> str:
    """Concatenate two consecutive chunks without repeating their shared overlap."""
    if not first:
        return second
    if not second:
        return first
    limit = min(len(first), len(second), max_overlap)
    for size in range(limit, 0, -1):
        if first.endswith(second[:size]):
            return first + second[size:]
    return f"{first}\n{second}"


def _chunk_body(chunk: dict) -> str:
    """Chunk text without its section header line (added again once per passage)."""
    content = (chunk.get("content") or "").strip()
    header = (chunk.get("metadata") or {}).get("section_path")
    prefix = f"{header}\n\n" if header else None
    if prefix and content.startswith(prefix):
        return content[len(prefix):]
    return content


def build_passage(group: list[dict], neighbours: dict[int, dict], window: int) -> dict:
    """Merge a group of hits and their neighbour chunks into one passage.

    `neighbours` maps chunk_index -> chunk row ({content, metadata}) for the
    group's document; it may hold chunks loaded for other passages of the same
    document, so only this group's window (`window_indexes`) is used. The
    passage keeps the best hit's scores and metadata.
    """
    best = group[0]
    wanted = window_indexes(group, window)
    indexes = [index for index in wanted if index in neighbours] or [best.get("chunk_index")]
    text = ""
    headers_seen = set()
    for index in indexes:
        chunk = neighbours.get(index) or (best if index == best.get("chunk_index") else None)
        if chunk is None:
            continue
        header = (chunk.get("metadata") or {}).get("section_path")
        body = _chunk_body(chunk)
        if header and header not in headers_seen:
            headers_seen.add(header)
            body = f"{header}\n\n{body}"
            text = f"{text}\n\n{body}" if text else body
        else:
            text = join_overlapping(text, body)

    pages = sorted({
        page
        for page in (
            _page_number(neighbours.get(index)) for index in indexes
        )
        if page is not None
    } | ({best["page"]} if best.get("page") is not None else set()))

    return {
        **best,
        "content": text or best.get("content"),
        "chunk_indexes": indexes,
        "hit_chunk_indexes": sorted(h.get("chunk_index") for h in group if h.get("chunk_index") is not None),
        "pages": pages,
        "retrieval_method": "hybrid",
    }


def _page_number(chunk: dict | None) -> int | None:
    """1-based page from chunk metadata (stored 0-based, as in search results)."""
    if not chunk:
        return None
    page = (chunk.get("metadata") or {}).get("page")
    return page + 1 if isinstance(page, int) else None
