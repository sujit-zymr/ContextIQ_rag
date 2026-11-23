"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { toast } from "sonner";

import { CONVERSATION_NOT_FOUND, ConversationView } from "@/components/chat/ConversationView";
import { useCurrentSessionId } from "@/hooks/useCurrentSession";
import { isValidSessionId } from "@/lib/chat";

/** Reads the route param and remounts the view per conversation (fresh state). */
export function ConversationRoute() {
  const sessionId = useCurrentSessionId();
  if (!sessionId) return null;
  if (!isValidSessionId(sessionId)) return <InvalidConversation />;
  return <ConversationView key={sessionId} sessionId={sessionId} />;
}

/** A malformed id can never exist: same outcome as a 404, without a request. */
function InvalidConversation() {
  const router = useRouter();
  useEffect(() => {
    toast.error(CONVERSATION_NOT_FOUND);
    router.replace("/chat");
  }, [router]);
  return null;
}
