# ContextIQ RAG — Complete Backend Specification & Frontend Integration Guide

This document is a comprehensive, standalone specification of the **ContextIQ RAG Backend**. It is written for frontend engineers and AI assistants building the ContextIQ client interface. 

---

## 1. System Overview & Architecture

ContextIQ is an enterprise Retrieval-Augmented Generation (RAG) platform. It provides document ingestion, hybrid vector/full-text search, cross-encoder reranking, evidence gating, strict citation verification, conversation contextualization, and authenticated REST APIs.

### Technology Stack
* **Language & Framework**: Python 3.12, FastAPI, Pydantic v2, Uvicorn
* **Database**: PostgreSQL 16 with `pgvector` extension (dense vectors) + `tsvector` (full-text search)
* **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional dense vectors)
* **Reranker Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
* **Generation LLM**: NVIDIA API (`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`) via `langchain-openai`
* **Auth**: OAuth2 Password Bearer flow, HS256 JWT tokens, Argon2 password hashing via `pwdlib`
* **Observability**: Langfuse v5 with automatic span sanitization and PII redaction

---

## 2. Database Schema & Data Models

### 2.1 Database Tables (PostgreSQL 16)

```sql
-- Users
CREATE TABLE app_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Conversation Sessions
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES app_users(id) ON DELETE CASCADE,
    title TEXT NOT NULL DEFAULT 'New chat',
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Conversation Messages
CREATE TABLE conversation_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES conversation_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    citations JSONB NOT NULL DEFAULT '[]',
    abstained BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Documents (Ingested files)
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,                -- SHA-256 hash of original file
    metadata JSONB DEFAULT '{}',            -- title, department, version, dates, etc.
    source_path TEXT,                       -- Absolute path on disk (API uploads go to server/storage/uploads/)
    status TEXT NOT NULL DEFAULT 'completed', -- 'queued' | 'processing' | 'completed' | 'failed'
    status_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Document Chunks (Vector + FTS search vectors)
CREATE TABLE document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(384),                  -- pgvector HNSW index
    search_vector TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED, -- GIN index
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);
```

---

## 3. Authentication & Security

### 3.1 Mechanism
* **Standard**: HTTP `Authorization: Bearer <access_token>`
* **Algorithm**: `HS256` signed JWT
* **TTL**: 30 minutes (`1800` seconds)
* **Password Policy**: Minimum 12 characters, hashed with Argon2

### 3.2 CORS Configuration
The backend includes `CORSMiddleware` in `app/api/main.py`.
* **Allowed Origins by Default**:
  * `http://localhost:3000` (Next.js default)
  * `http://localhost:5173` (Vite default)
  * `http://localhost:8080`, `http://localhost:8501`
  * `http://127.0.0.1:*` (same ports)
* **Custom Origins**: Set via environment variable `CORS_ALLOWED_ORIGINS=http://example.com,http://app.com`
* **Allowed Methods**: `["*"]`
* **Allowed Headers**: `["*"]`
* **Credentials**: Supported (`allow_credentials=True`)

---

## 4. Complete REST API Reference

Base URL (local dev): `http://localhost:8000`

### 4.1 System & Health

#### `GET /healthz`
* **Auth**: Public (No auth required)
* **Response `200 OK`**:
```json
{
  "status": "ok"
}
```

---

### 4.2 Authentication Endpoints

