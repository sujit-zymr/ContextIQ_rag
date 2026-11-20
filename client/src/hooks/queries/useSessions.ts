"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import { activateSession, createSession, listSessions } from "@/services/chat.service";
import type { MessageResponse, SessionResponse } from "@/types/api";

/** Newest activity first (plan §7.5). Sessions of every status are kept. */
function sortByUpdatedAtDesc(sessions: SessionResponse[]): SessionResponse[] {
  return [...sessions].sort((a, b) => b.updated_at.localeCompare(a.updated_at));
}

/** GET /sessions for the sidebar. */
export function useSessionsQuery() {
  return useQuery({
    queryKey: queryKeys.sessions.all,
    queryFn: ({ signal }) => listSessions(signal),
    select: sortByUpdatedAtDesc,
  });
}

/**
 * POST /sessions. Inserts the new session into the sidebar cache and seeds an
 * empty message history, so /chat/[id] renders without a fetch.
 */
export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (title?: string) => createSession(title),
    onSuccess: (session) => {
      queryClient.setQueryData<SessionResponse[]>(queryKeys.sessions.all, (old = []) => [
        session,
        ...old.filter((existing) => existing.id !== session.id),
      ]);
      queryClient.setQueryData<MessageResponse[]>(queryKeys.sessions.messages(session.id), []);
      // Creating a session archives the previous active one on the server.
      void queryClient.invalidateQueries({ queryKey: queryKeys.sessions.all, exact: true });
    },
  });
}

/** POST /sessions/{id}/activate. The server archives the user's other sessions. */
export function useActivateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => activateSession(sessionId),
    onSuccess: (activated) => {
      queryClient.setQueryData<SessionResponse[]>(queryKeys.sessions.all, (old) =>
        old?.map((session) =>
          session.id === activated.id
            ? { ...session, ...activated, message_count: session.message_count }
            : { ...session, status: "archived" },
        ),
      );
    },
  });
}
