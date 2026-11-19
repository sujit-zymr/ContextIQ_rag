# ContextIQ Client

**Status: planned, not yet implemented.** This directory is reserved for the
ContextIQ web frontend; it intentionally contains no source code yet.

## Planned scope

A web application on top of the existing [server](../server/README.md) REST API:

- Register / log in (JWT bearer auth).
- Chat sessions with grounded answers and inline `[S1]`-style citations, plus a
  sources panel showing document, page/section, version and freshness.
- Clarification and insufficient-evidence (abstention) states.
- Shared knowledge-base management: upload, list and delete documents.

Planned stack: Next.js (App Router) + TypeScript, Tailwind CSS, Radix UI,
Zustand. The only configuration it will need is the API base URL
(`NEXT_PUBLIC_API_BASE_URL`, default `http://localhost:8000`); no secrets belong
in the client.

## References

- [Frontend implementation plan](../docs/FRONTEND_IMPLEMENTATION_PLAN.md)
- [Backend API specification](../docs/BACKEND_SPECIFICATION.md)
