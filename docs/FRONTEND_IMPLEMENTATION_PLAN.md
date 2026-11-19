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
| Framework | **Next.js 14+** (App Router) | SSR + file-based routing + API routes if needed |
| Language | **TypeScript** (strict mode) | Type safety aligned with Pydantic backend models |
| Styling | **Tailwind CSS** | Utility-first; pairs perfectly with shadcn/ui primitives |
| Component Library | **Radix UI** primitives + custom Tailwind components | Accessible, headless; avoids heavy opinionated libraries |
| Icons | **lucide-react** | Already in shadcn ecosystem; clean and consistent |
| State | **Zustand** (3 stores: auth, chat, documents) | Lightweight; shared state only where genuinely needed |
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
│   │   ├── layout.tsx                   # Root layout: ThemeProvider, AuthGuard
│   │   ├── page.tsx                     # Root: redirect to /chat or /login
│   │   ├── login/
│   │   │   └── page.tsx                 # Login page
│   │   ├── register/
│   │   │   └── page.tsx                 # Registration page
│   │   ├── chat/
│   │   │   ├── page.tsx                 # New chat: welcome screen + prompt suggestions
│   │   │   └── [sessionId]/
│   │   │       └── page.tsx             # Active conversation view
│   │   └── documents/
│   │       └── page.tsx                 # Document management page
│   │
│   ├── components/
│   │   ├── layout/
│   │   │   ├── AppShell.tsx             # 3-panel coordinator: Sidebar | Chat | Sources
│   │   │   ├── Sidebar.tsx              # Left sidebar: logo, New Chat, session list, nav
│   │   │   └── Header.tsx               # Top bar: session title, mobile menu button
│   │   │
│   │   ├── auth/
│   │   │   ├── LoginForm.tsx            # Email + password form
│   │   │   └── RegisterForm.tsx         # Email + password + confirm form
│   │   │
│   │   ├── chat/
│   │   │   ├── ChatContainer.tsx        # Message list + scroll-to-bottom manager
│   │   │   ├── ChatInput.tsx            # Multiline textarea + send button
│   │   │   ├── MessageItem.tsx          # Renders user OR assistant message
│   │   │   ├── AssistantMessage.tsx     # Markdown + inline [S1] citation chips
│   │   │   ├── UserMessage.tsx          # User message bubble
│   │   │   ├── SuggestedPrompts.tsx     # Prompt cards on empty/new session
│   │   │   ├── TypingIndicator.tsx      # Skeleton while awaiting backend response
│   │   │   ├── ClarificationBadge.tsx   # Visual indicator for needs_clarification=true
│   │   │   └── AbstentionAlert.tsx      # Info box for abstained=true responses
│   │   │
│   │   ├── sources/
│   │   │   ├── SourcesPanel.tsx         # Right panel / mobile drawer
│   │   │   ├── CitationCard.tsx         # One source card: title, page, section, freshness
│   │   │   └── CitationChip.tsx         # Inline [S1] badge that opens SourcesPanel
│   │   │
│   │   ├── documents/
│   │   │   ├── DocumentTable.tsx        # List of uploaded docs with status & actions
│   │   │   ├── DocumentUploadZone.tsx   # Drag-and-drop + file picker
│   │   │   ├── DocumentStatusBadge.tsx  # completed / processing / failed badge
│   │   │   └── DeleteConfirmDialog.tsx  # Confirmation modal before deletion
│   │   │
│   │   └── ui/
│   │       ├── Button.tsx
│   │       ├── Input.tsx
│   │       ├── Badge.tsx
│   │       ├── Dialog.tsx
│   │       ├── Tooltip.tsx
│   │       ├── Spinner.tsx
│   │       └── EmptyState.tsx
│   │
│   ├── services/
│   │   ├── api.ts                       # Centralized fetch wrapper + auth interceptor
│   │   ├── auth.service.ts              # login(), register(), getProfile()
│   │   ├── chat.service.ts              # listSessions(), createSession(), getMessages(), sendMessage()
│   │   └── document.service.ts          # listDocuments(), uploadDocument(), deleteDocument(), getDetail()
│   │
│   ├── store/
│   │   ├── useAuthStore.ts              # user, token, isAuthenticated, logout()
│   │   ├── useChatStore.ts              # sessions, currentSession, messages, activeCitationSourceId
│   │   └── useDocumentStore.ts          # documents, uploadStatus, pagination
│   │
│   ├── hooks/
│   │   ├── useSession.ts                # Load session & history on mount; handle first message
│   │   ├── useDocuments.ts              # Fetch, upload, delete documents
│   │   └── useAuthGuard.ts              # Redirect to /login if no valid token
│   │
│   ├── types/
│   │   ├── api.ts                       # Exact mirrors of backend Pydantic models
│   │   ├── chat.ts                      # UI-layer session & message types
│   │   └── document.ts                  # UI-layer document types
│   │
│   ├── lib/
│   │   ├── utils.ts                     # classnames helper (cn), date formatters
│   │   └── constants.ts                 # APP_NAME, SUPPORTED_FILE_TYPES, MAX_FILE_SIZE
│   │
│   └── styles/
│       └── globals.css                  # Tailwind base + ContextIQ CSS variables
│
├── public/
│   └── logo.svg                         # ContextIQ brand logo
├── .env.example
├── .env.local                           # (git-ignored)
├── next.config.ts
├── tailwind.config.ts
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
- On `401 Unauthorized`: clears token from storage, dispatches logout in `useAuthStore`, and redirects to `/login`.
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

