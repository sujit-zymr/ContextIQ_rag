# ContextIQ Frontend — Implementation Plan

**Version**: 1.0  
**Date**: 2026-11-19  
**Backend Branch**: `main` (Document Management API merged in PR #2)  
**Frontend Location**: `client/` (monorepo; backend lives in `server/`)

---

## 1. Project Context & Goals

ContextIQ is an AI-powered document assistant backed by a fully-implemented RAG (Retrieval-Augmented Generation) pipeline. The frontend must connect to the **existing backend** without inventing or duplicating any server-side logic.

A user must be able to:
- Register and log in.
- Upload documents (PDF, DOCX, TXT, Markdown).
- Ask questions about uploaded documents in a chat interface.
- Receive AI-generated answers with grounded source citations.
- Review which pages/sections each answer came from.
- Manage (view, upload, delete) documents in the shared knowledge base. Documents are **not per-user**: every authenticated user sees and can delete every document.
- Resume previous conversations.

The interface should look and feel like a real SaaS AI product — not a demo.

---

## 2. Technology Decisions

| Concern | Decision | Reason |
|---|---|---|
| Framework | **Next.js 16** (App Router, Turbopack) | File-based routing; current stable release |
| Language | **TypeScript** (strict mode) | Type safety aligned with Pydantic backend models |
| Styling | **Tailwind CSS v4** (CSS-first config in `globals.css`, no `tailwind.config.ts`) | Utility-first; the styling layer shadcn/ui is built on |
| Component Library | **shadcn/ui** (CLI v4, `new-york` style, Radix UI primitives) | Components are generated into `src/components/ui/` and owned by us; accessible Radix primitives underneath; no runtime component-library dependency |
| Toasts | **sonner** (via the shadcn `sonner` component) | shadcn's recommended toast solution |
| Icons | **lucide-react** | Already in shadcn ecosystem; clean and consistent |
| Server state | **TanStack Query v5** (`@tanstack/react-query`) | Caching, request dedup, loading/error states, invalidation after mutations, optimistic updates, AbortSignal wiring for all backend data (sessions, messages, documents) |
| Client state | **Zustand** (2 stores: auth, chat UI) | Only state that lives in the browser: token/user/auth status and UI state (citation panel, sidebar). Never holds server data |
| Forms | **React Hook Form** + **Zod** | Type-safe form validation mirroring backend Pydantic rules |
| Markdown Rendering | **react-markdown** + **remark-gfm** + **rehype-highlight** | Correctly renders tables, lists, code blocks in AI answers |
| HTTP Client | **Native fetch** with a centralized wrapper | No extra dependency; interceptors for auth headers & 401s |
| Package Manager | **npm** (Node 26.x available on machine) | Already installed; no extra tooling needed |

---

## 3. Project Structure

Location: `client/`

```
client/
├── src/
│   ├── app/
│   │   ├── globals.css                  # Tailwind v4 + shadcn theme tokens (ContextIQ dark palette)
│   │   ├── layout.tsx                   # Root layout: DM Sans font, theme-ready <html>, Toaster (inside Providers)
│   │   ├── providers.tsx                # Client providers: QueryClientProvider, auth bootstrap
│   │   ├── page.tsx                     # Root: redirect to /chat or /login
│   │   ├── login/
│   │   │   └── page.tsx                 # Login page
│   │   ├── register/
│   │   │   └── page.tsx                 # Registration page
│   │   └── (app)/                       # Route group: signed-in screens share one layout
│   │       ├── layout.tsx               # Suspense + RequireAuth + AppShell
│   │       ├── chat/
│   │       │   ├── page.tsx             # New chat: welcome screen + prompt suggestions
│   │       │   └── [sessionId]/
│   │       │       └── page.tsx         # Active conversation view
│   │       └── documents/
│   │           └── page.tsx             # Document management page
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx             # SidebarProvider: Sidebar | main content (fixed height)
│   │   │   ├── Sidebar.tsx              # shadcn Sidebar: logo, New Chat, nav, sessions, user menu
│   │   │   ├── SessionList.tsx          # Recent conversations (loading / error / empty states)
│   │   │   ├── Header.tsx               # Top bar: sidebar toggle (drawer on mobile), page title
│   │   │
│   │   ├── auth/
│   │   │   ├── AuthCard.tsx             # Shared centered card layout for auth pages
│   │   │   ├── LoginForm.tsx            # Email + password form
│   │   │   ├── RegisterForm.tsx         # Email + password + confirm form
│   │   │   ├── PasswordInput.tsx        # Input with show/hide toggle
│   │   │   └── RouteGuards.tsx          # RequireAuth, GuestOnly, RootRedirect
│   │   │
│   │   ├── chat/
│   │   │   ├── ConversationRoute.tsx    # Validates the route id (UUID), remounts per session
│   │   │   ├── ConversationView.tsx     # /chat/[id]: activate, history, follow-ups, 404, errors
│   │   │   ├── ChatContainer.tsx        # Message list + scroll-to-bottom manager
│   │   │   ├── ChatInput.tsx            # shadcn input-group: auto-growing textarea (≤6 rows) + send
│   │   │   ├── NewChatScreen.tsx        # /chat welcome screen + first-message flow
│   │   │   ├── MessageItem.tsx          # Renders user OR assistant message
│   │   │   ├── AssistantMessage.tsx     # 3 states; [S1] citation chips + "View sources" button
│   │   │   ├── MarkdownContent.tsx      # react-markdown + GFM + highlight (raw HTML not rendered)
│   │   │   ├── UserMessage.tsx          # User message bubble
│   │   │   ├── SuggestedPrompts.tsx     # Prompt cards on empty/new session
│   │   │   ├── TypingIndicator.tsx      # 3-dot pulse while awaiting backend response
│   │   │   ├── ClarificationBadge.tsx   # Visual indicator for needs_clarification=true
│   │   │   └── AbstentionAlert.tsx      # Info box for abstained=true responses
│   │   │
│   │   ├── sources/
│   │   │   ├── SourcesPanel.tsx         # 320px right panel (≥1024px) / slide-over drawer (below)
│   │   │   ├── CitationCard.tsx         # One source card: title, page, section, version, dates, freshness
│   │   │   ├── CitationChip.tsx         # Inline [S1] button that opens SourcesPanel
│   │   │   └── FreshnessBadge.tsx       # current / outdated / superseded / future (undated: none)
│   │   │
│   │   ├── documents/
│   │   │   ├── DocumentsView.tsx        # /documents: list, states, pagination, upload + delete dialogs
│   │   │   ├── DocumentTable.tsx        # List of uploaded docs with status & actions
│   │   │   ├── DocumentUploadZone.tsx   # Drag-and-drop + file picker, inline validation, upload
│   │   │   ├── UploadDocumentDialog.tsx # Upload modal (Documents page + "Attach document" in ChatInput)
│   │   │   ├── DocumentStatusBadge.tsx  # completed / processing / queued / failed badge
│   │   │   └── DeleteConfirmDialog.tsx  # Confirmation modal before deletion
│   │   │
│   │   ├── ui/                          # shadcn/ui generated components (kebab-case, do not hand-roll)
│   │   │   ├── button.tsx  input.tsx  label.tsx  form.tsx  textarea.tsx
│   │   │   ├── badge.tsx  card.tsx  dialog.tsx  alert-dialog.tsx  sheet.tsx
│   │   │   ├── tooltip.tsx  scroll-area.tsx  skeleton.tsx  separator.tsx
│   │   │   ├── table.tsx  dropdown-menu.tsx  avatar.tsx  sonner.tsx
│   │   │   ├── field.tsx  alert.tsx  spinner.tsx  sidebar.tsx  input-group.tsx
│   │   └── common/                      # Small app-specific primitives not provided by shadcn
│   │       ├── Logo.tsx
│   │       ├── PageLoader.tsx
│   │       └── EmptyState.tsx
│   │
│   ├── services/
│   │   ├── api.ts                       # Centralized fetch wrapper + auth interceptor
│   │   ├── auth.service.ts              # login(), register(), getProfile()
│   │   ├── chat.service.ts              # listSessions(), createSession(), getMessages(), sendMessage()
│   │   └── document.service.ts          # listDocuments(), uploadDocument(), deleteDocument(), getDetail()
│   │
│   ├── store/
│   │   ├── useAuthStore.ts              # status, token, user, initialize(), login(), logout()
│   │   └── useChatUiStore.ts            # activeCitationSourceId, sources panel + sidebar UI state
│   │
│   ├── hooks/
│   │   ├── queries/
│   │   │   ├── useSessions.ts           # sessions list, create, activate
│   │   │   ├── useMessages.ts           # message history + send (optimistic)
│   │   │   ├── useStartConversation.ts  # /chat: create session → send → navigate
│   │   │   └── useDocuments.ts          # list, detail, upload, delete
│   │   ├── useAuthGuard.ts              # Redirect to /login (protected) or /chat (guest pages)
│   │   ├── useCurrentSession.ts         # Route sessionId + its cached session
│   │   ├── useMediaQuery.ts             # Generic media-query hook (Sources panel breakpoint)
│   │   └── use-mobile.ts                # shadcn hook (rewritten with useSyncExternalStore)
│   │
│   ├── types/
│   │   ├── api.ts                       # Exact mirrors of backend Pydantic models
│   │   ├── chat.ts                      # UI-layer session & message types
│   │   └── document.ts                  # UI-layer document types
│   │
│   └── lib/
│       ├── query-client.ts              # QueryClient factory + defaults (retry, staleTime)
│       ├── query-keys.ts                # Single source of truth for query keys
│       ├── token-storage.ts             # localStorage token accessors (SSR-safe)
│       ├── jwt.ts                       # Read `exp` from the JWT to schedule auto-logout
│       ├── errors.ts                    # User-safe messages; inline vs toast classification
│       ├── validation/auth.ts           # Zod schemas for login/register
│       ├── chat.ts                      # deriveSessionTitle(), isValidSessionId()
│       ├── messages.ts                  # getAssistantMessageKind() (reads message metadata)
│       ├── citations.ts                 # rehype plugin: [S1] markers → chips; competing versions
│       ├── format.ts                    # formatDate() (date-only values in UTC)
│       ├── utils.ts                     # cn() helper (shadcn)
│       ├── documents.ts                 # Upload validation (extension, empty file), file type label
│       └── constants.ts                 # APP_NAME, SUPPORTED_FILE_EXTENSIONS, limits, DOCUMENTS_PAGE_SIZE
│
├── public/
│   └── logo.svg                         # ContextIQ brand logo
├── .env.example
├── .env.local                           # (git-ignored)
├── components.json                  # shadcn/ui configuration
├── next.config.ts
├── postcss.config.mjs               # @tailwindcss/postcss
├── eslint.config.mjs
├── tsconfig.json
└── package.json
```

---

## 4. API Integration Layer

### 4.1 Base URL
```
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 4.2 `services/api.ts` — Centralized Fetch Client
- Reads `process.env.NEXT_PUBLIC_API_BASE_URL` for base URL.
- Reads JWT token from `localStorage` on each call (never hardcoded).
- Automatically attaches `Authorization: Bearer <token>` to every request.
- On `401 Unauthorized` for an authenticated request: clears the stored token and calls the registered unauthorized handler (`useAuthStore.logout('expired')`); `useAuthGuard` then redirects to `/login`.
- Normalizes HTTP errors into typed `ApiError` objects with `status` and `message` fields.
- Never exposes raw backend stack traces to the user.

### 4.3 Service Modules

#### `auth.service.ts`
```ts
register(email, password)        → POST /auth/register        (JSON body)
login(email, password)           → POST /auth/token           (form-encoded: application/x-www-form-urlencoded)
getProfile()                     → GET  /auth/me
```

> **Important**: `/auth/token` uses OAuth2 form encoding, NOT JSON. The `email` field maps to the form field named `username`.

#### `chat.service.ts`
```ts
listSessions()                            → GET  /sessions
createSession(title)                      → POST /sessions
activateSession(sessionId)                → POST /sessions/{sessionId}/activate
getMessages(sessionId, limit?)            → GET  /sessions/{sessionId}/messages
sendMessage(sessionId, content, top_k?)   → POST /sessions/{sessionId}/messages
```

#### `document.service.ts`
```ts
listDocuments(params?)           → GET    /documents
getDocumentDetail(id)            → GET    /documents/{id}
uploadDocument(file: File)       → POST   /documents/upload   (multipart/form-data)
deleteDocument(id)               → DELETE /documents/{id}
```

---

## 5. TypeScript Types (Exact Backend Mirrors)

Located in `src/types/api.ts`:

```ts
// ─── Auth ────────────────────────────────────────────────────────────────────
export interface UserResponse {
  id: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;    // always "bearer"
  expires_in: number;    // always 1800 (seconds)
}

// ─── Sessions ─────────────────────────────────────────────────────────────────
export interface SessionResponse {
  id: string;
  user_id: string;
  title: string;            // 1–80 chars
  status: 'active' | 'archived';  // 'archived' = not the most recently used session; still readable
  created_at: string;
  updated_at: string;
  message_count: number;
}

// ─── Messages & Citations ──────────────────────────────────────────────────────
export type SourceFreshness =
  | 'current'     // within effective/expiry window
  | 'outdated'    // past expiry_date
  | 'superseded'  // a newer version of the document exists
  | 'future'      // effective_date is after today
  | 'undated';    // no effective/expiry date in metadata

export interface Citation {
  source_id: string;             // e.g. "S1", "S2"
  document_id: string;
  title: string;
  filename: string | null;
  page: number | null;           // Physical page number for PDFs; null for DOCX/TXT/MD
  chunk_index: number;
  section: string | null;        // Section heading for DOCX/Markdown
  version: string | null;
  effective_date: string | null; // ISO date from document metadata
  expiry_date: string | null;    // ISO date from document metadata
  as_of_date: string | null;     // Date freshness was evaluated against (request date)
  source_freshness: SourceFreshness | null;
  has_competing_versions: boolean;
  competing_versions: unknown[];
}

export interface MessageMetadata {
  message_type?: string;             // "question" for user messages
  needs_clarification?: boolean;     // true when assistant asks for clarification.
                                     // SOURCE OF TRUTH for rendering: the top-level
                                     // SendMessageResponse.needs_clarification is not
                                     // present when history is reloaded.
  retrieval_query?: string | null;   // the rewritten search query used by backend
  answer_reason?: string | null;     // reason for abstention if abstained
}

export interface MessageResponse {
  id: string;
  session_id: string;
  role: 'user' | 'assistant';
  content: string;
  citations: Citation[];
  abstained: boolean;
  metadata: MessageMetadata;
  created_at: string;
}

export interface SendMessageRequest {
  content: string;    // 1–8000 characters
  top_k?: number;     // default 5, min 1, max 20
}

export interface SendMessageResponse {
  session_id: string;
  user_message: MessageResponse;
  assistant_message: MessageResponse;
  retrieval_query: string | null;
  needs_clarification: boolean;
}

// ─── Documents ────────────────────────────────────────────────────────────────
export interface DocumentMetadata {
  title?: string;
  file_type?: string;
  department?: string;
  version?: string;
  effective_date?: string;
  expiry_date?: string;
  [key: string]: unknown;
}

export interface DocumentSummary {
  id: string;
  filename: string;
  status: 'completed' | 'processing' | 'failed';
  status_message: string | null;
  metadata: DocumentMetadata;
  created_at: string;
  updated_at: string;
  chunk_count: number;
}

export interface DocumentDetail extends DocumentSummary {
  file_hash: string;
  source_path: string | null;
  total_chars: number;
}

export interface DocumentListResponse {
  total: number;
  limit: number;
  offset: number;
  items: DocumentSummary[];
}

export interface DocumentUploadResponse {
  document_id: string;
  filename: string;
  status: string;
  chunk_count: number;
  message: string;
}

export interface DocumentDeleteResponse {
  document_id: string;
  deleted: boolean;
  message: string;
}
```

---

## 6. State Management

Server data is owned by **TanStack Query**; Zustand holds only browser state.
Components never call `services/*` directly: they use the hooks in `hooks/queries/`.

### 6.1 TanStack Query

**Provider**: `app/providers.tsx` (client component) wraps the app in
`QueryClientProvider`, one browser-wide `QueryClient` (a fresh one per server render).
Devtools render in development only.

**Defaults** (`lib/query-client.ts`):
- `staleTime: 30s`. Cached data is shown instantly when revisiting a screen, then refreshed.
- `retry`: never for 4xx or aborted requests; at most 1 retry for network/5xx errors.
- Mutations never retry (sending a message costs an LLM call).

**Query keys** (`lib/query-keys.ts`):
```
['auth', 'me']
['sessions']                          list
['sessions', id, 'messages']          history of one session
['documents', 'list', params]         paginated list
['documents', 'detail', id]
```

**Hooks** (`hooks/queries/`):

| Hook | Backend | Cache behaviour |
|---|---|---|
| `useSessionsQuery()` | `GET /sessions` | Sorted by `updated_at` desc; all statuses kept |
| `useCreateSession()` | `POST /sessions` | Inserts the new session into `['sessions']` |
| `useActivateSession()` | `POST /sessions/{id}/activate` | Invalidates `['sessions']` (statuses change) |
| `useMessagesQuery(id)` | `GET /sessions/{id}/messages` | **Disabled while a send for that session is in flight** (prevents the race below) |
| `useSendMessage(id)` | `POST /sessions/{id}/messages` | `onMutate`: appends an optimistic user message. `onSuccess`: replaces it with the server's `user_message` + `assistant_message`. `onError`: rolls back. `onSettled`: invalidates `['sessions']`. Definition shared via `sendMessageMutationOptions()` |
| `useStartConversation()` | `POST /sessions` then `POST /sessions/{id}/messages` | Creates the session, starts the send through a `MutationObserver` with the shared options (keeps running after `/chat` unmounts), navigates to `/chat/{id}` immediately |
| `useDocumentsQuery(params)` | `GET /documents` | Keeps previous page visible while paginating |
| `useDocumentDetailQuery(id)` | `GET /documents/{id}` | |
| `useUploadDocument()` | `POST /documents/upload` | Invalidates `['documents']` |
| `useDeleteDocument()` | `DELETE /documents/{id}` | Optimistically removes the row; rolls back on error; invalidates `['documents']` |

**First-message race**: when `/chat` creates a session and navigates to `/chat/[id]`,
the send mutation has already put the optimistic question into
`['sessions', id, 'messages']`. The `[id]` page's history query stays disabled while
that send is pending, so it cannot overwrite the in-flight question. When the send
succeeds, the cache already holds the complete history and is fresh, so no refetch is needed.

### 6.2 `useAuthStore` (Zustand)
```
State:
  status: 'initializing' | 'authenticated' | 'unauthenticated'
  token: string | null
  user: UserResponse | null

Actions:
  initialize()            → on app mount (client only): read stored token;
                            none or expired → unauthenticated;
                            else GET /auth/me → authenticated, or logout if invalid
  login(email, password)  → POST /auth/token, store token, GET /auth/me, authenticated
  logout(reason?)         → clear token + user, clear the whole query cache,
                            status = unauthenticated ('expired' also shows a toast)
```
- The API client's 401 handler is wired to `logout('expired')` (§4.2).
- A timer logs the user out when the JWT's `exp` passes (30 min), so an idle tab
  also returns to `/login` (acceptance checklist).
- Redirects are done by `useAuthGuard`, which reacts to `status`, not by the store.

### 6.3 `useChatUiStore` (Zustand)
```
State:
  activeCitationSourceId: string | null   ← which [SN] is highlighted
  activeCitationMessageId: string | null  ← which answer the citation belongs to
  sourcesPanelOpen: boolean

Actions:
  setActiveCitation(messageId, sourceId) → opens + scrolls the Sources panel
  closeSources(), reset()
```
Sidebar open/collapsed (desktop) and drawer (mobile) state is owned by the shadcn
`SidebarProvider`; the desktop preference persists in the `sidebar_state` cookie.
```
```

### 6.4 `useAuthGuard`
- Protected pages (`/chat`, `/chat/[id]`, `/documents`): render nothing while
  `initializing`; `router.replace('/login')` when `unauthenticated`.
- Guest pages (`/login`, `/register`): `router.replace('/chat')` when `authenticated`.
- Protected content (and therefore every query) renders only on the client after
  authentication is confirmed, so no query runs during Next.js prerendering.

---

## 7. Screen-by-Screen Specification

### 7.1 Login Page (`/login`)
- Email + password fields with client-side Zod validation.
- Calls `POST /auth/token` using `application/x-www-form-urlencoded`.
  - Form field names: `username` (= email value), `password`.
- On `200 OK`: save `access_token` to `localStorage`, call `GET /auth/me` to load user profile, redirect to `/chat`.
- On `401`: show inline error — *"Incorrect email or password."*
- Link to `/register`.

### 7.2 Register Page (`/register`)
- Fields: email, password, confirm password.
- Zod schema: valid email format, password 12+ characters, passwords must match.
- Calls `POST /auth/register` (JSON body: `{ email, password }`).
- On `201 Created`: auto-login via `POST /auth/token`, redirect to `/chat`.
- On `409 Conflict`: show inline error — *"An account with this email already exists."*
- Link to `/login`.

### 7.3 New Chat Page (`/chat`)
**Welcome / empty state screen.**
- Displays the ContextIQ logo mark + heading: **"A clearer way to work with your knowledge."**
- Sub-heading: *"Ask questions, explore your files, and get answers grounded in your documents."*
- 4 Suggested Prompt Cards in a 2×2 grid (one column on phones). Each shows a short label;
  clicking pre-fills the chat input with the start of a question to complete (caret at the end):
  1. "Summarize a document" → *"Summarize the main points of the document about "*
  2. "Find a specific detail" → *"Find where the documents mention "*
  3. "Compare two documents" → *"Compare what the documents say about "*
  4. "Explain a key concept" → *"Explain the concept of "*
- `ChatInput` pinned at the bottom (max width 672px on this screen).
- **First message send flow**:
  1. `POST /sessions` with `title = content.slice(0, 50)` (backend max: 80 chars).
  2. `useSendMessage(session.id).mutate(content)`: adds the optimistic user bubble to the session's message cache, shows `TypingIndicator`, and starts `POST /sessions/{id}/messages`.
  3. `router.push('/chat/' + session.id)`, with no full reload.
  4. The `/chat/[sessionId]` page sees the pending send for this session: its history query stays disabled and it skips the activate call (the send activates the session server-side). See §6.1, "First-message race".

### 7.4 Active Chat Page (`/chat/[sessionId]`)
- On mount (skipped while a send for this session is pending, see §7.3):
  1. `POST /sessions/{sessionId}/activate`: activate this session (the backend sets the user's other sessions to `archived`).
  2. `GET /sessions/{sessionId}/messages`: load history.
  3. Auto-scroll to bottom.
  4. On `404` → toast "Conversation not found." and redirect to `/chat`.
     A malformed (non-UUID) id gets the same treatment without a request: the backend
     answers malformed ids with `422`, not `404`.
- Renders all messages chronologically.

**User message bubble**: slate-800 background, full content text.

**Assistant message bubble** (3 possible states). Read the flags from the **message itself** (`message.metadata.needs_clarification`, `message.abstained`), never from the top-level send response, so live and reloaded history render the same way:

| `metadata.needs_clarification` | `abstained` | UI treatment |
|---|---|---|
| `false` | `false` | Markdown content + clickable `[S1]` citation chips |
| `true` | `false` | Blue left-border card — assistant is asking for clarification; no citations |
| `false` | `true` | Amber info box: *"The knowledge base did not contain enough information to answer this question."* |

**ChatInput behaviour**:
- Auto-resizing textarea; grows up to 6 visible rows, then scrolls.
- `Enter` → send message.
- `Shift+Enter` → insert newline.
- Disabled (and dimmed) while `isSending === true`; an empty question only disables the send button.
- Bottom row: **"+ Attach document"** (left) opens the upload dialog (§7.7; the file joins the
  shared knowledge base) and the square send button (right). Character counter near the limit.
- Disclaimer under the box: *"ContextIQ can make mistakes. Verify important information in the cited source."*
- "Answer from selected sources" (in the design mockup) is **not** implemented: the backend's
  `SendMessageRequest` has no source filter.
- Clear input after successful submission.
- Loading state → `TypingIndicator` (3-dot pulse animation) appended to message list.

**No simulated streaming**. The backend returns a complete JSON response. Never animate character-by-character output.

### 7.5 Sidebar
Built on the shadcn `sidebar` component (`collapsible="icon"`), with `Ctrl/⌘+B` to toggle.
- **Logo area**: ContextIQ icon (filled `primary` square) + wordmark, aligned with the 64px header.
- **New chat** (plain navigation row with a `+` icon, not a filled button) → navigates to `/chat`; calls `useChatUiStore.reset()`.
- **"RECENT"** conversations list (small uppercase label):
  - Loaded from `GET /sessions` on sidebar mount.
  - Sorted by `updated_at` descending.
  - Show **all** sessions regardless of `status`. The backend automatically sets every non-current session to `archived` on activate, so filtering by `status === 'active'` would hide all past chats.
  - Shows the session title only (muted text, no icon or message count), truncated with "…".
  - Active session: grey (`sidebar-accent`) row background, based on the current route `sessionId` (not on `status`).
  - Click → `router.push('/chat/' + session.id)`.
- **Navigation**:
  - 📄 Documents → `/documents`
  - No separate "Chat" item: it duplicated **New Chat** and the conversation list, which already lead to the chat pages.
- **Bottom**:
  - User email (from `useAuthStore.user.email`) with an initial avatar; the backend has no
    display name, so the mockup's name/"workspace" lines are not shown.
  - Menu: **Theme** (Light / Dark / System) and Log out.
  - Logout button → `useAuthStore.logout()`.
- **Collapsible** on desktop (icon-only 64px mode).
- **Mobile**: hidden behind hamburger button in `Header`; opens as a slide-over drawer.

### 7.6 Sources Panel (Right Side)
- **Visible**: only after the user opens it, and only for an answer with `citations.length > 0`.
  It shows the sources of one answer at a time; it is rendered by `ConversationView`
  (which owns the messages), not by `AppShell`.
- **Desktop (≥1024px)**: Fixed right panel (320px), alongside the chat. Close button or `Esc`.
  (Below 1024px a 320px panel would squeeze the chat, so the drawer is used instead.)
- **Smaller screens**: slide-over drawer from the right (shadcn `sheet`).
- Every answer with citations has a **"View sources (n)"** button under it (all screen sizes).
- Clicking `[S1]` in the chat → `useChatUiStore.setActiveCitation(messageId, 'S1')` → panel opens + scrolls to that `CitationCard`.
- Only markers matching the message's `citations` become chips; unknown markers and
  markers inside code stay plain text.
- Switching conversations closes the panel.

**CitationCard** content:
- `[S1]` label badge (indigo).
- Document filename.
- Page number (PDFs) or Section heading (Markdown/DOCX).
- Version + as_of_date if available.
- **Source Freshness Badge**:
  - `current` → Green: "Current"
  - `outdated` → Amber: "Outdated — newer version may exist"
  - `superseded` → Red: "Superseded"
  - `future` → Blue: "Not yet effective"
  - `undated` / `null` → no badge
- Show `effective_date` / `expiry_date` when present (formatted, e.g. "Jan 1, 2026").
- Document title (from metadata, falls back to the filename) above the filename.
- When `has_competing_versions`, list `competing_versions` ("Versions found: …"; the
  backend sends version labels such as `"2 (effective 2025-06-01)"`).

> Note: Retrieved chunk text snippets are NOT returned by the messages API and will NOT be shown.

### 7.7 Document Management Page (`/documents`)
- Page heading: **"Knowledge Base"** (the header title), with a "Documents" section heading and a
  subtitle saying the documents are shared by all users, plus the document count.
- Calls `GET /documents` on mount, 50 per page (`DOCUMENTS_PAGE_SIZE`; backend max 200), with
  Previous/Next when there are more. The list refreshes every 5 s while any document is
  `queued` or `processing`.
- Loading skeleton; load error → message + "Try again" (raw backend detail never shown).

**Empty state** (zero documents):  
Document icon + *"No documents yet. Upload your first document to get started."* + Upload button.

**Document Table** columns:
- File type icon (by extension: PDF, DOCX, TXT, Markdown)
- Filename (from `DocumentSummary.filename`)
- Status badge: `completed` (green), `processing` (yellow + spinner), `queued` (grey), `failed` (red;
  `status_message` shown under the filename)
- Chunk count
- Uploaded date (formatted as "Nov 18, 2026")
- Delete button (trash icon)
- Below 640px the status, chunks and date move under the filename (only Document + delete columns).

**Upload Document**:
- Triggered by the page button or "Attach document" in the chat input → opens `UploadDocumentDialog` (`DocumentUploadZone` in a modal). One file at a time.
- Drag-and-drop area OR click to pick file.
- **Supported extensions** (enforced client-side before upload): `.pdf`, `.docx`, `.txt`, `.md`, `.markdown`.
- Validation before sending:
  - Reject unsupported extension → inline error in the dialog (§9): *"Only PDF, DOCX, TXT, and Markdown files are supported."*
  - Reject 0-byte file → inline error: *"The selected file is empty."*
  - No client-side size limit (the backend has none).
- Calls `POST /documents/upload` as `multipart/form-data` with form field name `file`.
- Shows loading spinner during upload. The backend indexes the file inside the request, so the
  dialog cannot be closed until it finishes (the result is reported there).
- On success: show success toast with `message` from response, refresh document list.
- On `422` from backend: toast with the backend `detail` message; the dialog stays open.
- On `500`: toast *"Document upload failed. Please try a different file."*

**Delete Document**:
- Click trash icon → `DeleteConfirmDialog` modal.
- Modal text: *"Delete [filename]? This will remove the document and all its indexed chunks from the shared knowledge base for all users. This cannot be undone."*
- **Confirm** → `DELETE /documents/{id}` → remove from list locally at once (restored if the
  delete fails) + show success toast. `404` → toast "Document not found." and the list resyncs.
  Deleting the only row of the last page goes back one page.
- **Cancel** → close modal.

---

## 8. Visual Design Decisions

### 8.1 Color Tokens
These values are mapped onto the shadcn/ui semantic tokens (`--background`, `--card`,
`--border`, `--primary`, `--muted-foreground`, `--destructive`, ...) in `globals.css`,
plus custom `--success` / `--warning` / `--info` tokens. Components use the semantic
classes (`bg-background`, `text-muted-foreground`, `bg-primary`), never raw palette classes.
**Two themes** (switched from the user menu, §8.4):

*Light (default, from the design mockup)* — monochrome: white background, sidebar and cards;
near-black `primary` (buttons, logo mark, active citation chip); neutral grey borders
(`oklch(0.922 0 0)`), muted text and hover rows. Status colours: green / amber / red / blue (600 shades).

*Dark (opt-in)* — the original palette:
```
Background:         slate-950   (main app background)
Surface (cards):    slate-900   (sidebar, panels, message bubbles)
Border:             slate-800
Accent Primary:     indigo-500  (buttons, active states, links)
Accent Hover:       indigo-600
Text Primary:       slate-50
Text Muted:         slate-400
Success:            green-500   (completed status, current freshness)
Warning:            amber-500   (outdated freshness, abstention box)
Danger:             red-500     (failed status, superseded freshness, delete)
```

### 8.1a Logo
Source: `client/src/assets/ContextIQ_Logo.png`. Derived transparent PNGs (light + dark copies):
`logo-full-*` (mark + "ContextIQ" + tagline) on sign-in/register; `logo-wordmark-*` (no tagline)
in the expanded sidebar; `logo-mark*` (the "C" with three dots, no sparkles) in the collapsed rail,
the welcome screen, the assistant avatar and `app/favicon.ico`. `components/common/Logo.tsx`
renders both theme copies and shows one with `dark:` classes (correct on first paint).

### 8.2 Layout Dimensions
- **Sidebar**: 260px expanded / 64px collapsed (icon-only)
- **Sources Panel**: 320px fixed right (desktop)
- **Chat content**: Remaining width; messages max-width 768px centered
- **Chat input bar**: Sticky bottom; full chat area width

### 8.3 Typography
- Font: **DM Sans** (via `next/font/google`, `--font-sans`), matching the design mockup; Geist Mono for code
- Headings: `font-semibold`, `tracking-tight`
- Body/messages: `text-sm` (sidebar) / `text-base` (chat), `leading-relaxed`
- Code blocks inside AI answers: `font-mono`, `bg-muted`, `text-foreground`, rounded (readable in both themes)
- Header title: `text-lg font-semibold` in a 64px header

### 8.4 Interaction Rules
- Transitions: `150ms ease-out` maximum — no heavy animations.
- **Themes**: light by default; Light / Dark / System in the user menu (`next-themes`,
  `attribute="class"`, saved in localStorage under `contextiq.theme`, applied to `<html>`
  before first paint so there is no flash). Components use semantic tokens only, so both
  themes come from `globals.css`; anything theme-specific uses the `dark:` variant
  (e.g. `dark:prose-invert` for answers).
- Hover states: `hover:bg-accent` on interactive list items.
- Focus rings: `focus-visible:ring-2 focus-visible:ring-ring`.
- No excessive gradients — solid fills only.
- No decorative illustration overload.

---

## 9. Error Handling Matrix

| Scenario | User-Facing Message | UI Treatment |
|---|---|---|
| Backend unreachable (network error) | "Could not connect to the ContextIQ server. Please try again." | Toast (destructive) |
| `401 Unauthorized` on any request | "Your session has expired. Please sign in again." | Auto logout + redirect `/login` |
| `404` on session | "Conversation not found." | Error state; redirect to `/chat` |
| Login `401` | "Incorrect email or password." | Inline form error |
| Register `409` | "An account with this email already exists." | Inline form error |
| Upload unsupported extension | "Only PDF, DOCX, TXT, and Markdown files are supported." | Inline file picker error |
| Upload empty file | "The selected file is empty." | Inline file picker error |
| Upload `422` from backend | Show backend `detail` field verbatim (safe, generated by our code) | Toast |
| Upload `500` from backend | "Document upload failed. Please try a different file." | Toast |
| Delete `404` | "Document not found." | Toast |
| `abstained: true` answer | "The knowledge base did not contain enough information to answer this question." | Amber info box in chat |
| `metadata.needs_clarification: true` | Display AI's clarification question as-is | Blue-border message bubble |
| AI generation error `502` | "The AI service is temporarily unavailable. Please try again." | Toast |
| TypeScript/parse error on response | Show raw text as fallback | Silent fallback; never crash |

---

## 10. Features Explicitly OUT of Scope

The following features will **NOT** be implemented because the backend does not expose corresponding REST endpoints:

| Feature | Reason Excluded |
|---|---|
| Ragas Evaluation Dashboard | CLI-only. No `/evaluation` REST API. |
| Document Reindexing via UI | CLI-only (`python -m app.main reindex <id>`). No REST endpoint. |
| Streaming AI responses | Backend returns complete JSON. No SSE or WebSocket endpoint. No fake streaming. |
| Document metadata editing | No `PATCH /documents/{id}` endpoint. |
| Session deletion or archiving | No `DELETE /sessions/{id}` or archive endpoint. |
| File download of original document | No `/documents/{id}/download` endpoint. |
| Search without a session | No stateless `/search` or `/ask` endpoint. All queries belong to a session. |
| Light mode toggle | Out of scope for this release. |
| Per-user document libraries / permissions | Backend has no document ownership; all documents are shared by all users. |

---

## 11. Environment Configuration

### `client/.env.example`
```bash
# Backend API URL — change this for staging or production deployments
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### `client/.env.local` (developer local, git-ignored)
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

> **Security rule**: Never put secret keys or private tokens in `NEXT_PUBLIC_*` variables. Only the API base URL is needed in the frontend environment.

---

## 12. Startup Commands

### Backend (must be running first)
```bash
# From the repository root: start PostgreSQL
scripts/compose.sh up -d postgres

# Activate the backend virtual environment
cd server
source .venv/bin/activate        # or: source ../venv/bin/activate

# Start API server
uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```
API Docs live at: `http://localhost:8000/docs`

### Frontend
```bash
cd client

# Install dependencies (first time only)
npm install

# Start development server
npm run dev
# → Runs on http://localhost:3000

# TypeScript type check
npm run type-check

# Production build
npm run build && npm start
```

---

## 13. Implementation Phases (Execution Order)

| Phase | Deliverable | Key Files |
|---|---|---|
| **1** | Next.js scaffold, Tailwind v4, shadcn/ui init + base components, ContextIQ theme, `.env.example` | `package.json`, `components.json`, `tsconfig.json`, `app/globals.css`, `components/ui/*` |
| **2** | TypeScript types, API client, 3 service modules | `types/api.ts`, `services/api.ts`, `auth.service.ts`, `chat.service.ts`, `document.service.ts` |
| **3** | TanStack Query provider, query keys + hooks; Zustand auth + chat UI stores; auth guard | `app/providers.tsx`, `lib/query-*.ts`, `hooks/queries/*`, `store/*.ts`, `hooks/useAuthGuard.ts` |
| **4** | Login + Register pages (React Hook Form + Zod + shadcn `field`), root redirect, temporary protected `/chat` | `app/login/page.tsx`, `app/register/page.tsx`, `app/page.tsx`, `components/auth/`, `lib/validation/auth.ts` |
| **5** | App shell (shadcn `sidebar`) + Header + real session list; `(app)` route group | `app/(app)/layout.tsx`, `components/layout/*`, `hooks/useCurrentSession.ts` |
| **6** | New Chat welcome screen, suggested prompts, `ChatInput`, first-message flow | `app/(app)/chat/page.tsx`, `components/chat/{NewChatScreen,SuggestedPrompts,ChatInput}.tsx`, `hooks/queries/useStartConversation.ts` |
| **7** | Active chat page (all 3 assistant states), markdown, follow-ups, scroll manager | `app/(app)/chat/[sessionId]/page.tsx`, `components/chat/*`, `lib/messages.ts` |
| **8** | Sources panel + inline citation chips + freshness badges | `components/sources/` |
| **9** | Document management page (table, upload, delete) | `app/documents/page.tsx`, `components/documents/` |
| **10** | End-to-end testing against live backend, TypeScript cleanup, responsive polish | All files |

---

## 14. Acceptance Checklist (Definition of Done)

Before the frontend is considered complete, every item below must be verified against the **live backend**:

**Authentication**
- [ ] User can register a new account via `/register`.
- [ ] User can log in and receives a JWT token stored in `localStorage`.
- [ ] Unauthenticated users on any protected route are redirected to `/login`.
- [ ] Token expiry (after 30 min) triggers automatic logout + redirect to `/login`.

**Documents**
- [ ] User can upload a `.pdf` document from the Documents page.
- [ ] Uploaded document appears in the table with `completed` status and correct chunk count.
- [ ] Upload of unsupported extension (e.g. `.png`) shows a clear client-side error.
- [ ] Upload of an empty file shows a clear client-side error.
- [ ] User can delete a document with the confirmation dialog.
- [ ] Deleted document disappears from the list immediately.
- [ ] Documents page and delete dialog clearly state that the knowledge base is shared.

**Chat & Sessions**
- [ ] User can start a new chat from the sidebar.
- [ ] New chat screen shows ContextIQ welcome and 4 suggested prompts.
- [ ] Sending the first question automatically creates a session and navigates to `/chat/[id]`.
- [ ] The new session appears in the sidebar "Recent Chats" list.
- [ ] User can click a previous session in the sidebar and load its message history.
- [ ] Previously used (`archived`) sessions remain visible in the sidebar.
- [ ] The first question in a new chat is never lost or duplicated during the `/chat` → `/chat/[id]` navigation.
- [ ] Loading state (TypingIndicator) shows while backend is processing.

**AI Responses**
- [ ] AI answer with citations renders with inline `[S1]`, `[S2]` chips.
- [ ] Clarification responses (`metadata.needs_clarification: true`) show the blue left-border indicator, both live and after page reload.
- [ ] Abstention responses (`abstained: true`) show the amber info box.
- [ ] Markdown in AI answers renders correctly (headings, bold, lists, code).

**Sources Panel**
- [ ] Clicking `[S1]` opens the sources panel.
- [ ] Citation card shows correct filename, page/section information.
- [ ] `outdated`, `superseded` and `future` citations show correct colored freshness badges; `undated` shows none.

**Quality**
- [ ] TypeScript compiles with zero errors (`npm run type-check`).
- [ ] No browser console errors during normal use.
- [ ] Layout is functional on mobile (375px viewport).
- [ ] No hardcoded mock data or fake responses anywhere in production code.
- [ ] No raw backend error messages or stack traces shown to the user.
