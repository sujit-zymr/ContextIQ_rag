import { AssistantAvatar } from "@/components/chat/AssistantMessage";

/**
 * Shown while the backend is generating an answer (plan §7.4). The backend
 * does not stream, so this is a pulse, never character-by-character text.
 */
export function TypingIndicator() {
  return (
    <div className="flex items-start gap-3" role="status" aria-live="polite">
      <AssistantAvatar />
      <div className="flex h-8 items-center gap-1" aria-hidden>
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            className="size-2 animate-bounce rounded-full bg-muted-foreground/70"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
      </div>
      <span className="sr-only">ContextIQ is preparing an answer…</span>
    </div>
  );
}
