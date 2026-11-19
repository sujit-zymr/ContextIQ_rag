# ContextIQ Server (RAG backend)

FastAPI + PostgreSQL/pgvector retrieval-augmented generation backend for
ContextIQ. This directory is the `server/` package of the ContextIQ monorepo
(see the [root README](../README.md)).

> **Working directory**: unless stated otherwise, run every command below from
> this `server/` directory. The `app` package, `storage/uploads/` (the default
> `UPLOAD_DIR`) and `evaluation_data/` are resolved relative to it.

## Quick start

```bash
cd server

# 1. Python environment (Python 3.12)
python3.12 -m venv .venv && source .venv/bin/activate
#    (an existing checkout may instead use the repository-root venv:
#     source ../venv/bin/activate)
python -m pip install -r requirements.txt

# 2. Configuration
cp .env.example .env
#    Set JWT_SECRET_KEY (openssl rand -hex 32), NVIDIA_API_KEY and,
#    optionally, Langfuse keys. Never commit .env.

# 3. Database: PostgreSQL 16 + pgvector on localhost:5433
../scripts/compose.sh up -d postgres
python -m app.main init-db

# 4. Run the API (also applies the schema on startup)
uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
#    Swagger UI: http://localhost:8000/docs   Health: http://localhost:8000/healthz

# 5. Tests
python -m pytest -q
```

### Layout

```text
server/
├── app/                 # Python package: api, ingestion, retrieval, generation,
│                        # conversations, database, evaluation, observability
│   └── evaluation_data/ # Tracked source evaluation questions
├── evaluation_data/     # Generated Ragas datasets and results (git-ignored)
├── storage/uploads/     # Uploaded source documents (git-ignored)
├── tests/
├── Dockerfile           # Backend image (build context: server/)
├── requirements.txt
└── .env.example
```

### CLI reference

`python -m app.main <command>`: `init-db`, `ingest`, `reindex`, `delete`,
`search`, `answer`, `evaluate`, and `collect-evaluation-data`. Run
`python -m app.main --help` for all options.

## Langfuse observability and Ragas evaluation

The RAG CLI sends traces to Langfuse when `LANGFUSE_ENABLED=true` (default) and
Langfuse project keys are configured. It traces document extraction, chunking,
embeddings, database storage, query embedding, vector retrieval, and answer
generation. LangChain callbacks record model generations, latency, errors, and
provider token usage when NVIDIA returns usage data.

## Ingest, reindex, and delete documents

Ingestion accepts PDF, TXT, DOCX, Markdown (`.md`), and `.markdown` files.
Markdown headings and DOCX heading paragraphs are retained as section metadata.
Set `RAG_CHUNK_SIZE` and `RAG_CHUNK_OVERLAP` in `.env` to configure defaults,
or pass `--chunk-size` and `--chunk-overlap` to `ingest` or `reindex`:

```bash
python -m app.main ingest handbook.docx --title "Staff handbook" \
  --department People --version 2026.1 \
  --effective-date 2026-07-01 --expiry-date 2027-06-30 \
  --permission employees \
  --chunk-size 500 --chunk-overlap 80
python -m app.main reindex <document-uuid> --chunk-size 600 --chunk-overlap 100
python -m app.main delete <document-uuid>
```

Document rows track `queued`, `processing`, `completed`, or `failed` status,
with a failure message and update timestamp. Ingestion runs synchronously in
the CLI, so `queued` is the initial database state rather than a background
job queue. Department, version, title, and permission labels are stored as
document and chunk metadata; permission labels are not access-control enforcement. Reindex
uses the original file path saved at ingestion time, so that file must remain
available at the same path. Reindexing swaps chunks and document metadata in a
single database transaction after extraction and embedding finish, preserving
the prior index if processing fails.

PostgreSQL full-text search is also available with the English configuration
and a GIN index. `init-db` adds the generated search vector to existing
databases. Compare the standalone retrieval methods with:

```bash
python -m app.main search "attendance requirement" --search-mode vector
python -m app.main search "attendance requirement" --search-mode full-text
python -m app.main answer "attendance requirement" --search-mode full-text
```

Hybrid retrieval combines both ranked result sets with Reciprocal Rank Fusion
(RRF); the CLI defaults to hybrid. Use `--search-mode vector` or
`--search-mode full-text` to compare either method independently. Hybrid search
fetches three times `top_k` candidates from each method, fuses ranks, reranks
the fused candidates with `cross-encoder/ms-marco-MiniLM-L-6-v2`, then returns
the requested `top_k` results. The first hybrid query may download the model.
Set `RAG_RERANKER_MODEL` to use another Sentence Transformers CrossEncoder.
If loading or scoring fails, retrieval logs the error and returns the RRF
ranking with `reranked: false` in the result metadata.

