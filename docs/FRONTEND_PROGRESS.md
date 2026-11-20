# ContextIQ Frontend — Progress Tracker

Tracks implementation of [FRONTEND_IMPLEMENTATION_PLAN.md](FRONTEND_IMPLEMENTATION_PLAN.md).
Work goes **one phase at a time**: each phase is reviewed and approved ("good to go")
before the next one starts. Updated at the end of every phase.

**Branch**: `feature/frontend-implementation` · **Last updated**: 2026-11-20 (Phase 4 complete)

**Legend**: ✅ done · 🔍 done, awaiting review/commit · ⏸ waiting for go-ahead · ⬜ not started · ⚠️ needs attention

---

## Phase overview

| # | Phase | Status | Reviewed | Committed |
|---|---|---|---|---|
| 1 | Scaffold, Tailwind v4, shadcn/ui, theme | ✅ Done | ✅ | ✅ `966a7110` |
| 2 | TypeScript types, API client, service modules | ✅ Done | ✅ | ✅ `905e9e93` |
| 3 | TanStack Query, Zustand stores, auth guard | ✅ Done | ✅ | ✅ `905e9e93` |
| 4 | Login + Register pages | ✅ Done | ✅ | ✅ |
| 5 | App shell: Sidebar + Header | ⏸ Next (waiting for go-ahead) | ⬜ | ⬜ |
| 6 | New Chat welcome screen + suggested prompts | ⬜ | ⬜ | ⬜ |
| 7 | Active chat page (answer / clarification / abstention) | ⬜ | ⬜ | ⬜ |
| 8 | Sources panel, citation chips, freshness badges | ⬜ | ⬜ | ⬜ |
| 9 | Documents page (table, upload, delete) | ⬜ | ⬜ | ⬜ |
| 10 | End-to-end testing on live backend, polish | ⬜ | ⬜ | ⬜ |

---

## Phase details

### Phase 1 — Scaffold & theme ✅
- [x] Next.js 16.4 (App Router, Turbopack), React 19, TypeScript strict, `src/` + `@/*` alias
- [x] Tailwind CSS v4 (CSS-first config in `src/app/globals.css`)
- [x] shadcn/ui 4.23 (`radix-nova` style, Radix primitives) + 18 components in `components/ui/`
- [x] ContextIQ dark palette mapped to shadcn tokens + `success` / `warning` / `info` tokens
- [x] Root layout: Inter + Geist Mono, fixed `dark` class, `TooltipProvider`, `Toaster`
- [x] `lib/constants.ts`, `.env.example`, `type-check` script, `client/README.md`
- [x] Plan updated for shadcn/ui, Next.js 16, Tailwind v4
- **Verified**: type-check, lint, build; screenshots at desktop and 375px

### Phase 2 — API layer ✅
- [x] `types/api.ts` — exact backend mirrors (5 freshness values, `effective/expiry_date`, `queued` status)
- [x] `types/chat.ts`, `types/document.ts` — UI-only types
- [x] `lib/token-storage.ts` — SSR-safe localStorage token access
- [x] `services/api.ts` — fetch client: JSON / form / multipart, bearer token, `ApiError`, 401 handler hook
- [x] Safe error messages: 5xx details never shown; 4xx backend messages shown; 422 lists formatted
- [x] `auth.service.ts`, `chat.service.ts`, `document.service.ts`
- **Verified**: 21 wire-level tests against a mock HTTP server (pass); type-check, lint, build
- **Not verified**: against the live backend (backend was down)

### Phase 3 — Data & state layer ✅
- [x] Plan switched to **TanStack Query** (server state) + **Zustand** (client state only)
- [x] `app/providers.tsx` — QueryClientProvider, auth bootstrap, cross-tab logout, devtools (dev only)
- [x] `lib/query-client.ts` (30s staleTime, retry policy), `lib/query-keys.ts`, `lib/jwt.ts`
- [x] `store/useAuthStore.ts` — initialize / login / logout, 30-min expiry timer, cache cleared on user change
- [x] `store/useChatUiStore.ts` — citation panel + sidebar UI state
- [x] `hooks/queries/useSessions.ts`, `useMessages.ts` (optimistic send, race-safe), `useDocuments.ts`
- [x] `hooks/useAuthGuard.ts` — `useAuthGuard()` / `useGuestGuard()`
- **Verified**: 14 store/hook tests in jsdom + mock backend (pass); Phase 2 tests still pass; build; no console errors in Chrome
- **Not verified**: live backend (guard redirects were verified in a real browser in Phase 4)

### Phase 4 — Login & Register ✅
- [x] Installed `react-hook-form` 7.92, `zod` 4.6, `@hookform/resolvers` 7.0; added shadcn `alert`, `spinner`
- [x] `lib/validation/auth.ts` — Zod schemas mirroring backend rules (password 12–128, matching confirm)
- [x] `lib/errors.ts` — network / 5xx → toast; 401 / 409 / 422 → inline (plan §9)
- [x] `components/auth/LoginForm.tsx` — inline "Incorrect email or password."
- [x] `components/auth/RegisterForm.tsx` — 409 on the email field; auto-login; if auto-login fails → toast + `/login`
- [x] `components/auth/PasswordInput.tsx` — show/hide toggle *(decision: yes)*
- [x] `components/auth/AuthCard.tsx`, `RouteGuards.tsx` (`RequireAuth`, `GuestOnly`, `RootRedirect`)
- [x] `components/common/Logo.tsx`, `PageLoader.tsx`
- [x] `app/login/page.tsx`, `app/register/page.tsx` — server pages with tab titles
- [x] `app/page.tsx` — Phase 1 preview replaced by redirect to `/chat` or `/login`
- [x] `app/chat/page.tsx` + `ChatPlaceholder.tsx` — **temporary** protected page *(decision: yes; replaced in Phase 6)*
- **Verified**: 21 browser tests in headless Chrome against a mock backend on :8000 (pass) — redirects for signed-in/out users, field validation, wrong password, 409, server unreachable toast, register → auto-login, reload keeps session, logout, idle token expiry, cross-tab logout, 375px layout, no console errors; type-check, lint, build (all routes prerender with Cache Components)
- **Not verified**: against the live backend (backend was down)

