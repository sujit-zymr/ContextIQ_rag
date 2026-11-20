export const APP_NAME = "ContextIQ";

export const APP_DESCRIPTION =
  "Ask questions about your documents and get AI-powered answers with cited sources.";

/** Backend base URL. Only public, non-secret configuration belongs in NEXT_PUBLIC_* vars. */
export const API_BASE_URL = (
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
).replace(/\/+$/, "");

/** localStorage key holding the JWT access token. */
export const TOKEN_STORAGE_KEY = "contextiq.access_token";

/** File types accepted by POST /documents/upload (server/app/api/documents.py). */
export const SUPPORTED_FILE_EXTENSIONS = [
  ".pdf",
  ".docx",
  ".txt",
  ".md",
  ".markdown",
] as const;

export const SUPPORTED_FILE_TYPES_LABEL = "PDF, DOCX, TXT, and Markdown";

/** Backend validation limits (server/app/api/schemas.py). */
export const PASSWORD_MIN_LENGTH = 12;
export const PASSWORD_MAX_LENGTH = 128;
export const MESSAGE_MAX_LENGTH = 8000;
export const SESSION_TITLE_MAX_LENGTH = 80;
/** Length of the session title derived from the first question (plan §7.3). */
export const SESSION_TITLE_FROM_QUESTION_LENGTH = 50;
export const DEFAULT_TOP_K = 5;
/** History size requested per session (backend max 500; returns the most recent N). */
export const MESSAGE_HISTORY_LIMIT = 500;
