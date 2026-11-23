"use client";

import { BookOpen, Sparkles } from "lucide-react";
import { useMemo } from "react";

import { AbstentionAlert } from "@/components/chat/AbstentionAlert";
import { ClarificationBadge } from "@/components/chat/ClarificationBadge";
import { MarkdownContent } from "@/components/chat/MarkdownContent";
import { Button } from "@/components/ui/button";
import { getAssistantMessageKind } from "@/lib/messages";
import { useChatUiStore } from "@/store/useChatUiStore";
import type { MessageResponse } from "@/types/api";

export function AssistantAvatar() {
  return (
    <span
      className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/15 text-primary"
      aria-hidden
    >
      <Sparkles className="size-4" />
    </span>
  );
}

/**
 * Assistant message in one of three states (plan §7.4):
 * answer (markdown + clickable [S1] citation chips + "View sources"),
 * clarification (blue left border), abstention (amber box).
 */
export function AssistantMessage({ message }: Readonly<{ message: MessageResponse }>) {
  const kind = getAssistantMessageKind(message);
  const citations = useMemo(
    () => ({ messageId: message.id, items: message.citations }),
    [message.id, message.citations],
  );

  return (
    <div className="flex items-start gap-3" data-kind={kind}>
      <AssistantAvatar />
      <div className="min-w-0 flex-1 pt-1">
        <span className="sr-only">ContextIQ:</span>
        {kind === "abstention" ? <AbstentionAlert /> : null}
        {kind === "clarification" ? (
          <div className="flex flex-col gap-2 rounded-r-lg border-l-4 border-info bg-info/5 py-3 pr-4 pl-4">
            <ClarificationBadge />
            <MarkdownContent content={message.content} />
          </div>
        ) : null}
        {kind === "answer" ? (
          <>
            <MarkdownContent content={message.content} citations={citations} />
            {message.citations.length > 0 ? (
              <ViewSourcesButton messageId={message.id} count={message.citations.length} />
            ) : null}
          </>
        ) : null}
      </div>
    </div>
  );
}

function ViewSourcesButton({ messageId, count }: Readonly<{ messageId: string; count: number }>) {
  const openSources = useChatUiStore((state) => state.openSources);
  const isOpen = useChatUiStore(
    (state) => state.sourcesPanelOpen && state.activeCitationMessageId === messageId,
  );
  return (
    <Button
      variant="ghost"
      size="sm"
      className="mt-2 -ml-2 text-muted-foreground"
      onClick={() => openSources(messageId)}
      aria-pressed={isOpen}
    >
      <BookOpen aria-hidden />
      View sources ({count})
    </Button>
  );
}
