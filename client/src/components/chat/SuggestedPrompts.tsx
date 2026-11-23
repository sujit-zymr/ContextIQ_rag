"use client";

import { FileText } from "lucide-react";

/**
 * Plan §7.3: four starter prompts. Clicking one pre-fills the chat input with
 * the start of a question for the user to complete.
 */
export const SUGGESTED_PROMPTS: readonly { label: string; prompt: string }[] = [
  { label: "Summarize a document", prompt: "Summarize the main points of the document about " },
  { label: "Find a specific detail", prompt: "Find where the documents mention " },
  { label: "Compare two documents", prompt: "Compare what the documents say about " },
  { label: "Explain a key concept", prompt: "Explain the concept of " },
];

interface SuggestedPromptsProps {
  onSelect: (prompt: string) => void;
  disabled?: boolean;
}

export function SuggestedPrompts({ onSelect, disabled }: SuggestedPromptsProps) {
  return (
    <ul className="grid w-full max-w-xl gap-3 sm:grid-cols-2" aria-label="Suggested questions">
      {SUGGESTED_PROMPTS.map(({ label, prompt }) => (
        <li key={label}>
          <button
            type="button"
            onClick={() => onSelect(prompt)}
            disabled={disabled}
            className="flex h-full w-full items-center gap-3 rounded-lg border bg-card px-4 py-3 text-left text-sm transition-colors duration-150 ease-out outline-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
          >
            <FileText className="size-4 shrink-0 text-muted-foreground" aria-hidden />
            <span>{label}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
