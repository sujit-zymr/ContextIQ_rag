import type { Metadata } from "next";

import { ConversationRoute } from "@/components/chat/ConversationRoute";

export const metadata: Metadata = { title: "Conversation" };

/** /chat/[sessionId]: active conversation (plan §7.4). */
export default function ConversationPage() {
  return <ConversationRoute />;
}