#### `POST /auth/register`
Create a new user account.
* **Auth**: Public
* **Request Header**: `Content-Type: application/json`
* **Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```
* **Validation**: Email must be valid format; password must be 12–128 characters.
* **Response `201 Created`**:
```json
{
  "id": "11111111-2222-3333-4444-555555555555",
  "email": "user@example.com",
  "created_at": "2026-11-19T10:00:00Z"
}
```
* **Error Responses**:
  * `409 Conflict`: `{"detail": "An account with this email already exists."}`
  * `422 Unprocessable Content`: Invalid email or password length.

#### `POST /auth/token`
Login to obtain a JWT Bearer token (Standard OAuth2 password flow).
* **Auth**: Public
* **Request Header**: `Content-Type: application/x-www-form-urlencoded`
* **Request Body** (Form URL-encoded):
```
username=user@example.com&password=SecurePassword123!
```
*(Note: Use `username` field for the user's email).*
* **Response `200 OK`**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
  "token_type": "bearer",
  "expires_in": 1800
}
```
* **Error Responses**:
  * `401 Unauthorized`: `{"detail": "Incorrect email or password."}`

#### `GET /auth/me`
Get the current authenticated user's profile.
* **Auth**: Bearer Token required
* **Request Header**: `Authorization: Bearer <access_token>`
* **Response `200 OK`**:
```json
{
  "id": "11111111-2222-3333-4444-555555555555",
  "email": "user@example.com",
  "created_at": "2026-11-19T10:00:00Z"
}
```
* **Error Responses**:
  * `401 Unauthorized`: `{"detail": "Invalid or expired access token."}`

---

### 4.3 Conversation Sessions Endpoints

#### `GET /sessions`
List all conversation sessions belonging to the authenticated user, ordered by most recently active.
* **Auth**: Bearer Token required
* **Response `200 OK`**:
```json
[
  {
    "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "user_id": "11111111-2222-3333-4444-555555555555",
    "title": "HR Attendance Policy",
    "status": "active",
    "created_at": "2026-11-19T09:30:00Z",
    "updated_at": "2026-11-19T10:15:00Z",
    "message_count": 6
  }
]
```

#### `POST /sessions`
Create a new conversation session.
* **Auth**: Bearer Token required
* **Validation**: `title` is optional (default `"New chat"`), 1–80 characters.
* **Request Body**:
```json
{
  "title": "New chat"
}
```
* **Response `201 Created`**:
```json
{
  "id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "user_id": "11111111-2222-3333-4444-555555555555",
  "title": "New chat",
  "status": "active",
  "created_at": "2026-11-19T10:15:00Z",
  "updated_at": "2026-11-19T10:15:00Z",
  "message_count": 0
}
```

#### `POST /sessions/{session_id}/activate`
Mark a session as active for the user (only one session is active at a time).
* **Auth**: Bearer Token required
* **Side effect**: Every other `active` session of the user is set to `status: "archived"`. Archived sessions are still fully readable and can be re-activated, and `POST /sessions/{id}/messages` also activates its session automatically. In practice `status` only marks the most recently used session; it does **not** mean the user archived it.
* **Response `200 OK`**: `SessionResponse` object.
* **Error Responses**: `404 Not Found` (`{"detail": "Conversation session not found."}`) if session doesn't exist or belongs to another user.

#### `GET /sessions/{session_id}/messages`
Retrieve message history for a session, ordered chronologically.
* **Auth**: Bearer Token required
* **Query Parameters**:
  * `limit` (optional, default: `100`, min: `1`, max: `500`): Maximum messages to return.
