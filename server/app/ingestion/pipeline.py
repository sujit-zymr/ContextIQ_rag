import hashlib
import os
import re
from datetime import date
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from app.database.chunk_repository import (
    complete_document_ingestion,
    fail_document_ingestion,
    get_document,
    start_document_ingestion,
)
from app.ingestion.chunker import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    chunk_documents,
    join_pages,
)
from app.ingestion.embedder import generate_embeddings
from app.observability import observation_span, set_span_output


class _SectionCollector:
    """Collects body text per section, tracking the heading path ("A > B > C").

    Headings are kept in metadata (`section` = innermost heading, `section_path`
    = full path), not in the text: the chunker adds the path to every chunk.
    """

    def __init__(self, source):
        self.source = str(source)
        self.stack: list[tuple[int, str]] = []
        self.body: list[str] = []
        self.documents: list[Document] = []

    def heading(self, level: int, title: str):
        self.flush()
        while self.stack and self.stack[-1][0] >= level:
            self.stack.pop()
        self.stack.append((level, title))

    def line(self, text: str):
        self.body.append(text)

    def flush(self):
        content = "\n".join(self.body).strip()
        self.body = []
        if not content:
            return
        if self.stack:
            section = self.stack[-1][1]
            section_path = " > ".join(title for _, title in self.stack)
        else:
            section, section_path = "Document", None
        metadata = {"source": self.source, "page": None, "section": section}
        if section_path:
            metadata["section_path"] = section_path
        self.documents.append(Document(page_content=content, metadata=metadata))


_MARKDOWN_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")


def _extract_markdown(file_path):
    text = file_path.read_text(encoding="utf-8", errors="replace")
    sections = _SectionCollector(file_path)
    in_code_block = False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_code_block = not in_code_block
        match = None if in_code_block else _MARKDOWN_HEADING.match(line)
        if match:
            sections.heading(len(match.group(1)), match.group(2).strip())
        else:
            sections.line(line)
    sections.flush()
    return sections.documents


def _docx_heading_level(paragraph):
    """1-9 for "Heading N" styles (and 0 for "Title"); None for body text."""
    name = (paragraph.style.name if paragraph.style else "").strip().lower()
    if name == "title":
        return 0
    if name.startswith("heading"):
        digits = re.findall(r"\d+", name)
        return int(digits[0]) if digits else 1
    return None


def _extract_docx(file_path):
    from docx import Document as DocxDocument

    sections = _SectionCollector(file_path)
    for paragraph in DocxDocument(str(file_path)).paragraphs:
        text = paragraph.text.strip()
        if not text:
            continue
        level = _docx_heading_level(paragraph)
        if level is not None:
            sections.heading(level, text)
        else:
            sections.line(text)
    sections.flush()
    return sections.documents


def extract_documents(file_path: Path) -> list[Document]:
    extension = file_path.suffix.lower()
    if extension == ".pdf":
        # One continuous text (with page offsets) so chunks can cross page breaks.
        return join_pages(PyPDFLoader(str(file_path)).load())
    if extension == ".txt":
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return [Document(page_content=text, metadata={"source": str(file_path), "page": None})]
    if extension in {".md", ".markdown"}:
        return _extract_markdown(file_path)
    if extension == ".docx":
        return _extract_docx(file_path)
    raise ValueError(f"Unsupported file format: {extension}. Supported formats: PDF, TXT, DOCX, MD, Markdown")


def configured_chunking(chunk_size=None, overlap=None):
    size = chunk_size if chunk_size is not None else int(os.getenv("RAG_CHUNK_SIZE", str(DEFAULT_CHUNK_SIZE)))
    chunk_overlap = (
        overlap if overlap is not None
        else int(os.getenv("RAG_CHUNK_OVERLAP", str(DEFAULT_CHUNK_OVERLAP)))
    )
    if size <= 0 or chunk_overlap < 0 or chunk_overlap >= size:
        raise ValueError("Chunk size must be positive and overlap must be between 0 and chunk size")
    return size, chunk_overlap