Answer generation checks the best retrieval score before calling NVIDIA. It
returns an explicit insufficient-evidence response when the threshold is not
met. Tune these starter thresholds in `.env` against the evaluation dataset:

```env
RAG_MIN_VECTOR_SIMILARITY=0.35
RAG_MIN_FULL_TEXT_SCORE=0.02
RAG_MIN_RERANK_SCORE=0.0
RAG_MIN_RRF_SCORE=0.032
```

The applicable threshold and best score are recorded in the `rag.evidence_gate`
Langfuse observation. Search-only requests still show the retrieved results;
the evidence gate controls answer generation.

For supported answers, generation requests JSON containing an answer and inline
source IDs such as `[S1]`. The application validates those IDs against the
retrieved chunks and returns a structured result with the answer, abstention
state, and canonical citation fields (document ID, filename, page, chunk,
section, and version). Invalid, missing, or unverified citations cause an
explicit abstention. The CLI prints the answer and its validated citations;
evaluation data collection keeps the answer text and citations in separate
fields.

Ingestion accepts `--effective-date` and `--expiry-date` in `YYYY-MM-DD` format.
Retrieved citations are marked `current`, `outdated`, `future`, `superseded`,
or `undated`. For documents that belong to the same policy or manual, ingest
each revision with the same `--title` and a distinct `--version` so retrieval
can identify competing revisions. Effective dates take precedence over numeric
version ordering; expired and future sources are identified explicitly in the
prompt and citations.

Ragas evaluation runs five metrics: faithfulness, answer relevancy, context
precision, context recall, and answer correctness. It also reports Recall@5,
MRR, nDCG@5, citation correctness, abstention quality, and ACL leakage when
the dataset contains the required labels. It writes a CSV with per-question scores and a
JSON summary under `evaluation_data/ragas_results/`, then sends each score to
Langfuse as `ragas_<metric>` attached to that sample's trace. If the dataset row
contains `langfuse_trace_id` (or `trace_id`), its scores attach to that trace.
Otherwise, evaluation creates a Langfuse trace for the question, retrieved
contexts, answer, reference, and scores.

### Install and configure

Activate the virtual environment and install the project dependencies (from `server/`):

```bash
source .venv/bin/activate   # or: source ../venv/bin/activate
python -m pip install -r requirements.txt
```

Create a project in Langfuse Cloud (or use your own Langfuse v4.59+ deployment
for the current Python SDK) and copy its project keys into `server/.env`:

```env
LANGFUSE_ENABLED=true
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_TRACING_ENVIRONMENT=development

# The same NVIDIA key/model used by answer generation is used as the Ragas judge.
NVIDIA_API_KEY=...
NVIDIA_MODEL=nvidia/nemotron-3-nano-omni-30b-a3b-reasoning
```

Use the base URL for your Langfuse region or self-hosted deployment. Keep `.env`
private and never commit it.

### Run the RAG pipeline and verify the connection

Start PostgreSQL and ingest at least one source document using the project's
existing setup. Then run an answer request:

```bash
python -m app.main answer "What is the college's attendance requirement?"
```

Open the matching Langfuse project and look for the `rag.answer_request` trace
and its child retrieval and generation observations. This verifies that the
credentials and Langfuse endpoint work from the application environment.

Run Ragas against the prepared JSON dataset:

```bash
python -m app.main evaluate --dataset evaluation_data/ragas_dataset.json
```

Capture the current implementation as a reproducible baseline before tuning.
The baseline file is immutable; choose another output directory to save a
different baseline. Use `--enforce-quality-gate` to return a nonzero status
after a report is saved if the dataset or thresholds do not pass:

```bash
python -m app.main evaluate --dataset evaluation_data/ragas_dataset.json --save-baseline
python -m app.main evaluate --dataset evaluation_data/ragas_dataset.json --enforce-quality-gate
```

The summary records dataset SHA-256, Git commit, sample/category counts, metric
coverage, per-category averages, configured thresholds, and gate results.
Set `RAG_EVAL_MIN_RECALL_AT_5`, `RAG_EVAL_MIN_MRR`,
`RAG_EVAL_MIN_NDCG_AT_5`, `RAG_EVAL_MIN_FAITHFULNESS`,
`RAG_EVAL_MIN_ANSWER_CORRECTNESS`, `RAG_EVAL_MIN_ABSTENTION_QUALITY`, and
`RAG_EVAL_MAX_ACL_LEAKAGE` to tune the initial gate thresholds.