* **Response `200 OK`**:
```json
[
  {
    "id": "m1111111-0000-0000-0000-000000000001",
    "session_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "role": "user",
    "content": "What is the attendance policy?",
    "citations": [],
    "abstained": false,
    "metadata": {
      "message_type": "question"
    },
    "created_at": "2026-11-19T10:15:05Z"
  },
  {
    "id": "m1111111-0000-0000-0000-000000000002",
    "session_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "role": "assistant",
    "content": "Employees are required to maintain at least 95% working hour compliance [S1]. Planned leaves must be logged 48 hours in advance [S2].",
    "citations": [
      {
        "source_id": "S1",
        "document_id": "d0000000-aaaa-bbbb-cccc-111111111111",
        "title": "Company Attendance & Leave Guidelines",
        "filename": "attendance_policy_2026.pdf",
        "page": 3,
        "chunk_index": 2,
        "section": "Working Hours and Punctuality",
        "version": "2.1",
        "effective_date": "2026-01-01",
        "expiry_date": null,
        "as_of_date": "2026-11-19",
        "source_freshness": "current",
        "has_competing_versions": false,
        "competing_versions": []
      },
      {
        "source_id": "S2",
        "document_id": "d0000000-aaaa-bbbb-cccc-111111111111",
        "title": "Company Attendance & Leave Guidelines",
        "filename": "attendance_policy_2026.pdf",
        "page": 4,
        "chunk_index": 4,
        "section": "Leave Request Procedure",
        "version": "2.1",
        "effective_date": "2026-01-01",
        "expiry_date": null,
        "as_of_date": "2026-11-19",
        "source_freshness": "current",
        "has_competing_versions": false,
        "competing_versions": []
      }
    ],
    "abstained": false,
    "metadata": {
      "retrieval_query": "attendance policy working hours leave guidelines",
      "needs_clarification": false,
      "answer_reason": null
    },
    "created_at": "2026-11-19T10:15:10Z"
  }
]
```

#### `POST /sessions/{session_id}/messages`
Send a question to the assistant inside a session.
* **Auth**: Bearer Token required
* **Request Header**: `Content-Type: application/json`
* **Request Body**:
```json
{
  "content": "What happens if someone fails to report leave?",
  "top_k": 5
}
```
*(Parameters: `content` [1-8000 chars], `top_k` [default 5, min 1, max 20] — the number of context **passages**: each is a retrieved chunk plus its neighbouring chunks, with nearby hits merged. Each passage is one citation; `chunk_index` and `page` refer to its best-matching chunk).*

* **Citation object fields**: `source_id`, `document_id`, `title`, `filename`, `page` (PDF only, else `null`), `chunk_index`, `section`, `version`, `effective_date`, `expiry_date`, `as_of_date` (the date freshness was evaluated against, i.e. the request date), `source_freshness`, `has_competing_versions`, `competing_versions`.
* **`source_freshness` values**: `current`, `outdated` (past `expiry_date`), `superseded` (a newer version of the same document exists), `future` (`effective_date` is after today), `undated` (no effective/expiry date in metadata).
* **Citation markers**: every cited source appears as an `[S1]`-style marker in `content`. If the model lists sources without placing markers inline, the backend appends them to the end of the answer.

* **Response `200 OK` (Standard Answer)**:
```json
{
  "session_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
  "user_message": {
    "id": "m1111111-...",
    "session_id": "a1b2c3d4-...",
    "role": "user",
    "content": "What happens if someone fails to report leave?",
    "citations": [],
    "abstained": false,
    "metadata": { "message_type": "question" },
    "created_at": "2026-11-19T10:16:00Z"
  },
  "assistant_message": {
    "id": "m2222222-...",
    "session_id": "a1b2c3d4-...",
    "role": "assistant",
    "content": "Unreported absences exceeding three consecutive working days are treated as unauthorized leave and may lead to disciplinary review [S1].",
    "citations": [
      {
        "source_id": "S1",
        "document_id": "d0000000-aaaa-bbbb-cccc-111111111111",
        "title": "Company Attendance & Leave Guidelines",
        "filename": "attendance_policy_2026.pdf",
        "page": 5,
        "chunk_index": 7,
        "section": "Unauthorized Absence",
        "version": "2.1",
        "effective_date": "2026-01-01",
        "expiry_date": null,
        "as_of_date": "2026-11-19",
        "source_freshness": "current",
        "has_competing_versions": false,
        "competing_versions": []
      }
    ],
    "abstained": false,
    "metadata": {
      "retrieval_query": "consequences unreported leave unexcused absence policy",
      "needs_clarification": false,
      "answer_reason": null
    },
    "created_at": "2026-11-19T10:16:04Z"
  },
  "retrieval_query": "consequences unreported leave unexcused absence policy",
  "needs_clarification": false
}
```

