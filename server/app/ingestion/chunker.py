from bisect import bisect_right

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# ~1000 characters is ~200-250 tokens: large enough to keep a paragraph or a short
# list together, and within all-MiniLM-L6-v2's 256-token input (longer text is
# truncated before embedding).
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 150

PAGE_SEPARATOR = "\n\n"


def join_pages(pages: list[Document]) -> list[Document]:
    """Join a PDF's pages into one document so chunks can cross page breaks.

    The start offset of every page is kept in `page_starts` (with the 0-based
    page numbers in `page_numbers`) so each chunk can be mapped back to the
    page it starts on.
    """
    if not pages:
        return []
    text_parts, page_starts, page_numbers = [], [], []
    offset = 0
    for page in pages:
        content = page.page_content or ""
        page_starts.append(offset)
        page_numbers.append(page.metadata.get("page"))
        text_parts.append(content)
        offset += len(content) + len(PAGE_SEPARATOR)
    metadata = {
        key: value
        for key, value in pages[0].metadata.items()
        if key not in {"page", "page_label"}
    }
    metadata.update({"page_starts": page_starts, "page_numbers": page_numbers})
    return [Document(page_content=PAGE_SEPARATOR.join(text_parts), metadata=metadata)]


def _page_for_offset(metadata: dict, start_index: int | None):
    starts = metadata.get("page_starts")
    numbers = metadata.get("page_numbers")
    if not starts or start_index is None:
        return metadata.get("page")
    position = max(bisect_right(starts, start_index) - 1, 0)
    return numbers[position]


def chunk_documents(
    pages: list[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> list[Document]:
    """Split documents into overlapping chunks.

    - Documents with `section_path` metadata (DOCX/Markdown headings) get that
      heading path as the first line of every chunk, so each chunk says which
      section it belongs to (the heading is not part of the page text).
    - Joined PDF documents (see `join_pages`) get each chunk's start page.
    """
    if not pages:
        return []

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap must be between 0 and chunk_size"
        )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""],
        # Keep ". " at the end of the sentence it closes, not at the start of the next chunk.
        keep_separator="end",
        add_start_index=True
    )

    chunks = []
    for chunk in splitter.split_documents(pages):
        metadata = dict(chunk.metadata)
        if "page_starts" in metadata:
            metadata["page"] = _page_for_offset(metadata, metadata.get("start_index"))
            metadata.pop("page_starts", None)
            metadata.pop("page_numbers", None)
        content = chunk.page_content
        section_path = metadata.get("section_path")
        if section_path:
            content = f"{section_path}\n\n{content}"
        chunks.append(Document(page_content=content, metadata=metadata))

    return chunks
