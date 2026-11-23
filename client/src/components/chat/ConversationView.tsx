"use client";

import { CircleAlert, MessagesSquare, RotateCw } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";

import { ChatContainer } from "@/components/chat/ChatContainer";
import { ChatInput } from "@/components/chat/ChatInput";
import { SourcesPanel } from "@/components/sources/SourcesPanel";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useIsSendingMessage,
  useMessagesQuery,
  useSendMessage,
} from "@/hooks/queries/useMessages";
import { useActivateSession } from "@/hooks/queries/useSessions";
import { getErrorMessage } from "@/lib/errors";
import { isApiError } from "@/services/api";
import { useChatUiStore } from "@/store/useChatUiStore";

export const CONVERSATION_NOT_FOUND = "Conversation not found.";

/**
 * /chat/[sessionId] (plan §7.4). Mount with `key={sessionId}` so all local state
 * resets when switching conversations.
 */
export function ConversationView({ sessionId }: Readonly<{ sessionId: string }>) {
  const router = useRouter();
  const isSending = useIsSendingMessage(sessionId);
  const { data: messages, isPending, isError, error, refetch, isFetching } =
    useMessagesQuery(sessionId);
  const { mutate: activate } = useActivateSession();
  const { mutate: send } = useSendMessage(sessionId);
  const resetChatUi = useChatUiStore((state) => state.reset);
  const [draft, setDraft] = useState("");

  // New conversation → close any open citation panel from the previous one.
  useEffect(() => resetChatUi(), [resetChatUi]);

  // Mark this session active, once. Skipped while the first question is in
  // flight: sending already activates the session on the server (plan §7.3).
  const activationRequested = useRef(false);
  useEffect(() => {
    if (activationRequested.current) return;
    activationRequested.current = true;
    if (!isSending) activate(sessionId);
  }, [activate, isSending, sessionId]);

  // Missing or someone else's conversation → back to a new chat (plan §9).
  const notFound = isApiError(error) && error.status === 404;
  useEffect(() => {
    if (!notFound) return;
    toast.error(CONVERSATION_NOT_FOUND);
    router.replace("/chat");
  }, [notFound, router]);

  const submit = (content: string) => {
    setDraft("");
    send(
      { content },
      {
        onError: (sendError) => {
          // Give the question back so it can be retried (unless a new one was typed).
          setDraft((current) => current || content);
          toast.error(getErrorMessage(sendError));
        },
      },
    );
  };

  const renderBody = () => {
    if (messages) {
      if (messages.length === 0 && !isSending) {
        return (
          <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center text-muted-foreground">
            <MessagesSquare className="size-8" aria-hidden />
            <p className="text-sm">No messages yet. Ask your first question below.</p>
          </div>
        );
      }
      return <ChatContainer messages={messages} isSending={isSending} />;
    }
    if (isError && !notFound) {
      return (
        <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
          <CircleAlert className="size-8 text-destructive" aria-hidden />
          <p className="text-sm text-muted-foreground">{getErrorMessage(error)}</p>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RotateCw aria-hidden /> Try again
          </Button>
        </div>
      );
    }
    if (isPending) return <ConversationSkeleton />;
    return null;
  };

  return (
    <div className="flex min-h-0 flex-1">
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {renderBody()}
        <div className="border-t bg-background px-4 pt-3 pb-4">
          <ChatInput
            value={draft}
            onChange={setDraft}
            onSubmit={submit}
            isBusy={isSending}
            disabled={!messages}
            placeholder="Ask a follow-up question…"
            className="mx-auto max-w-3xl"
          />
        </div>
      </div>
      {/* Right panel on desktop, drawer on smaller screens (plan §7.6). */}
      {messages ? <SourcesPanel messages={messages} /> : null}
    </div>
  );
}

function ConversationSkeleton() {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-6 px-4 py-6" aria-busy="true">
      <span className="sr-only">Loading conversation…</span>
      <Skeleton className="ml-auto h-10 w-2/3 rounded-2xl" />
      <div className="flex gap-3">
        <Skeleton className="size-8 shrink-0 rounded-lg" />
        <div className="flex flex-1 flex-col gap-2">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
          <Skeleton className="h-4 w-2/3" />
        </div>
      </div>
      <Skeleton className="ml-auto h-10 w-1/2 rounded-2xl" />
    </div>
  );
}
