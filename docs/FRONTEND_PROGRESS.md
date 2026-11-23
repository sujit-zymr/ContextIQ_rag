# ContextIQ Frontend — Progress Tracker

Tracks implementation of [FRONTEND_IMPLEMENTATION_PLAN.md](FRONTEND_IMPLEMENTATION_PLAN.md).
Work goes **one phase at a time**: each phase is reviewed and approved ("good to go")
before the next one starts. Updated at the end of every phase.

**Branch**: `feature/frontend-implementation` · **Last updated**: 2026-11-23 (UI redesign and logo committed; Phase 10 waiting for go-ahead)

**Legend**: ✅ done · 🔍 done, awaiting review/commit · ⏸ waiting for go-ahead · ⬜ not started · ⚠️ needs attention

---

## Phase overview

| # | Phase | Status | Reviewed | Committed |
|---|---|---|---|---|
| 1 | Scaffold, Tailwind v4, shadcn/ui, theme | ✅ Done | ✅ | ✅ `966a7110` |
| 2 | TypeScript types, API client, service modules | ✅ Done | ✅ | ✅ `905e9e93` |
| 3 | TanStack Query, Zustand stores, auth guard | ✅ Done | ✅ | ✅ `905e9e93` |
| 4 | Login + Register pages | ✅ Done | ✅ | ✅ `15dbcaf9` |
| 5 | App shell: Sidebar + Header | ✅ Done | ✅ | ✅ `96a5d02c` |
| 6 | New Chat welcome screen + suggested prompts | ✅ Done | ✅ | ✅ `ceab8988` |
| 7 | Active chat page (answer / clarification / abstention) | ✅ Done | ✅ | ✅ `00b8db92` |
| 8 | Sources panel, citation chips, freshness badges | ✅ Done | ✅ | ✅ `fe50ec7e` |
| 9 | Documents page (table, upload, delete) | ✅ Done | ✅ | ✅ `164bfd4d` |
| — | UI redesign to the light mockup + theme toggle, new logo (between 9 and 10) | ✅ Done | ✅ | ✅ `de395220` (+ logo commit) |
| 10 | End-to-end testing on live backend, polish | ⏸ Waiting for go-ahead | ⬜ | ⬜ |

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

### Phase 5 — App shell ✅
- [x] Added shadcn `sidebar` (+ `use-mobile` hook, rewritten with `useSyncExternalStore` to fix a lint error)
- [x] `app/(app)/layout.tsx` — route group for signed-in screens: Suspense + `RequireAuth` + `AppShell`
- [x] `components/layout/AppShell.tsx` — `SidebarProvider` (260px / 64px), restores collapsed preference from cookie
- [x] `components/layout/Sidebar.tsx` — logo, New chat, Documents nav (Chat item removed after Phase 9 review: duplicated New chat and the conversation list), recent conversations, user menu with Log out; icon-only collapse (`Ctrl/⌘+B`), mobile drawer
- [x] `components/layout/SessionList.tsx` — all sessions newest first (archived included), message-count badge, active indigo left bar, skeleton / error + Retry / empty states
- [x] `components/layout/Header.tsx` — sidebar toggle + title ("New chat", session title, "Knowledge Base")
- [x] `hooks/useCurrentSession.ts`
- [x] Temporary `PhasePlaceholder` pages for `/chat` (Phase 6), `/chat/[id]` (Phase 7), `/documents` (Phase 9); Phase 4 `ChatPlaceholder` removed (logout moved to the sidebar user menu)
- [x] `useChatUiStore`: removed `sidebarCollapsed` / `mobileSidebarOpen` (now owned by `SidebarProvider`)
- **Verified**: 17 browser tests in headless Chrome against a mock backend (pass) — protected redirects, skeleton loading, sort order incl. archived, badges, active highlighting (only the current item), header titles, nav, New chat, 64px collapse centred + persisted across reload, `Ctrl+B`, error + Retry (no raw detail), empty state, user-menu logout, mobile drawer open/close-on-select, no horizontal scroll at 375px, no console errors; type-check, lint, build (`/chat/[sessionId]` is partially prerendered)
- **Not verified**: against the live backend (backend was down)

