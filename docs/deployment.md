# Deployment and Operations Guide

This guide covers running ContextIQ locally, in Docker, and through automated CI.

> **Monorepo paths**: the backend lives in `server/`, the Compose file in
> `infrastructure/docker/docker-compose.yml`. Run Python commands from `server/`
> and Docker Compose through `scripts/compose.sh` (from the repository root),
> which passes `server/.env` to Compose.

---

## 1. Prerequisites

- **Docker & Docker Compose**: Docker Engine 24+ with Compose plugin (v2).
- **Python**: Python 3.12 (if running locally outside Docker).
- **NVIDIA API Key**: Required for contextual follow-up resolution, answer generation, and Ragas judge metrics.
- **Langfuse Account**: (Optional) For distributed tracing and evaluation score tracking.
- **PostgreSQL 16 with pgvector**: Provided automatically via Docker Compose.

---

## 2. Environment Configuration

Copy the example environment file and generate a JWT secret:

```bash
cp server/.env.example server/.env
openssl rand -hex 32
```

Add the generated secret to `JWT_SECRET_KEY` in `server/.env`, along with your `NVIDIA_API_KEY`.

### Complete Environment Variable Reference

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `postgresql://raguser:ragpassword@localhost:5433/ragdb` | PostgreSQL connection string |
| `POSTGRES_USER` | `raguser` | Database user for Docker container |
| `POSTGRES_PASSWORD` | `ragpassword` | Database password for Docker container |
| `POSTGRES_DB` | `ragdb` | Database name |
| `JWT_SECRET_KEY` | *(Required, 32+ chars)* | Signing secret for authentication tokens |
| `NVIDIA_API_KEY` | *(Required for LLM)* | API key for NVIDIA inference |
| `NVIDIA_MODEL` | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` | Model for answers & contextualization |
| `LANGFUSE_ENABLED` | `true` | Enable or disable fail-open tracing |
| `LANGFUSE_CAPTURE_CONTENT` | `false` | Enable prompt/document telemetry (`true` / `false`) |
| `LANGFUSE_PUBLIC_KEY` | *(Optional)* | Langfuse project public key |
| `LANGFUSE_SECRET_KEY` | *(Optional)* | Langfuse project secret key |
| `LANGFUSE_BASE_URL` | `https://cloud.langfuse.com` | Langfuse API host |
| `LANGFUSE_TRACING_ENVIRONMENT` | `development` | Deployment environment label |
| `RAG_CHUNK_SIZE` | `1000` | Target character size for chunking (keep ≤ ~1000 for the 256-token embedding model) |
| `RAG_CHUNK_OVERLAP` | `150` | Overlap characters between chunks |
| `RAG_CONTEXT_WINDOW` | `1` | Neighbouring chunks added on each side of a retrieved hit to form a passage (`0` = hits only) |
| `RAG_RERANKER_MODEL` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | SentenceTransformers CrossEncoder |
| `RAG_MIN_VECTOR_SIMILARITY` | `0.35` | Minimum cosine similarity for vector mode |
| `RAG_MIN_FULL_TEXT_SCORE` | `0.02` | Minimum text rank score for FTS mode |
| `RAG_MIN_RERANK_SCORE` | `0.0` | Minimum cross-encoder score for hybrid mode |
| `RAG_MIN_RRF_SCORE` | `0.032` | Minimum RRF score when reranker is skipped |
| `RAG_EVAL_MIN_RECALL_AT_5` | `0.75` | Quality gate minimum Recall@5 |
| `RAG_EVAL_MIN_PRECISION_AT_5` | `0.50` | Quality gate minimum Precision@5 |
| `RAG_EVAL_MIN_HIT_RATE_AT_5` | `0.80` | Quality gate minimum Hit Rate@5 |
| `RAG_EVAL_MIN_MRR` | `0.50` | Quality gate minimum MRR |
| `RAG_EVAL_MIN_NDCG_AT_5` | `0.60` | Quality gate minimum NDCG@5 |
| `RAG_EVAL_MIN_FAITHFULNESS` | `0.75` | Quality gate minimum Ragas Faithfulness |
| `RAG_EVAL_MIN_ANSWER_CORRECTNESS` | `0.75` | Quality gate minimum Answer Correctness |
| `RAG_EVAL_MIN_ABSTENTION_QUALITY` | `0.90` | Quality gate minimum Abstention Quality |
| `RAG_EVAL_MIN_CITATION_CORRECTNESS` | `0.90` | Quality gate minimum Citation Correctness |
| `RAG_EVAL_MAX_ACL_LEAKAGE` | `0.0` | Quality gate maximum allowed ACL leakage |

---

## 3. Docker Deployment

The application provides a containerized setup with PostgreSQL pgvector and FastAPI:

