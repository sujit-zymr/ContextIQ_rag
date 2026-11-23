# ContextIQ — Instructions for Claude

ContextIQ is an enterprise RAG assistant: users upload documents to a shared knowledge
base, ask questions in chat sessions, and get answers grounded in cited sources.

## Repository layout

| Path | Contents |
|---|---|
| `server/` | Python 3.12 / FastAPI backend (implemented). Package `app/` |
| `client/` | Next.js 16 frontend (in progress, phase by phase) |
| `infrastructure/docker/` | `docker-compose.yml`: Postgres 16 + pgvector, API container |
| `scripts/compose.sh` | Docker Compose wrapper (passes `server/.env`) |
| `docs/` | Specs, plans, progress tracker (see "Documentation map") |
| `.github/workflows/ci.yml` | CI: py_compile, pytest, compose config check, image build |

### Backend architecture (`server/app/`)
- `api/` — FastAPI app (`main.py`: health, sessions, messages), `auth.py` (JWT, OAuth2
  password flow), `documents.py` (document management), Pydantic schemas.
- `ingestion/` — load (PDF/DOCX/TXT/MD) → chunk → embed (`all-MiniLM-L6-v2`, 384-d).
- `retrieval/` — hybrid search (pgvector + Postgres full-text, RRF), cross-encoder
  reranking, evidence gate (abstention), versioning/freshness, query spell normalisation.
- `generation/` — prompt + answer generation (NVIDIA Nemotron via `langchain-openai`),
  citation verification.
- `conversations/` — follow-up contextualisation / clarification detection.
- `database/` — psycopg repositories (raw SQL) + schema in `connection.py`.
- `evaluation/` — Ragas + retrieval/citation/ACL quality metrics.
- `observability.py` — Langfuse tracing with redaction (`observation_span`).
- `main.py` — CLI: `init-db`, `ingest`, `reindex`, `delete`, `search`, `answer`,
  `evaluate`, `collect-evaluation-data`.

### Frontend architecture (`client/src/`)
`app/` routes · `components/ui/` shadcn · `components/{auth,common,...}` app components ·
`services/` fetch client + API calls · `hooks/queries/` TanStack Query hooks ·
`store/` Zustand · `types/` backend mirrors · `lib/` helpers (query keys/client, errors,
validation, token storage, constants).

## Commands

```bash
# Database (from repo root) — Postgres on localhost:5433
scripts/compose.sh up -d postgres
scripts/compose.sh ps

# Backend (from server/)
source ../venv/bin/activate            # or a local .venv
python -m pip install -r requirements.txt
python -m app.main init-db
uvicorn app.api.main:app --reload --host 127.0.0.1 --port 8000   # docs at /docs
python -m pytest -q                    # tests
python -m py_compile $(find app tests -name "*.py")             # CI syntax check

# Frontend (from client/)
npm install
npm run dev                            # http://localhost:3000
npm run type-check && npm run lint && npm run build
```

Ports: API `8000`, Postgres `5433` (host) / `5432` (container network), client `3000`.
The backend's default CORS origins include `localhost:3000` and `localhost:5173`.

## Phase workflow (mandatory)

The frontend is built phase by phase from `docs/FRONTEND_IMPLEMENTATION_PLAN.md` §13.
Progress is tracked in `docs/FRONTEND_PROGRESS.md`. Follow this cycle exactly:

1. **Start only on the user's command.** Never begin a phase until the user explicitly
   says to start it (e.g. "start phase 5", "good to go"). Finishing one phase is not
   permission to start the next.
2. **Before starting**, briefly explain the phase if asked, and list any open decisions.
   If the user says "defaults", use the proposed defaults.
3. **Implement the whole phase**, then verify it (see "Verification").
4. **Update `docs/FRONTEND_PROGRESS.md`**: tick completed items, set the phase to
   🔍 "Awaiting review", record what was and was not verified, set the next phase to ⏸.
   Update the plan doc if the implementation deviated from it.
5. **Stop and report for review.** Do NOT commit or push. Report: files added/changed,
   verification results, anything not verified, and points needing the user's decision.
