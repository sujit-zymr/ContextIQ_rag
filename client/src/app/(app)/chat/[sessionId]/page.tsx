import type { Metadata } from "next";

import { PhasePlaceholder } from "@/components/layout/PhasePlaceholder";

export const metadata: Metadata = { title: "Conversation" };

/** TEMPORARY: replaced by the active conversation view in Phase 7. */
export default function ConversationPage() {
  return <PhasePlaceholder title="Conversation" phase={7} />;
}
