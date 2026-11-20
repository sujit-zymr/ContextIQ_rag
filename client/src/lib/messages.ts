import type { MessageResponse } from "@/types/api";
import type { AssistantMessageKind } from "@/types/chat";

/**
 * How an assistant message is rendered (plan §7.4). Reads the message itself,
 * never the top-level send response, so live and reloaded history match:
 * `metadata.needs_clarification` → clarification, `abstained` → abstention.
 */
export function getAssistantMessageKind(message: MessageResponse): AssistantMessageKind {
  if (message.metadata?.needs_clarification === true) return "clarification";
  if (message.abstained) return "abstention";
  return "answer";
}
