import { ERROR_MESSAGES, isApiError } from "@/services/api";

const FALLBACK_MESSAGE = ERROR_MESSAGES.serverError;

/** User-safe message for any thrown value. */
export function getErrorMessage(error: unknown): string {
  return isApiError(error) ? error.message : FALLBACK_MESSAGE;
}

/**
 * Plan §9: connectivity and server-side failures are shown as toasts; client
 * errors (wrong password, duplicate email, validation) are shown inline.
 */
export function isToastError(error: unknown): boolean {
  if (!isApiError(error)) return true;
  if (error.kind === "network" || error.kind === "parse") return true;
  return error.kind === "http" && error.status >= 500;
}