def _validate_document_dates(metadata):
    parsed_dates = {}
    for field in ("effective_date", "expiry_date"):
        value = metadata.get(field)
        if value is None:
            continue
        try:
            normalized = str(value).strip()
            parsed = date.fromisoformat(normalized)
            if parsed.isoformat() != normalized:
                raise ValueError
        except ValueError as exc:
            raise ValueError(f"{field} must use ISO format YYYY-MM-DD") from exc
        metadata[field] = parsed.isoformat()
        parsed_dates[field] = parsed
    effective = parsed_dates.get("effective_date")
    expiry = parsed_dates.get("expiry_date")
    if effective and expiry and expiry < effective:
        raise ValueError("expiry_date must be the same as or later than effective_date")


def ingest_file(file_path, *, metadata=None, chunk_size=None, overlap=None, document_id=None):
    file_path = Path(file_path).expanduser().resolve()
    if not file_path.is_file():
        raise FileNotFoundError(file_path)
    size, chunk_overlap = configured_chunking(chunk_size, overlap)
    file_hash = hashlib.sha256(file_path.read_bytes()).hexdigest()
    document_metadata = dict(metadata or {})
    _validate_document_dates(document_metadata)
    document_metadata.setdefault("title", file_path.stem)
    document_metadata["file_type"] = file_path.suffix.lower().lstrip(".")
    active_document_id = start_document_ingestion(
        filename=file_path.name,
        file_hash=file_hash,
        source_path=str(file_path),
        metadata=document_metadata,
        document_id=document_id,
    )

    try:
        with observation_span(
            "rag.ingestion.extraction",
            input_value={"filename": file_path.name, "extension": file_path.suffix.lower()},
        ) as span:
            pages = extract_documents(file_path)
            set_span_output(span, {"page_count": len(pages)})
        if not pages or not any(page.page_content.strip() for page in pages):
            raise ValueError("Document contains no readable text")

        with observation_span(
            "rag.ingestion.chunking",
            input_value={"page_count": len(pages), "chunk_size": size, "overlap": chunk_overlap},
        ) as span:
            chunks = chunk_documents(pages, chunk_size=size, overlap=chunk_overlap)
            set_span_output(span, {"chunk_count": len(chunks)})

        contents = [chunk.page_content for chunk in chunks]
        chunk_metadata = [
            {**chunk.metadata, **document_metadata, "filename": file_path.name}
            for chunk in chunks
        ]
        with observation_span(
            "rag.ingestion.embeddings",
            input_value={"chunk_count": len(contents), "model": "all-MiniLM-L6-v2"},
            as_type="embedding",
        ) as span:
            embeddings = generate_embeddings(contents)
            dimensions = int(embeddings.shape[-1]) if len(embeddings) else 0
            set_span_output(span, {"embedding_count": len(embeddings), "dimensions": dimensions})

        with observation_span(
            "rag.ingestion.database_store",
            input_value={"filename": file_path.name, "chunk_count": len(contents)},
        ) as span:
            complete_document_ingestion(
                active_document_id,
                contents,
                embeddings,
                chunk_metadata,
                filename=file_path.name,
                file_hash=file_hash,
                source_path=str(file_path),
                metadata=document_metadata,
            )
            set_span_output(span, {"document_id": str(active_document_id), "stored_chunks": len(contents)})
        return active_document_id
    except Exception as exc:
        try:
            fail_document_ingestion(active_document_id, str(exc))
        except Exception:
            pass
        raise


def reindex_document(document_id, *, chunk_size=None, overlap=None):
    record = get_document(document_id)
    if record is None:
        raise ValueError(f"Document not found: {document_id}")
    source_path = record.get("source_path")
    if not source_path or not Path(source_path).is_file():
        raise FileNotFoundError(f"Original source file is unavailable: {source_path or record['filename']}")
    metadata = {k: v for k, v in record["metadata"].items() if k != "file_type"}
    return ingest_file(
        source_path,
        metadata=metadata,
        chunk_size=chunk_size,
        overlap=overlap,
        document_id=document_id,
    )