6. **Commit and push only after the user confirms** the phase works (e.g. "checked it,
   commit and push"). Then mark the phase ✅ (Done / Reviewed / Committed) in the
   tracker, add the previous phase's commit hash if missing, commit, and push.
7. **Wait** for the user's command before starting the next phase.

If the user interrupts or rejects a tool call, stop and wait for instructions.
Work outside the phases (bug fixes, docs, backend changes) follows the same rule:
implement → verify → report → commit/push only when the user approves.

## Git rules

- Never commit or push without the user's explicit approval.
- Never commit or push to `main`; changes reach `main` only through pull requests.
  Frontend work goes on `feature/frontend-implementation`.
- New branches: `git checkout --no-track -b <name> origin/main` (so a plain `git push`
  cannot target `main`); first push with `git push -u origin <name>`.
  Naming: `feature/…`, `fix/…`, `chore/…`, `docs/…`.
- Before pushing, check `git branch -vv` shows the intended upstream.
- Stage explicit paths (no repo-wide `git add -A`; `git add -A -- <path>` is fine to
  record deletions/renames inside a specific path). Confirm no `.env`, secrets,
  `node_modules/`, `.next/`, `venv/`, uploads (`server/storage/`) or generated eval data
  (`server/evaluation_data/`) are staged.
- **Check the index before every commit**: run `git diff --cached --name-only` and make
  sure it lists exactly the files intended for that commit. `git commit` includes
  everything already staged, not just the files added last (e.g. earlier `git mv` /
  `git rm` changes). To commit only certain files, use `git commit -- <paths>`.
- When splitting work into several commits, commit and verify each one in turn
  (`git show --stat HEAD`) before staging the next.
- If an unpushed local commit is wrong, it may be undone with `git reset --mixed HEAD~1`
  (keeps the working tree) and redone; never do this to a pushed commit.
- Commit messages: Conventional Commits with a scope, e.g.
  `feat(client): add app shell with sidebar and header (phase 5)`,
  `fix(api): …`, `docs: …`, `chore: …`. Body: what changed and how it was verified
  (live vs mock backend). One logical change per commit.
- Never rewrite published history (no force-push, no amend of pushed commits) unless asked.
- PR descriptions: use the `pr-description` skill (`.claude/skills/pr-description/`).

## Verification

Never claim something works unless it was tested; always list what was not verified.

**Frontend (every phase)** — from `client/`: `npm run type-check`, `npm run lint`,
`npm run build` (all routes must prerender with Cache Components). Then test behaviour in a
real browser (headless Chrome) where the phase has UI: main flows, error states, 375px
mobile width, no console errors. Prefer the live backend; if it is down, use a mock backend
and say so. Keep test scripts and screenshots in the scratchpad, not the repo.

**Backend** — from `server/`: `python -m pytest -q` must pass (41+ tests) and
`py_compile` must succeed. New behaviour needs tests. Tests use `unittest` + FastAPI
`TestClient` with the database mocked, so they run without Postgres.

**Costly / external calls** — `POST /sessions/{id}/messages`, `answer`, and `evaluate`
call the NVIDIA API (paid). Ask before running them. Langfuse tracing should be disabled
(`LANGFUSE_ENABLED=false`) for local test runs unless tracing itself is being tested.

## Frontend conventions (`client/`)

- Next.js 16 (App Router; `cacheComponents` + `partialPrefetching` enabled), React 19,
  TypeScript strict. This Next.js version differs from older ones: read the relevant guide
  in `client/node_modules/next/dist/docs/` before using an unfamiliar API (`client/AGENTS.md`).
- Pages are server components (they set `metadata`); interactive parts are client
  components (`"use client"`) rendered inside them.
- Tailwind CSS v4 (config in `src/app/globals.css`). Use semantic classes (`bg-background`,
  `bg-card`, `text-muted-foreground`, `bg-primary`, `text-success|warning|destructive|info`),
  never raw palette classes. Light theme by default with a Dark/System option (`next-themes`,
  class on `<html>`); use the `dark:` variant for anything theme-specific and check both themes.
- UI components: shadcn/ui (`radix-nova`, Radix). Add with `npx shadcn@latest add <name>`;
  don't hand-roll components shadcn provides. Icons: `lucide-react`.
- Server state: TanStack Query hooks in `src/hooks/queries/` (keys in `src/lib/query-keys.ts`).
  Components never call `src/services/*` directly. Mutations never retry.
- Client state: Zustand (`useAuthStore`, `useChatUiStore`) only — never server data.
- Protected content renders inside `RequireAuth`; guest pages inside `GuestOnly`.
- Forms: React Hook Form + Zod + shadcn `field`; limits come from `src/lib/constants.ts`.
- Errors: network/5xx → toast; 4xx → inline. Never show raw backend 5xx details.
- Types in `src/types/api.ts` must mirror `server/app/api/*schemas.py`; update both sides
  of the contract together and note it in `docs/BACKEND_SPECIFICATION.md`.
- Accessibility: labelled inputs, `aria-invalid` on errors, `aria-label` on icon buttons,
  keyboard-reachable controls, visible focus rings.
- File names: components `PascalCase.tsx`, hooks `useX.ts`, shadcn files kebab-case.
- Install new dependencies only in the phase that first needs them, with an explicit
  version (`npm install pkg@x.y.z`); commit `package-lock.json` with `package.json`.

## Backend conventions (`server/`)

- Python 3.12, FastAPI, Pydantic v2. Run everything from `server/`.
- SQL lives in `app/database/*_repository.py` and is always parameterised (`%s`);
  never build SQL with f-strings or string formatting.
- API request/response models live in `app/api/schemas.py` / `document_schemas.py`.
  Return 404 for both missing and foreign-owned sessions (no existence leak).
- Wrap significant operations in `observation_span(...)`; never send document content or
  PII to Langfuse unless `LANGFUSE_CAPTURE_CONTENT=true`.
- Configuration comes from environment variables (`server/.env`, template
  `server/.env.example`); add new variables to `.env.example` and `docs/deployment.md`.
- Do not change backend behaviour as part of frontend phases unless the user asks.

## Documentation map — keep these in sync

| When this changes | Update |
|---|---|
| A frontend phase progresses | `docs/FRONTEND_PROGRESS.md` |
| Frontend design/structure deviates from the plan | `docs/FRONTEND_IMPLEMENTATION_PLAN.md` |
| An API endpoint, schema or response shape | `docs/BACKEND_SPECIFICATION.md`, `client/src/types/api.ts` |
| Env vars, Docker, deployment | `docs/deployment.md`, `server/.env.example`, `infrastructure/README.md` |
| Backend pipeline/architecture | `docs/architecture.md`, `server/README.md` |
| Commands, workflow or conventions | this file (`CLAUDE.md`) |

## Security & privacy

- Never print, log, copy or commit values from `server/.env` (API keys, `JWT_SECRET_KEY`).
  When inspecting config, show variable names only.
- No secrets in `NEXT_PUBLIC_*` variables or anywhere in `client/`.
- Uploaded documents (`server/storage/`) may be private: never commit or share them.
- Never put the user's personal details in requests to external services.

## Communication

- Before risky or hard-to-reverse actions (moving data, deleting, rewriting history,
  Docker volume changes), explain the risk and get confirmation.
- Reports: what changed, how it was verified, what was not verified, open decisions.
  Use clickable file links.