### Phase 6 — New Chat screen ✅
- [x] Added shadcn `input-group`
- [x] `components/chat/NewChatScreen.tsx` — heading "What would you like to know?", sub-heading, prompts, sticky input; `/chat` page now uses it (Phase 5 placeholder removed)
- [x] `components/chat/SuggestedPrompts.tsx` — the 4 plan prompts; click pre-fills + focuses the input (does not send); 1 column on mobile
- [x] `components/chat/ChatInput.tsx` — auto-grows to 6 rows then scrolls; Enter sends, Shift+Enter newline (IME-safe); disabled + spinner while busy; 8000-char limit with counter near the limit; reused in Phase 7
- [x] `hooks/queries/useStartConversation.ts` — create session (title from question) → start send → navigate to `/chat/{id}` without waiting for the answer
- [x] `sendMessageMutationOptions()` extracted in `useMessages.ts` (shared by `useSendMessage` and the first-message flow)
- [x] `lib/chat.ts` — `deriveSessionTitle()` (≤ 50 chars, ellipsis)
- [x] Error handling: session creation failure → toast, question kept, nothing sent; send failure after navigation → toast
- [x] Fixed (Phase 5): header divider was pinned to the top edge; now vertically centred
- **Verified**: 13 browser tests in headless Chrome against a mock backend (pass) — welcome content, autofocus, disabled send for empty/whitespace, prompt pre-fill, Shift+Enter + 6-row cap, counter + maxLength, create-session 500 (toast, text kept, no raw detail), first send (derived title, `{content, top_k: 5}`, navigates in < 1.5 s before the answer), no history fetch while pending (race guard), sidebar badge refresh after the answer, 502 toast, 375px single column + no horizontal scroll, no console errors; Phase 5 tests re-run (17 pass); type-check, lint, build
- **Not verified**: against the live backend / real NVIDIA answers (backend down; paid call needs approval). `/chat/[id]` still shows the Phase 7 placeholder, so the question and answer are not displayed yet

### Phase 7 — Active chat ✅
- [x] Installed `react-markdown` 10.1, `remark-gfm` 4.0, `rehype-highlight` 7.0, `@tailwindcss/typography` 0.5; code-highlight colours from theme tokens (`globals.css`)
- [x] `app/(app)/chat/[sessionId]/page.tsx` → `ConversationRoute` (UUID check, remount per session) → `ConversationView`
- [x] `ConversationView` — activates the session once (skipped while the first question is in flight), loads history, follow-up questions, 404 → toast + `/chat`, load error + Try again, empty state, skeleton
- [x] `ChatContainer` — opens at the bottom, follows new messages, "Scroll to latest" button when scrolled up
- [x] `MessageItem`, `UserMessage` (right bubble), `AssistantMessage` (answer / clarification / abstention via `lib/messages.ts`), `MarkdownContent`
- [x] `ClarificationBadge` (blue left border), `AbstentionAlert` (amber; internal `answer_reason` hidden), `TypingIndicator` (3-dot pulse)
- [x] Send failure → toast + question restored to the input; history resyncs
- [x] App shell: content area is now the scroll container (fixed-height viewport) so inputs stay pinned
- [x] Found via live backend: malformed ids return **422** (not 404) → validated client-side, same "Conversation not found." handling, no request
- **Verified**:
  - 22 browser tests against a mock backend (pass) — 3 states from history and live, markdown (heading, bold, list, GFM table, highlighted code, safe links), raw HTML not executed, activation once, opens at bottom, follow-up flow (typing indicator, input disabled, single POST), clarification persists after reload, 502 (toast, text restored, resync shows saved question once), scroll-to-latest, draft reset on switch, empty state, load error + retry, 404 redirect, first-message end-to-end, 375px, no console errors
  - 6 checks against the **live backend** (free endpoints only, no NVIDIA calls) — real login, real session list incl. archived, empty history + header, `POST /activate` marks the session active server-side, malformed id (no request), unknown UUID → live 404 redirect
  - type-check, lint, build
- **Not verified**: real AI answers (paid `POST /messages` not run); Phase 5/6 mock suites not re-run after the UUID check (their mocks used non-UUID ids; the first-message flow is covered by the Phase 7 suite)
- **Test data left in the live DB**: user `contextiq-e2e-<timestamp>@example.com` with a few empty "E2E …" sessions (no delete endpoint)

### Phase 8 — Sources panel ✅
- [x] `components/sources/SourcesPanel.tsx` — 320px right panel at ≥1024px (close button, `Esc`), slide-over drawer (shadcn `sheet`) below; shows one answer's sources; scrolls to and highlights the clicked citation; rendered by `ConversationView`
- [x] `CitationChip.tsx` — inline `[S1]` button (labelled with the file name, `aria-pressed` while its card is shown); `lib/citations.ts` rehype plugin turns only markers that match the message's citations into chips (unknown markers and code stay text)
- [x] `CitationCard.tsx` — title, filename, page/section, version, effective/expiry/checked dates (`lib/format.ts`), competing versions
- [x] `FreshnessBadge.tsx` — current (green) / outdated (amber) / superseded (red) / future (blue); undated or null → none
- [x] "View sources (n)" button under every answer with citations (all screen sizes)
- [x] `hooks/useMediaQuery.ts`; no new npm dependencies
- **Verified**:
  - 21 browser tests against a mock backend (pass) — chips for known markers in order (incl. `[S2][S3]`), `[S9]` and code stay text, no chips on clarification/abstention, panel hidden until opened, chip → 320px panel with the right card highlighted, card fields + date formatting, all 4 badge colours and undated → none, section + competing versions, scroll to S8, no overflow with long names, close button / `Esc` / "View sources", keyboard Enter on a chip, follow-up answer opens its own sources, panel closes on conversation switch, 1024px no horizontal scroll, 375px drawer (open from chip and button, `Esc` and close button), no console errors
  - Phase 7 suite re-run as regression (22 tests, pass), including the Phase 6 first-message flow
  - type-check, lint, build
