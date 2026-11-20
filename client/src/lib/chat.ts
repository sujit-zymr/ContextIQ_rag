import { SESSION_TITLE_FROM_QUESTION_LENGTH } from "@/lib/constants";

/**
 * Session title derived from the first question (plan §7.3): whitespace
 * collapsed, cut to 50 characters with an ellipsis when truncated.
 * Always within the backend's 1–80 character limit.
 */
export function deriveSessionTitle(question: string): string {
  const singleLine = question.replaceAll(/\s+/g, " ").trim();
  if (singleLine.length <= SESSION_TITLE_FROM_QUESTION_LENGTH) return singleLine;
  return singleLine.slice(0, SESSION_TITLE_FROM_QUESTION_LENGTH - 1).trimEnd() + "…";
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/** Session ids are UUIDs; the backend answers malformed ids with 422, not 404. */
export function isValidSessionId(value: string): boolean {
  return UUID_PATTERN.test(value);
}