```bash
# Build and start services in the background (from the repository root)
scripts/compose.sh up --build -d

# Verify container status and health
scripts/compose.sh ps
```

### Startup Architecture
1. **PostgreSQL service (`postgres`)**:
   - Starts `pgvector/pgvector:pg16` on container port 5432 (mapped to host port 5433).
   - Runs continuous health checks: `pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}`.
   - Persists data to the named volume `postgres_data` (Docker name `rag-project_postgres_data`; the Compose project name is pinned to `rag-project`).
2. **API service (`api`)**:
   - Waits for the `postgres` healthcheck to pass before booting (`condition: service_healthy`).
   - Runs database bootstrap (`init_db()`), enabling `vector` extension and creating tables.
   - Mounts `server/storage` at `/app/storage` for local document persistence.
   - Exposes port 8000.

### Interacting with the API
- **Health Check**: `GET http://localhost:8000/healthz`
- **Swagger Documentation**: `http://localhost:8000/docs`
- **Interactive OpenAPI Spec**: `http://localhost:8000/redoc`

### Ingesting Documents Inside Docker
```bash
# Copy document to storage directory
cp /path/to/handbook.pdf server/storage/uploads/

# Run ingestion via docker compose exec
scripts/compose.sh exec api python -m app.main ingest /app/storage/uploads/handbook.pdf --title "Staff Policy"
```

---

## 4. Evaluation Workflow

To run deterministic quality metrics and Ragas evaluation (from `server/`):

```bash
# Standard evaluation
python -m app.main evaluate --dataset evaluation_data/ragas_dataset.json

# Capture immutable baseline
python -m app.main evaluate --dataset evaluation_data/ragas_dataset.json --save-baseline

# Run in CI/CD pipeline enforcing quality gates (exits nonzero on gate failure)
python -m app.main evaluate --dataset evaluation_data/ragas_dataset.json --enforce-quality-gate
```

---

## 5. CI Workflow (GitHub Actions)

The CI pipeline runs on every push and pull request via `.github/workflows/ci.yml`:
1. **Checks out** code repository.
2. **Sets up Python 3.12** with dependency caching.
3. **Provisions PostgreSQL with pgvector** container service with automated healthchecks.
4. **Installs dependencies** from `server/requirements.txt` (Python steps run in `server/`).
5. **Runs syntax and static compilation checks** across all application modules and tests.
6. **Executes automated unit tests** with pytest.
7. **Validates the Compose file** (`infrastructure/docker/docker-compose.yml`) and **builds the backend image** from `server/`.

---

## 6. Troubleshooting

### 1. Database Connection Refused
- **Symptom**: `psycopg.OperationalError: connection to server at "localhost", port 5433 failed`.
- **Resolution**:
  - If running locally on host, verify Docker Postgres is running: `scripts/compose.sh ps`.
  - Ensure the host port in `DATABASE_URL` matches `infrastructure/docker/docker-compose.yml` (`5433` on host, `5432` inside container network).
  - Verify credentials match `POSTGRES_USER` and `POSTGRES_PASSWORD`.

### 2. pgvector Extension Missing
- **Symptom**: `type "vector" does not exist`.
- **Resolution**:
  - Run `python -m app.main init-db` or ensure PostgreSQL image is `pgvector/pgvector:pg16` rather than plain `postgres:16`.

### 3. NVIDIA API Errors / Rate Limits
- **Symptom**: `AnswerGenerationError: NVIDIA request failed... 401 Unauthorized or 429 Too Many Requests`.
- **Resolution**:
  - Check that `NVIDIA_API_KEY` is present in `server/.env` without surrounding quotes.
  - The answerer has built-in timeout and retry settings; check model availability on the NVIDIA API dashboard.

### 4. Langfuse Connection Failures
- **Symptom**: `Could not initialize Langfuse; continuing without tracing`.
- **Resolution**:
  - Observability is designed to be **fail-open**: network or authentication issues with Langfuse will never block RAG operations.
  - Check `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_BASE_URL`.
  - To disable telemetry entirely, set `LANGFUSE_ENABLED=false`.

### 5. First-Run Model Download Delays
- **Symptom**: Ingestion or hybrid search pauses for 10-30 seconds on initial run.
- **Resolution**:
  - `sentence-transformers` automatically downloads `all-MiniLM-L6-v2` and `ms-marco-MiniLM-L-6-v2` to the HuggingFace cache directory on first use.
  - Subsequent queries use the local cache. In Docker, this is cached under `/app/.cache/huggingface`.

### Changing chunking settings

New chunk sizes only apply to documents ingested afterwards. Re-index existing
documents to rebuild their chunks (the original file must still exist at its
stored path; the old chunks are kept if re-indexing fails):

```bash
cd server
python -m app.main reindex <document-uuid>
```