* **Response `200 OK` (Clarification Case)**:
When the user's question is too vague or refers to ambiguous pronouns ("How do I apply for it?"):
```json
{
  "session_id": "a1b2c3d4-...",
  "user_message": { ... },
  "assistant_message": {
    "id": "m3333333-...",
    "session_id": "a1b2c3d4-...",
    "role": "assistant",
    "content": "Could you clarify whether you are asking about applying for medical leave, casual leave, or remote work permissions?",
    "citations": [],
    "abstained": false,
    "metadata": { "needs_clarification": true },
    "created_at": "2026-11-19T10:17:02Z"
  },
  "retrieval_query": null,
  "needs_clarification": true
}
```
> **Important**: The top-level `needs_clarification` field exists only in this send-message response. When history is reloaded via `GET /sessions/{id}/messages`, the flag is available only as `assistant_message.metadata.needs_clarification`. Clients should always read it from `metadata` so live and reloaded messages render the same way.

* **Response `200 OK` (Abstention Case / Insufficient Evidence)**:
When the retrieved documents do not contain enough information to safely answer:
```json
{
  "session_id": "a1b2c3d4-...",
  "user_message": { ... },
  "assistant_message": {
    "id": "m4444444-...",
    "role": "assistant",
    "content": "I don't have enough evidence in the retrieved documents to answer that question.",
    "citations": [],
    "abstained": true,
    "metadata": {
      "retrieval_query": "travel reimbursement per diem rates",
      "needs_clarification": false,
      "answer_reason": "No chunk scored above evidence threshold."
    },
    "created_at": "2026-11-19T10:18:00Z"
  },
  "retrieval_query": "travel reimbursement per diem rates",
  "needs_clarification": false
}
```

---

### 4.4 Document Management Endpoints

> **Scope**: Documents form a single **shared knowledge base** and are **not owned by users**. Every authenticated user can list, upload and delete any document, and all chat queries search all documents. There is no per-user document isolation or role-based permission in this release.

#### `GET /documents`
List indexed documents with pagination and optional status filter.
* **Auth**: Bearer Token required
* **Query Parameters**:
  * `status` (optional): Filter by `'completed'`, `'processing'`, `'failed'`.
  * `limit` (optional, default: `50`, min: `1`, max: `200`): Page size.
  * `offset` (optional, default: `0`, min: `0`): Pagination offset.
* **Response `200 OK`**:
```json
{
  "total": 3,
  "limit": 50,
  "offset": 0,
  "items": [
    {
      "id": "d0000000-aaaa-bbbb-cccc-111111111111",
      "filename": "attendance_policy_2026.pdf",
      "status": "completed",
      "status_message": null,
      "metadata": {
        "title": "Company Attendance & Leave Guidelines",
        "file_type": "pdf"
      },
      "created_at": "2026-11-18T10:00:00Z",
      "updated_at": "2026-11-18T10:02:15Z",
      "chunk_count": 14
    }
  ]
}
```

#### `GET /documents/{document_id}`
Retrieve detailed information for a single document.
* **Auth**: Bearer Token required
* **Response `200 OK`**:
```json
{
  "id": "d0000000-aaaa-bbbb-cccc-111111111111",
  "filename": "attendance_policy_2026.pdf",
  "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "source_path": "/storage/uploads/attendance_policy_2026.pdf",
  "status": "completed",
  "status_message": null,
  "metadata": {
    "title": "Company Attendance & Leave Guidelines",
    "file_type": "pdf",
    "effective_date": "2026-01-01"
  },
  "created_at": "2026-11-18T10:00:00Z",
  "updated_at": "2026-11-18T10:02:15Z",
  "chunk_count": 14,
  "total_chars": 8420
}
```
* **Error Responses**: `404 Not Found` if document ID does not exist.

