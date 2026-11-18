
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

    # pgvector's type adapter can only register after the extension exists.
    # Bootstrap it with a plain connection before using get_connection(), which
    # registers vector types on every normal application connection.
    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")

    statements = [
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
        CREATE TABLE IF NOT EXISTS app_users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS conversation_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
            title TEXT NOT NULL DEFAULT 'New chat',
            status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,

        """
        CREATE TABLE IF NOT EXISTS conversation_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
            content TEXT NOT NULL,
            citations JSONB NOT NULL DEFAULT '[]',
            abstained BOOLEAN NOT NULL DEFAULT FALSE,
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """,

        """
        CREATE INDEX IF NOT EXISTS conversation_sessions_owner_activity_idx
        ON conversation_sessions (user_id, updated_at DESC)
        """,

        """
        CREATE UNIQUE INDEX IF NOT EXISTS conversation_sessions_one_active_per_user_idx
        ON conversation_sessions (user_id) WHERE status='active'
        """,

        """
        CREATE INDEX IF NOT EXISTS conversation_messages_session_time_idx
        ON conversation_messages (session_id, created_at, id)
        """,

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

    # Schema creation itself does not need vector adaptation. Keep this plain
    # connection so initialization never tries to register a type before the
    # database has made the extension visible on the connection search path.
    with psycopg.connect(DATABASE_URL) as conn:
        for statement in statements:
            conn.execute(statement)

    print("Database initialized successfully!")
