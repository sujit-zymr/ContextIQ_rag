
import hashlib
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

from app.ingestion.chunker import chunk_documents
from app.ingestion.embedder import generate_embeddings

from app.database.chunk_repository import (
    save_document,
    document_exists
)


def extract_documents(file_path: Path) -> list[Document]:

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        loader = PyPDFLoader(str(file_path))
        return loader.load()

    elif extension == ".txt":
        text = file_path.read_text(
            encoding="utf-8",
            errors="replace"
        )

        return [
            Document(
                page_content=text,
                metadata={
                    "source": str(file_path),
                    "page": None
                }
            )
        ]

    else:
        raise ValueError(
            f"Unsupported file format: {extension}"
        )


def ingest_file(file_path):

    file_path = Path(file_path)

    if not file_path.is_file():
        raise FileNotFoundError(file_path)

    # Step 1: Generate file hash
    file_bytes = file_path.read_bytes()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    # Step 2: Check duplicate
    if document_exists(file_hash):
        print("Document already exists. Skipping ingestion.")
        return None

    # Step 3: Extract documents
    pages = extract_documents(file_path)

    if not pages or not any(
        page.page_content.strip() for page in pages
    ):
        raise ValueError("Document contains no readable text")

    # Step 4: Chunk documents
    chunks = chunk_documents(
        pages,
        chunk_size=200,
        overlap=40
    )

    print(f"Generated {len(chunks)} chunks")

    # Step 5: Extract text for embeddings
    contents = [
        chunk.page_content for chunk in chunks
    ]

    # Step 6: Extract metadata
    chunk_metadata = [
        {
            **chunk.metadata,
            "filename": file_path.name
        }
        for chunk in chunks
    ]

    # Step 7: Generate embeddings
    embeddings = generate_embeddings(contents)

    print("Embeddings generated successfully")

    # Step 8: Store in PostgreSQL
    document_id = save_document(
        filename=file_path.name,
        file_hash=file_hash,
        chunks=contents,
        embeddings=embeddings,
        chunk_metadata=chunk_metadata
    )

    print("Document stored successfully")

    return document_id
