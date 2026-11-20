import type { Metadata } from "next";

import { RequireAuth } from "@/components/auth/RouteGuards";

import { ChatPlaceholder } from "./ChatPlaceholder";

export const metadata: Metadata = { title: "Chat" };

/**
 * TEMPORARY (Phase 4): a protected placeholder so the sign-in flow and route
 * guards can be tested end to end. Replaced by the New Chat screen in Phase 6.
 */
export default function ChatPage() {
  return (
    <RequireAuth>
      <ChatPlaceholder />
    </RequireAuth>
  );
}