- **Not verified**: real citations from the live backend (backend was down, and producing an answer is a paid NVIDIA call)
- **Decision**: the panel opens only when the user clicks a chip or "View sources" (it does not auto-open on desktop)

### Phase 9 — Documents page ✅
- [x] `app/(app)/documents/page.tsx` → `DocumentsView` — "Knowledge Base" header, shared-by-all-users subtitle + count, empty state, skeleton, load error + Try again, Previous/Next pagination (50 per page)
- [x] `DocumentTable` — type tag (PDF/DOCX/TXT/MD), filename, status, chunks, "Nov 18, 2026" date, labelled delete button; failed rows show `status_message`; on phones status/chunks/date move under the filename
- [x] `DocumentStatusBadge` — completed / processing (spinner) / queued / failed; list auto-refreshes every 5 s while any document is queued or processing
- [x] `DocumentUploadZone` in a dialog — drag-and-drop or browse, one file at a time; inline errors for unsupported extension / empty file (nothing sent); spinner while the server indexes; dialog can't be closed mid-upload; success toast + list refresh; 422 → backend detail toast; 500 → generic toast
- [x] `DeleteConfirmDialog` — "…from the shared knowledge base for all users. This cannot be undone."; row removed at once, restored on failure; 404 → "Document not found."
- [x] `components/common/EmptyState.tsx`, `lib/documents.ts`, `lib/format.ts` dates now "Nov 18, 2026" everywhere (citation cards too); shadcn `spinner` used (no separate `common/Spinner`)
- [x] Removed the temporary `PhasePlaceholder` (no placeholders left); no new npm dependencies
- **Verified**:
  - 21 browser tests against a mock documents API (pass, 3 runs in a row) — empty state, page title, .png / no-extension / empty file rejected inline with no request, valid upload (spinner, can't close, toast, row added, single POST), 422 detail toast, 500 generic toast (no raw detail), drag-and-drop, two-file drop rejected, table cells + date format, failed row, processing → completed by auto-refresh, delete dialog text + Cancel, confirm delete (immediate removal, toast, single DELETE), 404 delete, pagination 1–50 / 51–55, last-row-on-page delete, list error + retry, 375px (no horizontal scroll, details under filename, upload dialog), no console errors
  - Phase 8 (21) and Phase 7 (22) suites re-run (pass)
  - type-check, lint, build
- **Fixed during testing**: the "51–55 of 55" range changed before the next page arrived; it now comes from the page shown
- **Not verified**: against the live backend (it was down); real ingestion of PDF/DOCX files

### UI redesign (light mockup + theme toggle) ✅
Requested after Phase 9 from a design mockup. Decisions: light by default with a Light/Dark/System
toggle (dark keeps the original palette); Chat nav item stays removed; "Attach document" opens the
upload dialog; "Answer from selected sources" left out (backend has no source filter).
- [x] Themes: `next-themes` provider (already a dependency) in `providers.tsx`, default light, saved under `contextiq.theme`; `dark` class no longer fixed on `<html>`; toaster follows the theme
- [x] Light tokens: white sidebar; font Inter → DM Sans
- [x] Sidebar: logo mark + wordmark in a 64px row; New chat as a plain row; Documents; "RECENT" titles only (no icons or message counts); user row with email; user menu gains Theme (Light/Dark/System)
- [x] Header: 64px, `text-lg` semibold title, toggle kept (needed on phones)
- [x] New chat screen: mockup heading/subtitle; 4 short prompt cards pre-fill a question starter
- [x] `ChatInput`: rounded box, "+ Attach document" → `UploadDocumentDialog` (extracted from `DocumentsView`), square send button, disclaimer line; no longer looks disabled when empty
- [x] Answers: `prose-invert` only in dark mode; code blocks use `text-foreground` (were unreadable in light)
- [x] Docs: plan §7.3–7.5, §7.7, §8, CLAUDE.md frontend conventions
- [x] Logo: from `client/src/assets/ContextIQ_Logo.png` — transparent PNGs in `src/assets/` (full with tagline, wordmark without tagline, "C" mark with the three dots), each with a dark-theme copy (white "Context" text and dots); `Logo` component takes `variant`; full logo on sign-in pages, wordmark in the expanded sidebar, mark in the collapsed rail, welcome screen and assistant avatar; favicon replaced with the mark. Verified by screenshots in both themes (desktop, collapsed rail, 375px) and the 13 redesign tests
- **Verified** (mock backend, headless Chrome): 13 tests — first visit light, sidebar items, welcome text and cards, prompt pre-fill + caret, input not dimmed when empty, Attach → upload → dialog closes with draft kept, answer and code text contrast in light and dark, Dark persists across reload, stored theme applied before page scripts (no flash), System follows the OS setting, Tab order, 375px no horizontal scroll, no console errors; screenshots of login / new chat / conversation / documents / menus in both themes at 1440px and 375px; type-check, lint, build
- **Not verified**: live backend; the older phase-by-phase mock suites (lost when the scratchpad was cleared) were not re-run

### Phase 10 — End-to-end & polish ⏸
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
