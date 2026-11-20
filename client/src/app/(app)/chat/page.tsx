import type { Metadata } from "next";

import { PhasePlaceholder } from "@/components/layout/PhasePlaceholder";

export const metadata: Metadata = { title: "Chat" };

/** TEMPORARY: replaced by the New Chat welcome screen in Phase 6. */
export default function ChatPage() {
  return <PhasePlaceholder title="New chat" phase={6} />;
}
