"use client";

import { ArrowDown } from "lucide-react";
import { useCallback, useLayoutEffect, useRef, useState } from "react";

import { MessageItem } from "@/components/chat/MessageItem";
import { TypingIndicator } from "@/components/chat/TypingIndicator";
import { Button } from "@/components/ui/button";
import type { MessageResponse } from "@/types/api";

/** Within this distance of the bottom, the list counts as "at the bottom". */
const STICK_TO_BOTTOM_PX = 120;

interface ChatContainerProps {
  messages: MessageResponse[];
  /** Show the TypingIndicator after the last message. */
  isSending: boolean;
}

/**
 * Scrollable message list (plan §7.4).
 * - Starts at the bottom; follows new messages while the reader is at the bottom.
 * - Always scrolls to the user's own new question.
 * - If the reader has scrolled up, shows a "scroll to latest" button instead
 *   of jumping.
 */
export function ChatContainer({ messages, isSending }: Readonly<ChatContainerProps>) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const atBottomRef = useRef(true);
  const initialScrollDone = useRef(false);
  const [showJump, setShowJump] = useState(false);

  const scrollToBottom = useCallback((behavior: ScrollBehavior) => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior });
  }, []);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < STICK_TO_BOTTOM_PX;
    atBottomRef.current = atBottom;
    setShowJump(!atBottom);
  };

  const lastMessage = messages.at(-1);
  useLayoutEffect(() => {
    if (!initialScrollDone.current) {
      initialScrollDone.current = true;
      scrollToBottom("instant");
      return;
    }
    if (atBottomRef.current || lastMessage?.role === "user") scrollToBottom("smooth");
  }, [messages.length, lastMessage?.role, isSending, scrollToBottom]);

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div
        ref={scrollRef}
        onScroll={onScroll}
        className="flex-1 overflow-y-auto"
        role="log"
        aria-label="Conversation"
        aria-live="polite"
        aria-relevant="additions"
      >
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6">
          {messages.map((message) => (
            <MessageItem key={message.id} message={message} />
          ))}
          {isSending ? <TypingIndicator /> : null}
        </div>
      </div>

      {showJump ? (
        <Button
          variant="secondary"
          size="icon-sm"
          className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full shadow-md"
          onClick={() => scrollToBottom("smooth")}
          aria-label="Scroll to latest message"
        >
          <ArrowDown aria-hidden />
        </Button>
      ) : null}
    </div>
  );
}
