import { MessageCircleQuestion } from "lucide-react";

/** Label on assistant messages that ask the user to clarify (plan §7.4). */
export function ClarificationBadge() {
  return (
    <span className="inline-flex items-center gap-1.5 text-xs font-medium text-info">
      <MessageCircleQuestion className="size-3.5" aria-hidden />
      Clarification needed
    </span>
  );
}
