import type { Metadata } from "next";

import { NewChatScreen } from "@/components/chat/NewChatScreen";

export const metadata: Metadata = { title: "New chat" };

/** Signed-in only: RequireAuth renders a loader on the server, so instant validation can't render this page. */
export const instant = false;

/** /chat: New Chat welcome screen (plan §7.3). */
export default function ChatPage() {
  return <NewChatScreen />;
}
