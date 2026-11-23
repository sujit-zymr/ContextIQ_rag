import type { Metadata } from "next";

import { ConversationRoute } from "@/components/chat/ConversationRoute";

export const metadata: Metadata = { title: "Conversation" };

/** Signed-in only: RequireAuth renders a loader on the server, so instant validation can't render this page. */
export const instant = false;

/** /chat/[sessionId]: active conversation (plan §7.4). */
export default function ConversationPage() {
  return <ConversationRoute />;
}