#### `POST /documents/upload`
Upload a document file to be parsed, chunked, embedded, and indexed.
* **Auth**: Bearer Token required
* **Request Header**: `Content-Type: multipart/form-data`
* **Form Body**: `file` (Binary file)
* **Supported Extensions**: `.pdf`, `.docx`, `.txt`, `.md`, `.markdown`
* **Response `201 Created`**:
```json
{
  "document_id": "d0000000-aaaa-bbbb-cccc-111111111111",
  "filename": "attendance_policy_2026.pdf",
  "status": "completed",
  "chunk_count": 14,
  "message": "Document 'attendance_policy_2026.pdf' ingested successfully with 14 chunks."
}
```
* **Error Responses**:
  * `422 Unprocessable Content`: Empty file, or unsupported file extension.
  * `500 Internal Server Error`: Ingestion failure (e.g. corrupted PDF with no readable text).

#### `DELETE /documents/{document_id}`
Remove a document and all its chunks/embeddings from the database.
* **Auth**: Bearer Token required
* **Response `200 OK`**:
```json
{
  "document_id": "d0000000-aaaa-bbbb-cccc-111111111111",
  "deleted": true,
  "message": "Document 'attendance_policy_2026.pdf' and all its chunks have been removed."
}
```
* **Error Responses**: `404 Not Found` if document does not exist.

---

## 5. RAG Pipeline Mechanics (How Backend Generates Answers)

Understanding this pipeline helps the frontend build a superior UX:

```
User Query: "What is the notice period?"
           │
           ▼
[ Conversation Contextualizer ]
   * Checks prior 12 messages in session.
   * If ambiguous: Returns needs_clarification=True (stops early, no retrieval).
   * If clear: Generates standalone retrieval query: "employee resignation notice period requirements".
           │
           ▼
[ Query Preprocessor ]
   * Corrects typos against corpus dictionary (e.g. "attendence" -> "attendance").
           │
           ▼
[ Hybrid Retrieval ]
   * Dense Vector Search: pgvector <=> cosine distance (top candidates).
   * Full-Text Search: PostgreSQL websearch_to_tsquery('english', ...) with terms joined by OR, ranked by ts_rank_cd.
   * Reciprocal Rank Fusion (RRF): Combines ranks with constant k=60.
           │
           ▼
[ Cross-Encoder Reranker ]
   * Models candidate relevance using cross-encoder/ms-marco-MiniLM-L-6-v2.
   * Assigns calibrated relevance logit score.
           │
           ▼
[ Context Passages ]
   * Top hits + RAG_CONTEXT_WINDOW neighbouring chunks (default 1 each side).
   * Nearby hits merged; top_k passages returned (one citation each).
           │
           ▼
[ Evidence Gate (Abstention Threshold) ]
   * Evaluates top chunk score against RAG_MIN_RERANK_SCORE (threshold: -6.0).
   * If best chunk < threshold: Abstains immediately ("I don't have enough evidence...").
           │
           ▼
[ LLM Generation (NVIDIA Nemotron-3) ]
   * Formats retrieved chunks as sources: [S1], [S2], [S3].
   * System Prompt enforces strict citation markers.
           │
           ▼
[ Citation Verification Engine ]
   * Validates that every [S1] marker references an actual chunk provided.
   * Verifies source freshness (marks as 'current', 'outdated', 'superseded', 'future', or 'undated').
   * Strips hallucinated markers.
           │
           ▼
Returns final answer with validated citations array to client.
```

---

## 6. Frontend Architectural Guidelines

When building the client interface against this backend:

### 6.1 Authentication Lifecycle
1. Maintain an `auth` state (e.g. Zustand `useAuthStore`).
2. Store `access_token` in `localStorage` (or secure cookies).
3. Set up an Axios/fetch interceptor:
   * Attach `Authorization: Bearer <token>` to all `/sessions*` and `/documents*` requests.
   * On `401 Unauthorized`: Clear the token and redirect to `/login`.