### 6.1 `useAuthStore` (Zustand)
```
State:
  user: UserResponse | null
  token: string | null
  isAuthenticated: boolean

Actions:
  login(token, user)      → store token in localStorage; set state
  logout()                → clear localStorage; clear state; redirect /login
  checkAuth()             → on app mount: validate stored token via GET /auth/me
                            if valid: restore user state
                            if invalid/expired: auto logout
```

### 6.2 `useChatStore` (Zustand)
```
State:
  sessions: SessionResponse[]
  currentSessionId: string | null
  messages: MessageResponse[]
  pendingMessage: { sessionId: string; content: string } | null   ← in-flight question (optimistic)
  isSending: boolean
  activeCitationSourceId: string | null   ← which [SN] is highlighted in Sources panel

Actions:
  loadSessions()                  → GET /sessions
  setCurrentSession(id)           → updates currentSessionId + loads messages
  loadMessages(sessionId)         → GET /sessions/{id}/messages
                                    must NOT clear/overwrite while pendingMessage.sessionId === sessionId;
                                    merge server history with the optimistic message instead
  sendMessage(sessionId, content) → set pendingMessage + isSending, POST /sessions/{id}/messages,
                                    then append user_message + assistant_message and clear pendingMessage
  appendMessage(message)          → adds message to messages array locally
  setActiveCitation(sourceId)     → opens + scrolls Sources panel
  clearChat()                     → reset messages + currentSessionId
```

### 6.3 `useDocumentStore` (Zustand)
```
State:
  documents: DocumentSummary[]
  total: number
  isLoading: boolean
  isUploading: boolean
  error: string | null

Actions:
  fetchDocuments(params?)         → GET /documents
  uploadDocument(file: File)      → POST /documents/upload
  deleteDocument(id)              → DELETE /documents/{id}; refresh list
```

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
- Displays ContextIQ logo + heading: **"What would you like to know?"**
- Sub-heading: *"Ask questions about your documents and get AI-powered answers with cited sources."*
- 4 Suggested Prompt Cards (clicking pre-fills chat input):
  1. "Summarize the main points of an uploaded document"
  2. "What is the company leave and attendance policy?"
  3. "Explain the key terms in the uploaded agreement"
  4. "What are the latest guidelines for remote work?"
- Prominent `ChatInput` at the bottom.
- **First message send flow**:
  1. `POST /sessions` with `title = content.slice(0, 50)` (backend max: 80 chars).
  2. `useChatStore.sendMessage(session.id, content)`: sets `pendingMessage`, shows the optimistic user bubble and `TypingIndicator`, and starts `POST /sessions/{id}/messages`.
  3. `router.push('/chat/' + session.id)`, with no full reload.
  4. The `/chat/[sessionId]` page sees `pendingMessage` for this session and **skips** its mount-time activate and history fetch (the session is brand new and the send call activates it server-side). This avoids a race where the history fetch overwrites the in-flight question.

