"use client";

import { cn } from "@/lib/utils";
import { useChatUiStore } from "@/store/useChatUiStore";
import type { Citation } from "@/types/api";

/**
 * Inline [S1] marker in an answer (plan §7.6). Clicking it opens the Sources
 * panel on this message and highlights the matching CitationCard.
 */
export function CitationChip({
  messageId,
  citation,
}: Readonly<{ messageId: string; citation: Citation }>) {
  const setActiveCitation = useChatUiStore((state) => state.setActiveCitation);
  const isActive = useChatUiStore(
    (state) =>
      state.sourcesPanelOpen &&
      state.activeCitationMessageId === messageId &&
      state.activeCitationSourceId === citation.source_id,
  );
  const name = citation.filename ?? citation.title;

  return (
    <button
      type="button"
      onClick={() => setActiveCitation(messageId, citation.source_id)}
      aria-pressed={isActive}
      aria-label={`Source ${citation.source_id}: ${name}`}
      title={name}
      data-source-id={citation.source_id}
      className={cn(
        "ml-0.5 inline-flex h-5 translate-y-[-1px] items-center rounded-md px-1.5 align-middle font-sans text-[11px] leading-none font-semibold not-italic",
        "bg-primary/15 text-primary transition-colors duration-150 ease-out hover:bg-primary/25",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        "aria-pressed:bg-primary aria-pressed:text-primary-foreground",
      )}
    >
      {citation.source_id}
    </button>
  );
}
