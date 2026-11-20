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
