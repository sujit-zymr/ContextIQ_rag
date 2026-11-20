import { isOptimisticMessage } from "@/hooks/queries/useMessages";
import { cn } from "@/lib/utils";
import type { MessageResponse } from "@/types/api";

/** The user's question, right-aligned (plan §7.4: slate-800 bubble = `bg-secondary`). */
export function UserMessage({ message }: { message: MessageResponse }) {
  const pending = isOptimisticMessage(message);
  return (
    <div className="flex justify-end">
      <div
        className={cn(
          "max-w-[85%] rounded-2xl rounded-br-sm bg-secondary px-4 py-2.5 text-sm whitespace-pre-wrap break-words text-secondary-foreground md:text-base",
          pending && "opacity-80",
        )}
        aria-busy={pending || undefined}
      >
        <span className="sr-only">You:</span>
        {message.content}
      </div>
    </div>
  );
}
