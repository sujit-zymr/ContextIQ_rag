/**
 * Exact mirrors of the backend's Pydantic models.
 *
 * Sources:
 *   server/app/api/schemas.py           (auth, sessions, messages)
 *   server/app/api/document_schemas.py  (documents)
 *   server/app/generation/answerer.py   (citation objects)
 *   server/app/retrieval/versioning.py  (source freshness values)
 *
 * UUIDs and datetimes are serialized by FastAPI as strings (ISO 8601 for datetimes).
 */

// ─── Auth ────────────────────────────────────────────────────────────────────

export interface UserResponse {
  id: string;
  email: string;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  /** Always "bearer". */
  token_type: string;
  /** Lifetime in seconds (1800 = 30 minutes). */
  expires_in: number;
}

export interface RegisterRequest {
  email: string;
  /** 12–128 characters. */
  password: string;
}

// ─── Sessions ────────────────────────────────────────────────────────────────

/**
 * `active` marks the user's most recently used session. Activating a session
 * sets every other session to `archived`; archived sessions remain readable
 * and must still be listed in the UI.
 */
export type SessionStatus = "active" | "archived";

export interface SessionResponse {
  id: string;
  user_id: string;
  /** 1–80 characters. */
  title: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface SessionCreateRequest {
  /** Optional, defaults to "New chat" on the server. 1–80 characters. */
  title?: string;
}

// ─── Messages & citations ────────────────────────────────────────────────────

export type SourceFreshness =
  /** Within the effective/expiry window. */
  | "current"
  /** Past `expiry_date`. */
  | "outdated"
  /** A newer version of the same document exists. */
  | "superseded"
  /** `effective_date` is after today. */
  | "future"
  /** No effective/expiry date in the document metadata. */
  | "undated";

export interface Citation {
  /** Marker used in the answer text, e.g. "S1". */
  source_id: string;
  document_id: string;
  title: string;
  filename: string | null;
  /** Physical page for PDFs; null for DOCX/TXT/Markdown. */
  page: number | null;
  chunk_index: number | null;
  /** Section heading for DOCX/Markdown. */
  section: string | null;
  version: string | null;
  /** ISO date from document metadata. */
  effective_date: string | null;
  /** ISO date from document metadata. */
  expiry_date: string | null;
  /** Date freshness was evaluated against (the request date). */
  as_of_date: string | null;
  source_freshness: SourceFreshness | null;
  has_competing_versions: boolean;
  competing_versions: unknown[];
}

export type MessageRole = "user" | "assistant";

export interface MessageMetadata {
  /** "question" for user messages. */
  message_type?: string;
  /**
   * True when the assistant asked for clarification. This is the source of
   * truth for rendering: the top-level `SendMessageResponse.needs_clarification`
   * is not available when history is reloaded.
   */
  needs_clarification?: boolean;
  /** The standalone query the backend used for retrieval. */
  retrieval_query?: string | null;
  /** Reason for abstention when `abstained` is true. */
  answer_reason?: string | null;
  [key: string]: unknown;
}

export interface MessageResponse {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  citations: Citation[];
  abstained: boolean;
  metadata: MessageMetadata;
  created_at: string;
}

export interface SendMessageRequest {
  /** 1–8000 characters. */
  content: string;
  /** Default 5, min 1, max 20. */
  top_k?: number;
}

export interface SendMessageResponse {
  session_id: string;
  user_message: MessageResponse;
  assistant_message: MessageResponse;
  retrieval_query: string | null;
  needs_clarification: boolean;
}

// ─── Documents ───────────────────────────────────────────────────────────────

export type DocumentStatus = "queued" | "processing" | "completed" | "failed";

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
  status: DocumentStatus;
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

export interface DocumentListParams {
  status?: DocumentStatus;
  /** 1–200, default 50. */
  limit?: number;
  /** ≥ 0, default 0. */
  offset?: number;
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
  status: DocumentStatus;
  chunk_count: number;
  message: string;
}

export interface DocumentDeleteResponse {
  document_id: string;
  deleted: boolean;
  message: string;
}

// ─── Errors ──────────────────────────────────────────────────────────────────

/** One entry of FastAPI's 422 validation error list. */
export interface ValidationErrorItem {
  loc: (string | number)[];
  msg: string;
  type: string;
}

/** FastAPI error body: `detail` is a string, or a list for request validation errors. */
export interface ApiErrorBody {
  detail?: string | ValidationErrorItem[];
}
