import type { DocumentListParams } from "@/types/api";

/**
 * Single source of truth for TanStack Query keys (plan §6.1).
 * Keys are hierarchical, so invalidating a prefix (e.g. `queryKeys.documents.all`)
 * also invalidates every list and detail query below it.
 */
export const queryKeys = {
  sessions: {
    all: ["sessions"] as const,
    messages: (sessionId: string) => ["sessions", sessionId, "messages"] as const,
  },
  documents: {
    all: ["documents"] as const,
    lists: ["documents", "list"] as const,
    list: (params: DocumentListParams = {}) => ["documents", "list", params] as const,
    detail: (documentId: string) => ["documents", "detail", documentId] as const,
  },
} as const;

/** Mutation keys, used to detect in-flight sends with `useIsMutating`. */
export const mutationKeys = {
  sendMessage: (sessionId: string) => ["sessions", sessionId, "send"] as const,
} as const;
