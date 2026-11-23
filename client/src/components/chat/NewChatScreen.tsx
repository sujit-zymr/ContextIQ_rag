"use client";

import { useRef, useState } from "react";
import { toast } from "sonner";

import { ChatInput } from "@/components/chat/ChatInput";
import { SuggestedPrompts } from "@/components/chat/SuggestedPrompts";
import { Logo } from "@/components/common/Logo";
import { useStartConversation } from "@/hooks/queries/useStartConversation";
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
      // Next.js keeps this page mounted but hidden (<Activity>) after navigating
      // to the conversation, so its state survives: clear the sent question, or
      // the next "New chat" would show it and append the new question to it.
      setQuestion("");
    } catch (error) {
      // The session could not be created; keep the question for a retry.
      toast.error(getErrorMessage(error));
    }
  };

  return (
    <div className="flex flex-1 flex-col">
      <div className="flex flex-1 flex-col items-center justify-center px-4 py-8">
        <div className="flex w-full max-w-3xl flex-col items-center gap-8">
          <div className="flex flex-col items-center gap-4 text-center">
            <Logo variant="mark" className="size-12" decorative />
            <div className="flex flex-col gap-2">
              <h2 className="text-2xl font-semibold tracking-tight sm:text-3xl">
                A clearer way to work with your knowledge.
              </h2>
              <p className="text-sm text-muted-foreground">
                Ask questions, explore your files, and get answers grounded in your documents.
              </p>
            </div>
          </div>
          <SuggestedPrompts onSelect={selectPrompt} disabled={isStarting} />
        </div>
      </div>

      <div className="sticky bottom-0 bg-background px-4 pt-2 pb-3">
        <ChatInput
          value={question}
          onChange={setQuestion}
          onSubmit={submit}
          isBusy={isStarting}
          autoFocus
          textareaRef={textareaRef}
          className="mx-auto max-w-2xl"
        />
      </div>
    </div>
  );
}
