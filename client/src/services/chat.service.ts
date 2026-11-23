import { DEFAULT_TOP_K, SESSION_TITLE_MAX_LENGTH } from "@/lib/constants";
import { apiRequest, segment } from "@/services/api";
import type {
  MessageResponse,
  SendMessageResponse,
  SessionResponse,
} from "@/types/api";

const SESSION_NOT_FOUND = "Conversation not found.";

/** GET /sessions: all of the user's sessions, both `active` and `archived`. */
export function listSessions(signal?: AbortSignal) {
  return apiRequest<SessionResponse[]>("/sessions", { signal });
}

/**
 * POST /sessions. The title is trimmed and cut to the backend's 80-character
 * limit; an empty title falls back to the server default ("New chat").
 */
export function createSession(title?: string, signal?: AbortSignal) {
  const trimmed = title?.trim().slice(0, SESSION_TITLE_MAX_LENGTH).trim();
  return apiRequest<SessionResponse>("/sessions", {
    method: "POST",
    json: trimmed ? { title: trimmed } : {},
    signal,
  });
}

/** POST /sessions/{id}/activate. The backend archives the user's other sessions. */
export function activateSession(sessionId: string, signal?: AbortSignal) {
  return apiRequest<SessionResponse>(`/sessions/${segment(sessionId)}/activate`, {
    method: "POST",
    errorMessages: { 404: SESSION_NOT_FOUND },
    signal,
  });
}

/** GET /sessions/{id}/messages: chronological history. `limit` is 1–500 (server default 100). */
export function getMessages(sessionId: string, limit?: number, signal?: AbortSignal) {
  return apiRequest<MessageResponse[]>(`/sessions/${segment(sessionId)}/messages`, {
    query: { limit },
    errorMessages: { 404: SESSION_NOT_FOUND },
    signal,
  });
}

/**
 * POST /sessions/{id}/messages. Returns only after the full answer has been
 * generated (no streaming), which can take several seconds.
 */
export function sendMessage(
  sessionId: string,
  content: string,
  topK: number = DEFAULT_TOP_K,
  signal?: AbortSignal,
) {
  return apiRequest<SendMessageResponse>(`/sessions/${segment(sessionId)}/messages`, {
    method: "POST",
    json: { content, top_k: topK },
    errorMessages: { 404: SESSION_NOT_FOUND },
    signal,
  });
}
