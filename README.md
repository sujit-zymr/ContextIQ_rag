# ContextIQ

ContextIQ is an enterprise retrieval-augmented generation (RAG) assistant: upload
documents, ask questions in a chat session, and get answers grounded in cited
sources.

This repository is a monorepo:

| Path | Contents | Status |
|---|---|---|
| [`server/`](server/README.md) | Python 3.12 / FastAPI RAG backend: ingestion, hybrid retrieval (pgvector + full-text + reranking), answer generation with citation verification, auth, sessions, document API, Ragas evaluation, Langfuse observability | **Implemented** |
| [`client/`](client/README.md) | Web frontend | **Planned**, not yet started |
| [`infrastructure/`](infrastructure/README.md) | Docker Compose for PostgreSQL/pgvector and the API container | Implemented |
| [`docs/`](docs/) | Architecture, deployment, backend API specification, frontend plan | |
| [`scripts/`](scripts/) | Repository-level helper scripts (`compose.sh`) | |
| `.github/workflows/` | CI: compile checks, tests, Compose validation, image build | |

## Quick start (backend)

```bash
# 1. Start PostgreSQL + pgvector (host port 5433)
scripts/compose.sh up -d postgres

# 2. Set up and run the API
cd server
python3.12 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env          # then set JWT_SECRET_KEY, NVIDIA_API_KEY, ...
python -m app.main init-db
uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: <http://localhost:8000/docs>. See [server/README.md](server/README.md)
for ingestion, retrieval, evaluation and observability.

To run the whole stack in containers instead: `scripts/compose.sh up --build -d`.

## Documentation

- [Architecture](docs/architecture.md)
- [Deployment and operations](docs/deployment.md)
- [Backend API specification](docs/BACKEND_SPECIFICATION.md)
- [Frontend implementation plan](docs/FRONTEND_IMPLEMENTATION_PLAN.md)

## Security

Secrets live only in `server/.env`, which is git-ignored. Never commit `.env`
files, API keys, or uploaded documents (`server/storage/`).
