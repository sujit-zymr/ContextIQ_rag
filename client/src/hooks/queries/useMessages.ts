"use client";

import { useIsMutating, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { DEFAULT_TOP_K, MESSAGE_HISTORY_LIMIT } from "@/lib/constants";
import { mutationKeys, queryKeys } from "@/lib/query-keys";
import { getMessages, sendMessage } from "@/services/chat.service";
import type { MessageResponse } from "@/types/api";

/** Prefix of the temporary id given to a question while it is being answered. */
export const OPTIMISTIC_MESSAGE_PREFIX = "optimistic-";

export function isOptimisticMessage(message: MessageResponse): boolean {
  return message.id.startsWith(OPTIMISTIC_MESSAGE_PREFIX);
}

let optimisticCounter = 0;

/** True while a question in this session is waiting for the backend's answer. */
export function useIsSendingMessage(sessionId: string): boolean {
  return useIsMutating({ mutationKey: mutationKeys.sendMessage(sessionId) }) > 0;
}

/**
 * GET /sessions/{id}/messages.
 *
 * Disabled while a send for this session is in flight, so a history fetch can
 * never overwrite the optimistic question (the /chat → /chat/[id] race, plan §6.1).
 */
export function useMessagesQuery(sessionId: string) {
  const isSending = useIsSendingMessage(sessionId);
  return useQuery({
    queryKey: queryKeys.sessions.messages(sessionId),
    queryFn: ({ signal }) => getMessages(sessionId, MESSAGE_HISTORY_LIMIT, signal),
    enabled: Boolean(sessionId) && !isSending,
  });
}

export interface SendMessageVariables {
  content: string;
  topK?: number;
}

/**
 * POST /sessions/{id}/messages with an optimistic user bubble.
 *
 * These callbacks are defined on the mutation itself, so they still run if the
 * component that started the send unmounts (e.g. /chat navigating to /chat/[id]).
 */
export function useSendMessage(sessionId: string) {
  const queryClient = useQueryClient();
  const messagesKey = queryKeys.sessions.messages(sessionId);

  return useMutation({
    mutationKey: mutationKeys.sendMessage(sessionId),
    mutationFn: ({ content, topK = DEFAULT_TOP_K }: SendMessageVariables) =>
      sendMessage(sessionId, content, topK),

    onMutate: async ({ content }) => {
      await queryClient.cancelQueries({ queryKey: messagesKey });
      const previous = queryClient.getQueryData<MessageResponse[]>(messagesKey);
      optimisticCounter += 1;
      const optimistic: MessageResponse = {
        id: `${OPTIMISTIC_MESSAGE_PREFIX}${Date.now()}-${optimisticCounter}`,
        session_id: sessionId,
        role: "user",
        content,
        citations: [],
        abstained: false,
        metadata: { message_type: "question" },
        created_at: new Date().toISOString(),
      };
      queryClient.setQueryData<MessageResponse[]>(messagesKey, [...(previous ?? []), optimistic]);
      return { previous, optimisticId: optimistic.id };
    },

    onSuccess: (response, _variables, context) => {
      queryClient.setQueryData<MessageResponse[]>(messagesKey, (old = []) => [
        ...old.filter((message) => message.id !== context?.optimisticId),
        response.user_message,
        response.assistant_message,
      ]);
    },

    onError: (_error, _variables, context) => {
      queryClient.setQueryData(messagesKey, context?.previous);
      // The server may have stored the question before failing (e.g. a 502
      // from the AI service), so resync with the real history.
      void queryClient.invalidateQueries({ queryKey: messagesKey });
    },

    onSettled: () => {
      // message_count, updated_at and statuses changed.
      void queryClient.invalidateQueries({ queryKey: queryKeys.sessions.all, exact: true });
    },
  });
}
