import { create } from "zustand";

/**
 * Browser-only chat UI state (plan §6.3). Server data (sessions, messages)
 * lives in the TanStack Query cache, never here.
 */
interface ChatUiState {
  /** Citation marker highlighted in the Sources panel, e.g. "S1". */
  activeCitationSourceId: string | null;
  /** Assistant message the active citation belongs to (markers repeat per answer). */
  activeCitationMessageId: string | null;
  sourcesPanelOpen: boolean;
  /** Desktop sidebar in icon-only (64px) mode. */
  sidebarCollapsed: boolean;
  /** Mobile slide-over sidebar. */
  mobileSidebarOpen: boolean;

  /** Opens the Sources panel on a message's citation and highlights it. */
  setActiveCitation: (messageId: string, sourceId: string | null) => void;
  /** Opens the Sources panel for a message without highlighting a citation. */
  openSources: (messageId: string) => void;
  closeSources: () => void;
  toggleSidebar: () => void;
  setMobileSidebarOpen: (open: boolean) => void;
  /** Clears per-conversation state (New Chat, logout). Keeps the sidebar preference. */
  reset: () => void;
}

const conversationDefaults = {
  activeCitationSourceId: null,
  activeCitationMessageId: null,
  sourcesPanelOpen: false,
  mobileSidebarOpen: false,
} satisfies Partial<ChatUiState>;

export const useChatUiStore = create<ChatUiState>()((set) => ({
  ...conversationDefaults,
  sidebarCollapsed: false,

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
  toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
  setMobileSidebarOpen: (open) => set({ mobileSidebarOpen: open }),
  reset: () => set(conversationDefaults),
}));
