"use client";

import { MutationObserver, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback } from "react";
import { toast } from "sonner";

import { sendMessageMutationOptions } from "@/hooks/queries/useMessages";
import { useCreateSession } from "@/hooks/queries/useSessions";
import { deriveSessionTitle } from "@/lib/chat";
import { getErrorMessage } from "@/lib/errors";
import type { SessionResponse } from "@/types/api";

/**
 * First-message flow from /chat (plan §7.3):
 *   1. POST /sessions with a title derived from the question
 *   2. start POST /sessions/{id}/messages (optimistic question in the cache)
 *   3. navigate to /chat/{id} without waiting for the answer
 *
 * The send runs through a MutationObserver with the shared mutation options, so
 * it keeps running independently of /chat (which Next.js hides with <Activity>
 * rather than unmounting; the caller clears its input), and /chat/[id] sees it as pending via
 * `useIsSendingMessage` (its history query stays disabled: no race).
 *
 * `start` rejects if the session cannot be created (nothing was sent); the
 * caller keeps the question so the user can retry.
 */
export function useStartConversation() {
  const queryClient = useQueryClient();
  const router = useRouter();
  const { mutateAsync: createSession, isPending } = useCreateSession();

  const start = useCallback(
    async (question: string): Promise<SessionResponse> => {
      const content = question.trim();
      const session = await createSession(deriveSessionTitle(content));

      const send = new MutationObserver(
        queryClient,
        sendMessageMutationOptions(queryClient, session.id),
      );
      // Rollback and resync happen in the mutation's own onError.
      send.mutate({ content }).catch((error: unknown) => {
        toast.error(getErrorMessage(error));
      });

      router.push(`/chat/${session.id}`);
      return session;
    },
    [createSession, queryClient, router],
  );

  return { start, isStarting: isPending };
}