### Phase 5 — App shell ⬜
- [ ] `components/layout/AppShell.tsx` — Sidebar | Chat | Sources layout
- [ ] `Sidebar.tsx` — logo, New Chat, session list (all statuses, newest first), nav, user email, logout; collapsible; mobile drawer
- [ ] `Header.tsx` — session title, mobile menu button

### Phase 6 — New Chat screen ⬜
- [ ] `app/chat/page.tsx` — welcome heading + 4 suggested prompt cards
- [ ] `components/chat/SuggestedPrompts.tsx`, `ChatInput.tsx`
- [ ] First message: create session → optimistic send → navigate to `/chat/[id]`

### Phase 7 — Active chat ⬜
- [ ] `app/chat/[sessionId]/page.tsx` — activate + load history; 404 → "Conversation not found."
- [ ] `ChatContainer`, `MessageItem`, `UserMessage`, `AssistantMessage` (markdown), `TypingIndicator`
- [ ] `ClarificationBadge` (blue, from `metadata.needs_clarification`), `AbstentionAlert` (amber)
- [ ] Install `react-markdown`, `remark-gfm`, `rehype-highlight`

### Phase 8 — Sources panel ⬜
- [ ] `components/sources/SourcesPanel.tsx` (desktop panel / mobile drawer)
- [ ] `CitationChip.tsx` (inline `[S1]`), `CitationCard.tsx` (file, page/section, version, dates)
- [ ] Freshness badges: current / outdated / superseded / future / undated

### Phase 9 — Documents page ⬜
- [ ] `app/documents/page.tsx` — "Knowledge Base" (shared) heading, empty state
- [ ] `DocumentTable`, `DocumentStatusBadge`, `DocumentUploadZone` (client-side extension + empty-file checks), `DeleteConfirmDialog`
- [ ] `components/common/Spinner.tsx`, `EmptyState.tsx`

### Phase 10 — End-to-end & polish ⬜
- [ ] Run the full acceptance checklist (below) against the **live backend**
- [ ] Responsive polish (375px), console-error sweep, TypeScript cleanup

---

## Acceptance checklist (plan §14)

To be ticked only when verified against the **live backend** (Phase 10, or earlier when the backend is running).

**Authentication**
- [ ] Register a new account via `/register`
- [ ] Log in; JWT stored in `localStorage`
- [ ] Unauthenticated access to protected routes redirects to `/login`
- [ ] Token expiry (30 min) logs out and redirects to `/login`

**Documents**
- [ ] Upload a `.pdf` from the Documents page
- [ ] Uploaded document shows `completed` status and correct chunk count
- [ ] Unsupported extension (e.g. `.png`) shows a client-side error
- [ ] Empty file shows a client-side error
- [ ] Delete with confirmation dialog
- [ ] Deleted document disappears immediately
- [ ] Page and delete dialog say the knowledge base is shared

**Chat & sessions**
- [ ] Start a new chat from the sidebar
- [ ] New chat screen shows welcome + 4 suggested prompts
- [ ] First question creates a session and navigates to `/chat/[id]`
- [ ] New session appears in the sidebar
- [ ] Clicking a previous session loads its history
- [ ] `archived` sessions remain visible in the sidebar
- [ ] First question is never lost or duplicated during navigation
- [ ] TypingIndicator shows while the backend is processing

**AI responses**
- [ ] Answers render inline `[S1]`, `[S2]` chips
- [ ] Clarifications show the blue indicator, live and after reload
- [ ] Abstentions show the amber info box
- [ ] Markdown renders correctly (headings, bold, lists, code)

**Sources panel**
- [ ] Clicking `[S1]` opens the sources panel
- [ ] Citation card shows correct filename and page/section
- [ ] `outdated`, `superseded`, `future` badges are coloured correctly; `undated` shows none

**Quality**
- [ ] `npm run type-check` passes with zero errors
- [ ] No browser console errors during normal use
- [ ] Layout works at 375px
- [ ] No hardcoded mock data in production code
- [ ] No raw backend errors or stack traces shown to users

---

## Open items & known issues

| | Item | Owner | Notes |
|---|---|---|---|
| ⚠️ | Rotate `JWT_SECRET_KEY` in `server/.env` | You | The old key is in Git history on the remote. Rotating also logs out existing users |
| ⚠️ | Live backend not yet available for testing | You | Needs `scripts/compose.sh up -d postgres` + API running from `server/`; Docker was unreachable from the agent session |
| ⬜ | Approve live `sendMessage` test (calls NVIDIA, costs money) | You | Needed by Phase 7/10 |
| ⬜ | `npm audit`: 4 moderate in shadcn CLI tooling (`ts-morph` → `minimatch`) | — | Build-time only, not in the browser bundle; revisit when shadcn updates |
| ⬜ | Update stored `source_path` values after the monorepo move | You | SQL in the monorepo restructure notes; root `storage` symlink keeps reindex working until then |
| ⬜ | Add a `LICENSE` file | You | Listed in the target monorepo structure; licence choice is yours |
