import { Sparkles } from "lucide-react";

import { AbstentionAlert } from "@/components/chat/AbstentionAlert";
import { ClarificationBadge } from "@/components/chat/ClarificationBadge";
import { MarkdownContent } from "@/components/chat/MarkdownContent";
import { getAssistantMessageKind } from "@/lib/messages";
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
 * answer (markdown), clarification (blue left border), abstention (amber box).
 * Inline [S1] markers become clickable citation chips in Phase 8.
 */
export function AssistantMessage({ message }: { message: MessageResponse }) {
  const kind = getAssistantMessageKind(message);

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
        {kind === "answer" ? <MarkdownContent content={message.content} /> : null}
      </div>
    </div>
  );
}
