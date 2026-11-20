import type { Metadata } from "next";

import { NewChatScreen } from "@/components/chat/NewChatScreen";

export const metadata: Metadata = { title: "New chat" };

/** /chat: New Chat welcome screen (plan §7.3). */
export default function ChatPage() {
  return <NewChatScreen />;
}
