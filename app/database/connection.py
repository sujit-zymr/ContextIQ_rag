
import os
import psycopg

from dotenv import load_dotenv
from pgvector.psycopg import register_vector

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def get_connection():
    conn = psycopg.connect(DATABASE_URL)
    register_vector(conn)
    return conn


def init_db():

    statements = [
        "CREATE EXTENSION IF NOT EXISTS vector",

        """
        CREATE TABLE IF NOT EXISTS documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            filename TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            source_path TEXT,
            status TEXT NOT NULL DEFAULT 'completed',
            status_message TEXT,
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """,

        # Upgrade databases created by earlier versions of the project.
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS source_path TEXT",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'completed'",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS status_message TEXT",
        "ALTER TABLE documents ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()",

        """
        CREATE TABLE IF NOT EXISTS document_chunks (
            id BIGSERIAL PRIMARY KEY,
            document_id UUID NOT NULL
                REFERENCES documents(id) ON DELETE CASCADE,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding VECTOR(384),
            search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
            metadata JSONB DEFAULT '{}',
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(document_id, chunk_index)
        )
        """,

        # Add the generated full-text vector to existing installations too.
        """ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS search_vector
           TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED""",

        """
        CREATE INDEX IF NOT EXISTS document_chunks_search_vector_idx
        ON document_chunks USING GIN (search_vector)
        """,

        """
        CREATE INDEX IF NOT EXISTS document_chunks_embedding_idx
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        """
    ]

    with get_connection() as conn:
        for statement in statements:
            conn.execute(statement)

    print("Database initialized successfully!")
