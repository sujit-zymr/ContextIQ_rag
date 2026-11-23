"use client";

import { X } from "lucide-react";
import { useEffect } from "react";

import { CitationCard, citationCardId } from "@/components/sources/CitationCard";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useChatUiStore } from "@/store/useChatUiStore";
import type { Citation, MessageResponse } from "@/types/api";

/** Below this width the 320px panel would squeeze the chat, so it becomes a drawer. */
const DESKTOP_PANEL_QUERY = "(min-width: 1024px)";

function describe(count: number) {
  return `${count} ${count === 1 ? "source" : "sources"} cited in this answer`;
}

/**
 * Sources for one answer (plan §7.6): a 320px right panel on desktop, a
 * slide-over drawer on smaller screens. Opened from a citation chip (scrolls
 * to and highlights that card) or the "View sources" button under an answer.
 */
export function SourcesPanel({ messages }: Readonly<{ messages: MessageResponse[] }>) {
  const isDesktop = useMediaQuery(DESKTOP_PANEL_QUERY, true);
  const open = useChatUiStore((state) => state.sourcesPanelOpen);
  const messageId = useChatUiStore((state) => state.activeCitationMessageId);
  const activeSourceId = useChatUiStore((state) => state.activeCitationSourceId);
  const closeSources = useChatUiStore((state) => state.closeSources);

  const citations = messages.find((m) => m.id === messageId)?.citations ?? [];
  const visible = open && messageId !== null && citations.length > 0;

  if (isDesktop) {
    if (!visible) return null;
    return (
      <aside
        aria-labelledby="sources-panel-title"
        className="flex w-80 shrink-0 flex-col border-l bg-card"
        onKeyDown={(event) => {
          if (event.key === "Escape") closeSources();
        }}
      >
        <div className="flex items-start justify-between gap-2 border-b px-4 py-3">
          <div>
            <h2 id="sources-panel-title" className="text-sm font-semibold tracking-tight">
              Sources
            </h2>
            <p className="text-xs text-muted-foreground">{describe(citations.length)}</p>
          </div>
          <Button variant="ghost" size="icon-sm" onClick={closeSources} aria-label="Close sources">
            <X aria-hidden />
          </Button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto p-3">
          <CitationList messageId={messageId} citations={citations} activeSourceId={activeSourceId} />
        </div>
      </aside>
    );
  }

  return (
    <Sheet open={visible} onOpenChange={(next) => (next ? undefined : closeSources())}>
      <SheetContent side="right" className="w-full gap-0 sm:max-w-sm">
        <SheetHeader className="border-b">
          <SheetTitle>Sources</SheetTitle>
          <SheetDescription>{describe(citations.length)}</SheetDescription>
        </SheetHeader>
        {messageId ? (
          <div className="min-h-0 flex-1 overflow-y-auto p-3">
            <CitationList messageId={messageId} citations={citations} activeSourceId={activeSourceId} />
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

function CitationList({
  messageId,
  citations,
  activeSourceId,
}: Readonly<{ messageId: string; citations: Citation[]; activeSourceId: string | null }>) {
  // Bring the clicked citation into view (it may be further down the list).
  useEffect(() => {
    if (!activeSourceId) return;
    document
      .getElementById(citationCardId(messageId, activeSourceId))
      ?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [messageId, activeSourceId]);

  return (
    <ul className="flex flex-col gap-3" aria-label="Cited sources">
      {citations.map((citation) => (
        <CitationCard
          key={citation.source_id}
          messageId={messageId}
          citation={citation}
          isActive={citation.source_id === activeSourceId}
        />
      ))}
    </ul>
  );
}