4. Provide a Register screen (`POST /auth/register`) and Login screen (`POST /auth/token`).

### 6.2 Chat & Session Flow
1. **New Chat**: When a user opens `/chat` with no active session, show the ContextIQ welcoming screen and suggested prompt cards.
2. **First Question Handling**:
   * Calling `POST /sessions` to create a session (`title` can be derived from the first query e.g. `query.slice(0, 50)`; max 80 chars).
   * Keep the pending question in client state, then post it to `POST /sessions/{session_id}/messages`.
   * Update the URL to `/chat/[session_id]` without full page reload. If the route change triggers a history fetch, the fetch must not overwrite the in-flight optimistic message (see the frontend plan, §7.3).
3. **Subsequent Questions**:
   * Send directly to `POST /sessions/{session_id}/messages`.
4. **No Simulated Streaming**:
   * The backend does not stream tokens. Show an elegant typing / generation skeleton while awaiting the HTTP response.
5. **Handling Clarifications**:
   * If `assistant_message.metadata.needs_clarification === true`, render the assistant message with a distinct visual style (e.g. a blue clarification badge). Use the `metadata` field rather than the top-level response flag so that reloaded history renders the same way.
6. **Handling Abstentions**:
   * If `response.assistant_message.abstained === true`, render a subtle warning/info box indicating that evidence in the knowledge base was insufficient.

### 6.3 Citations & Sources Panel
1. The assistant response text contains markers like `[S1]`, `[S2]`.
2. Convert these markers into **clickable citation badges** (e.g. `<CitationChip id="S1" />`).
3. Clicking a badge opens the **Sources Inspector** (desktop side panel or mobile drawer) and highlights that specific source card.
4. Each source card displays:
   * Title / Document filename
   * Page number (for PDFs) or Section header (for Markdown/DOCX)
   * Version & Date
   * **Freshness Badge**: Color code `source_freshness`:
     * `current` -> Green badge
     * `outdated` -> Yellow/Amber badge
     * `superseded` -> Red badge
     * `future` -> Blue/neutral badge ("Not yet effective")
     * `undated` or `null` -> No badge (or a muted "Undated" label)

### 6.4 Document Management Screen
1. Dedicated `/documents` page. Present it as the shared knowledge base, not "my documents", because deletes affect every user (see §4.4).
2. Drag-and-drop file upload zone accepting `.pdf`, `.docx`, `.txt`, `.md`, `.markdown`.
3. Table listing all documents with:
   * Document Name & File Type icon
   * Status (`completed`, `processing`, `failed`)
   * Chunk count
   * Upload date
   * Delete button (with confirmation modal stating the document is removed for all users)
4. Calls `POST /documents/upload` as multipart form data.
5. Calls `DELETE /documents/{id}` and updates list on success.

---

## 7. Environment & Running the Backend

### Environment Variables (`server/.env`)
```bash
# Database
DATABASE_URL=postgresql://raguser:ragpassword@localhost:5433/ragdb

# Authentication
JWT_SECRET_KEY=<generate-with: python -c "import secrets; print(secrets.token_hex(32))">

# LLM Providers
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-5.4-mini
NVIDIA_API_KEY=nvapi-...
NVIDIA_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning

# Observability
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_TRACING_ENVIRONMENT=development

# Storage & CORS
UPLOAD_DIR=storage/uploads   # relative to server/
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### Commands to Run the Backend
```bash
# 1. Start PostgreSQL with pgvector (via Docker), from the repository root
scripts/compose.sh up -d postgres

# 2. Switch to the backend and activate its virtual environment
cd server
source .venv/bin/activate        # or the repository-root venv: source ../venv/bin/activate

# 3. Start the FastAPI server
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```
API Documentation will be live at:
* Swagger UI: `http://localhost:8000/docs`
* ReDoc: `http://localhost:8000/redoc`
