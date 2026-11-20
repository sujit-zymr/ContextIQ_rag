"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";

import { ChatInput } from "@/components/chat/ChatInput";
import { SuggestedPrompts } from "@/components/chat/SuggestedPrompts";
import { Logo } from "@/components/common/Logo";
import { useStartConversation } from "@/hooks/queries/useStartConversation";
import { APP_DESCRIPTION } from "@/lib/constants";
import { getErrorMessage } from "@/lib/errors";

/**
 * /chat (plan §7.3): welcome screen with suggested prompts. Sending the first
 * question creates a session and continues in /chat/[id].
 */
export function NewChatScreen() {
  const [question, setQuestion] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const { start, isStarting } = useStartConversation();

  const selectPrompt = (prompt: string) => {
    setQuestion(prompt);
    // Focus with the caret at the end so the user can edit or just press Enter.
    requestAnimationFrame(() => {
      const el = textareaRef.current;
      if (!el) return;
      el.focus();
      el.setSelectionRange(prompt.length, prompt.length);
    });
  };

  const submit = async (content: string) => {
    try {
      await start(content);
    } catch (error) {
      // The session could not be created; keep the question for a retry.
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex flex-1 flex-col items-center justify-center px-4 py-8">
        <div className="flex w-full max-w-3xl flex-col items-center gap-8">
          <div className="flex flex-col items-center gap-3 text-center">
            <Logo withWordmark={false} />
            <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              What would you like to know?
            </h2>
            <p className="max-w-md text-sm text-muted-foreground sm:text-base">{APP_DESCRIPTION}</p>
          </div>
          <SuggestedPrompts onSelect={selectPrompt} disabled={isStarting} />
        </div>
      </div>

      <div className="sticky bottom-0 bg-background/95 px-4 pt-2 pb-4 backdrop-blur supports-[backdrop-filter]:bg-background/80">
        <ChatInput
          value={question}
          onChange={setQuestion}
          onSubmit={submit}
          isBusy={isStarting}
          autoFocus
          textareaRef={textareaRef}
          className="mx-auto max-w-3xl"
        />
      </div>
    </div>
  );
}
