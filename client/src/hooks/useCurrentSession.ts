"use client";

import { useParams } from "next/navigation";

import { useSessionsQuery } from "@/hooks/queries/useSessions";
import type { SessionResponse } from "@/types/api";

/** The `[sessionId]` route param, or null outside /chat/[sessionId]. */
export function useCurrentSessionId(): string | null {
  const params = useParams<{ sessionId?: string }>();
  return typeof params?.sessionId === "string" ? params.sessionId : null;
}

/** The session for the current route, looked up in the cached session list. */
export function useCurrentSession(): {
  sessionId: string | null;
  session: SessionResponse | undefined;
} {
  const sessionId = useCurrentSessionId();
  const { data: sessions } = useSessionsQuery();
  return {
    sessionId,
    session: sessionId ? sessions?.find((s) => s.id === sessionId) : undefined,
  };
}
