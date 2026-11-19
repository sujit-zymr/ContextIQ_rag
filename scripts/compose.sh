#!/usr/bin/env bash
# Run Docker Compose for ContextIQ from any directory.
#
# Passes server/.env as the interpolation env file so ${LANGFUSE_BASE_URL},
# ${API_PORT}, etc. resolve the same way they did before the monorepo move.
#
# Usage:
#   scripts/compose.sh up -d postgres
#   scripts/compose.sh up -d --build
#   scripts/compose.sh config
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="$ROOT_DIR/server/.env"
COMPOSE_FILE="$ROOT_DIR/infrastructure/docker/docker-compose.yml"

args=(-f "$COMPOSE_FILE")
if [[ -f "$ENV_FILE" ]]; then
  args+=(--env-file "$ENV_FILE")
else
  echo "warning: $ENV_FILE not found; using defaults (copy server/.env.example)" >&2
fi

exec docker compose "${args[@]}" "$@"
