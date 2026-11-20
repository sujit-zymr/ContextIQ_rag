import { QueryClient } from "@tanstack/react-query";

import { isApiError } from "@/services/api";

/** Shown instantly when revisiting a screen, then refreshed in the background. */
const DEFAULT_STALE_TIME_MS = 30_000;
const MAX_QUERY_RETRIES = 1;

/**
 * Retry policy: never retry client errors (4xx: auth, validation, not found)
 * or cancelled requests. Retry network failures and 5xx at most once.
 */
export function shouldRetryQuery(failureCount: number, error: unknown): boolean {
  if (failureCount >= MAX_QUERY_RETRIES) return false;
  if (!isApiError(error)) return false;
  if (error.kind === "aborted" || error.kind === "parse") return false;
  if (error.kind === "network") return true;
  return error.status >= 500;
}

export function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: DEFAULT_STALE_TIME_MS,
        retry: shouldRetryQuery,
      },
      mutations: {
        // Never retry writes: sending a message costs an LLM call, and an
        // upload or delete must not be repeated without the user knowing.
        retry: false,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

/**
 * One QueryClient for the whole browser session, a fresh one for each server
 * render (so requests are never shared between users on the server).
 */
export function getQueryClient(): QueryClient {
  if (typeof window === "undefined") return makeQueryClient();
  browserQueryClient ??= makeQueryClient();
  return browserQueryClient;
}
