# ContextIQ Infrastructure

## Docker Compose

[`docker/docker-compose.yml`](docker/docker-compose.yml) defines:

| Service | Image / build | Ports | Storage |
|---|---|---|---|
| `postgres` (`rag-postgres`) | `pgvector/pgvector:pg16` | host `5433` → `5432` | named volume `postgres_data` |
| `api` (`contextiq-api`) | built from `server/Dockerfile` | `${API_PORT:-8000}` → `8000` | bind mount `server/storage` → `/app/storage` |

The API container reads its configuration from `server/.env` (`env_file`).

### Running it

Use the wrapper from the repository root (works from any directory):

```bash
scripts/compose.sh up -d postgres       # database only (local API development)
scripts/compose.sh up --build -d        # database + API container
scripts/compose.sh ps
scripts/compose.sh logs -f api
scripts/compose.sh down                 # keeps the database volume
```

The wrapper runs `docker compose -f infrastructure/docker/docker-compose.yml
--env-file server/.env`. The `--env-file` matters: Compose substitutes
`${LANGFUSE_BASE_URL}`, `${API_PORT}`, etc. from it. Running
`docker compose -f infrastructure/docker/docker-compose.yml ...` directly also
works, but those variables then fall back to their defaults.

### Volume and project name

The Compose project name is pinned to `rag-project` (`name:` in the file).
This keeps the existing database volume, `rag-project_postgres_data`, in use
after the file moved here from the repository root. Changing or removing the
`name:` key would make Compose create a new, empty volume. Do not run
`down -v` unless you intend to delete the database.