The output reports the result file paths and how many samples were linked to
Langfuse traces. Each score appears on its corresponding trace in Langfuse.
Override the result directory with `--output-dir` if needed.

### Evaluation requirements and data handling

- The evaluation JSON must be a non-empty array. Each row needs `user_input`,
  `retrieved_contexts` (a list of strings), and `response`. `reference` is
  needed for context precision and context recall. The existing dataset's
  `question`, `contexts`, `answer`, and `expected_answer` aliases are accepted.
- Ragas uses `NVIDIA_API_KEY` and `NVIDIA_MODEL` for judge calls. Those calls
  send the question, answer, reference, and retrieved contexts to NVIDIA.
- Answer relevancy reuses the local `all-MiniLM-L6-v2` embedding model. The
  model may be downloaded the first time it is needed.
- Langfuse export redacts common API-key patterns, labeled credentials, and
  email addresses before sending span attributes. Prompt, answer, question, and
  document content are replaced with `[CONTENT REDACTED]` by default. Set
  `LANGFUSE_CAPTURE_CONTENT=true` only when the project data policy permits
  sending content to Langfuse. Pattern-based PII redaction cannot guarantee
  removal of every sensitive value.
- Tracing and score export fail open: Langfuse errors are logged and do not
  prevent RAG or evaluation results from being produced. Set
  `LANGFUSE_ENABLED=false` to disable tracing and score publishing.

## Backend conversation sessions

The API lives under `app/api/` in the `server/` package. It stores users,
sessions, and message history in PostgreSQL. Creating a new session archives
the user's prior active session without deleting it; activating an older
session resumes it and archives the current one.

Install the added backend dependencies, set a JWT signing secret, and start the
API (startup applies the database schema):

```bash
python -m pip install -r requirements.txt
openssl rand -hex 32  # put the output in JWT_SECRET_KEY in .env
../scripts/compose.sh up -d postgres
uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
```

The API supports `POST /auth/register`, `POST /auth/token`, and `GET /auth/me`.
Login uses OAuth2 form fields, with the email supplied as `username`. Send the
returned bearer token to the session endpoints:

```text
POST /sessions
GET  /sessions
POST /sessions/{session_id}/activate
GET  /sessions/{session_id}/messages
POST /sessions/{session_id}/messages
```

Session ownership comes from the signed access token; the API checks ownership
for each session and message request. Follow-up questions are resolved from
the latest 12 stored messages. If context leaves multiple materially different
interpretations, the API saves and returns a clarification question without
running retrieval. Otherwise, it rewrites the question for retrieval, then
saves the structured answer, validated citations, and abstention state.
Interactive API documentation is available at `/docs` while the server runs.

## Container deployment with Docker Compose

Run the entire application (API and PostgreSQL with pgvector) via Docker Compose.
The Compose file lives in `infrastructure/docker/`; `scripts/compose.sh` runs it
with `server/.env` (see [infrastructure/README.md](../infrastructure/README.md)):

```bash
cp .env.example .env
# Set JWT_SECRET_KEY, NVIDIA_API_KEY, and optional Langfuse keys in .env
../scripts/compose.sh up --build -d
```

The API service automatically waits for PostgreSQL health checks to pass before starting.
Check health at `http://localhost:8000/healthz` and view Swagger UI at `http://localhost:8000/docs`.

## Automated CI Workflow

ContextIQ includes a GitHub Actions continuous integration workflow (`.github/workflows/ci.yml`) that runs on every push and pull request:
- Provisions PostgreSQL with the pgvector extension and health checks.
- Installs Python 3.12 dependencies.
- Runs syntax and static compilation checks.
- Executes automated test suites.
- Validates the Docker Compose configuration and builds the backend image.

All Python steps run with `server/` as the working directory.

## Troubleshooting

- **Database connection error**: Verify PostgreSQL is running (`../scripts/compose.sh ps`) and that `DATABASE_URL` matches your host port (5433 for local host, 5432 inside Docker network).
- **Missing vector extension**: Ensure your database is initialized with `python -m app.main init-db` and running the `pgvector/pgvector:pg16` image.
- **NVIDIA API errors**: Ensure `NVIDIA_API_KEY` is exported and valid. Rate limits or model downtime fall back to explicit error logging without application crashes.
- **Langfuse connection issues**: Observability is fail-open; tracing errors are logged as warnings and do not interrupt core RAG operations. Set `LANGFUSE_ENABLED=false` to silence telemetry.