### 7.4 Active Chat Page (`/chat/[sessionId]`)
- On mount (skipped if `pendingMessage.sessionId === sessionId`, see §7.3):
  1. `POST /sessions/{sessionId}/activate`: activate this session (the backend sets the user's other sessions to `archived`).
  2. `GET /sessions/{sessionId}/messages`: load history.
  3. Auto-scroll to bottom.
  4. On `404` → toast "Conversation not found." and redirect to `/chat`.
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
- Disabled while `isSending === true`.
- Clear input after successful submission.
- Loading state → `TypingIndicator` (3-dot pulse animation) appended to message list.

**No simulated streaming**. The backend returns a complete JSON response. Never animate character-by-character output.

### 7.5 Sidebar
- **Logo area**: ContextIQ wordmark + icon.
- **New Chat button** → navigates to `/chat`; calls `useChatStore.clearChat()`.
- **Recent Conversations** list:
  - Loaded from `GET /sessions` on sidebar mount.
  - Sorted by `updated_at` descending.
  - Show **all** sessions regardless of `status`. The backend automatically sets every non-current session to `archived` on activate, so filtering by `status === 'active'` would hide all past chats.
  - Shows: session title + message count badge.
  - Active session: indigo left border highlight, based on the current route `sessionId` (not on `status`).
  - Click → `router.push('/chat/' + session.id)`.
- **Navigation**:
  - 💬 Chat → `/chat`
  - 📄 Documents → `/documents`
- **Bottom**:
  - User email (from `useAuthStore.user.email`).
  - Logout button → `useAuthStore.logout()`.
- **Collapsible** on desktop (icon-only 64px mode).
- **Mobile**: hidden behind hamburger button in `Header`; opens as a slide-over drawer.

### 7.6 Sources Panel (Right Side)
- **Visible**: only when `currentSession` has an assistant message with `citations.length > 0`.
- **Desktop**: Fixed right panel (320px), appears alongside the chat.
- **Mobile**: Bottom sheet / slide-over drawer, triggered by **"View Sources"** button in the assistant message footer.
- Clicking `[S1]` in the chat → `useChatStore.setActiveCitation('S1')` → panel opens + scrolls to that `CitationCard`.

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
- Show `effective_date` / `expiry_date` when present.

> Note: Retrieved chunk text snippets are NOT returned by the messages API and will NOT be shown.

### 7.7 Document Management Page (`/documents`)
- Page heading: **"Knowledge Base"**, with a subtitle saying the documents are shared by all users.
- Calls `GET /documents` on mount.

**Empty state** (zero documents):  
Document icon + *"No documents yet. Upload your first document to get started."* + Upload button.

**Document Table** columns:
- File type icon (by extension: PDF, DOCX, TXT, Markdown)
- Filename (from `DocumentSummary.filename`)
- Status badge: `completed` (green), `processing` (yellow + spinner), `failed` (red)
- Chunk count
- Uploaded date (formatted as "Nov 18, 2026")
- Delete button (trash icon)

**Upload Document**:
- Triggered by button → opens `DocumentUploadZone` (modal overlay or inline).
- Drag-and-drop area OR click to pick file.
- **Supported extensions** (enforced client-side before upload): `.pdf`, `.docx`, `.txt`, `.md`, `.markdown`.
- Validation before sending:
  - Reject unsupported extension → error toast: *"Only PDF, DOCX, TXT, and Markdown files are supported."*
  - Reject 0-byte file → error toast: *"The selected file is empty."*
- Calls `POST /documents/upload` as `multipart/form-data` with form field name `file`.
- Shows loading spinner during upload.
- On success: show success toast with `message` from response, refresh document list.
- On `422` from backend: show backend `detail` message.
- On `500`: show *"Document upload failed. Please try a different file."*

**Delete Document**:
- Click trash icon → `DeleteConfirmDialog` modal.
- Modal text: *"Delete [filename]? This will remove the document and all its indexed chunks from the shared knowledge base for all users. This cannot be undone."*
- **Confirm** → `DELETE /documents/{id}` → remove from list locally + show success toast.
- **Cancel** → close modal.

---

## 8. Visual Design Decisions

### 8.1 Color Tokens
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

### 8.2 Layout Dimensions
- **Sidebar**: 260px expanded / 64px collapsed (icon-only)
- **Sources Panel**: 320px fixed right (desktop)
- **Chat content**: Remaining width; messages max-width 768px centered
- **Chat input bar**: Sticky bottom; full chat area width

### 8.3 Typography
- Font: **Inter** (via `next/font/google`)
- Headings: `font-semibold`, `tracking-tight`
- Body/messages: `text-sm` (sidebar) / `text-base` (chat), `leading-relaxed`
- Code blocks inside AI answers: `font-mono`, `bg-slate-800`, rounded

### 8.4 Interaction Rules
- Transitions: `150ms ease-out` maximum — no heavy animations.
- **Dark mode only** in this release. Light mode is a future enhancement.
- Hover states: `hover:bg-slate-800` on interactive list items.
- Focus rings: `focus-visible:ring-2 focus-visible:ring-indigo-500`.
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
| **1** | Next.js scaffold, Tailwind setup, folder structure, `.env.example` | `package.json`, `tailwind.config.ts`, `tsconfig.json`, `globals.css` |
| **2** | TypeScript types, API client, 3 service modules | `types/api.ts`, `services/api.ts`, `auth.service.ts`, `chat.service.ts`, `document.service.ts` |
| **3** | Zustand stores + auth guard hook | `store/*.ts`, `hooks/useAuthGuard.ts` |
| **4** | Login + Register pages with form validation | `app/login/page.tsx`, `app/register/page.tsx`, `components/auth/` |
| **5** | App Shell + Sidebar + Header (with real session list) | `components/layout/AppShell.tsx`, `Sidebar.tsx`, `Header.tsx` |
| **6** | New Chat welcome screen + suggested prompts | `app/chat/page.tsx`, `components/chat/SuggestedPrompts.tsx` |
| **7** | Active chat page (all 3 assistant states) | `app/chat/[sessionId]/page.tsx`, all `components/chat/` |
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
