import { memo } from "react";

import { AssistantMessage } from "@/components/chat/AssistantMessage";
import { UserMessage } from "@/components/chat/UserMessage";
import type { MessageResponse } from "@/types/api";

/** Renders a user OR assistant message. Memoised: history doesn't re-render on each send. */
export const MessageItem = memo(function MessageItem({ message }: { message: MessageResponse }) {
  return message.role === "user" ? (
    <UserMessage message={message} />
  ) : (
    <AssistantMessage message={message} />
  );
});
