import { TOKEN_STORAGE_KEY } from "@/lib/constants";

/**
 * JWT access-token persistence in localStorage (plan §6.1).
 *
 * Every accessor is SSR-safe (no `window` on the server) and tolerant of
 * storage being unavailable (private mode, blocked site data), in which case
 * the user simply appears signed out.
 */

function storage(): Storage | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage;
  } catch {
    return null;
  }
}

export function getStoredToken(): string | null {
  try {
    return storage()?.getItem(TOKEN_STORAGE_KEY) ?? null;
  } catch {
    return null;
  }
}

export function setStoredToken(token: string): void {
  try {
    storage()?.setItem(TOKEN_STORAGE_KEY, token);
  } catch {
    // Storage full or blocked: the token stays in memory only (auth store).
  }
}

export function clearStoredToken(): void {
  try {
    storage()?.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    // Nothing to clear.
  }
}
