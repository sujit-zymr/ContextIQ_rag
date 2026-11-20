import { create } from "zustand";

/**
 * Browser-only chat UI state (plan §6.3). Server data (sessions, messages)
 * lives in the TanStack Query cache, never here. Sidebar open/collapsed state
 * is owned by the shadcn `SidebarProvider` (see components/layout/AppShell.tsx).
 */
interface ChatUiState {
  /** Citation marker highlighted in the Sources panel, e.g. "S1". */
  activeCitationSourceId: string | null;
  /** Assistant message the active citation belongs to (markers repeat per answer). */
  activeCitationMessageId: string | null;
  sourcesPanelOpen: boolean;

  /** Opens the Sources panel on a message's citation and highlights it. */
  setActiveCitation: (messageId: string, sourceId: string | null) => void;
  /** Opens the Sources panel for a message without highlighting a citation. */
  openSources: (messageId: string) => void;
  closeSources: () => void;
  /** Clears per-conversation state (New Chat, switching conversation, logout). */
  reset: () => void;
}

const conversationDefaults = {
  activeCitationSourceId: null,
  activeCitationMessageId: null,
  sourcesPanelOpen: false,
} satisfies Partial<ChatUiState>;

export const useChatUiStore = create<ChatUiState>()((set) => ({
  ...conversationDefaults,

  setActiveCitation: (messageId, sourceId) =>
    set({
      activeCitationMessageId: messageId,
      activeCitationSourceId: sourceId,
      sourcesPanelOpen: true,
    }),
  openSources: (messageId) =>
    set({
      activeCitationMessageId: messageId,
      activeCitationSourceId: null,
      sourcesPanelOpen: true,
    }),
  closeSources: () => set({ sourcesPanelOpen: false, activeCitationSourceId: null }),
  reset: () => set(conversationDefaults),
}));
