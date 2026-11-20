"use client";

import { CalendarCheck, FileText, Laptop, Scale, type LucideIcon } from "lucide-react";

/** Plan §7.3: four starter prompts; clicking one pre-fills the chat input. */
export const SUGGESTED_PROMPTS: readonly { text: string; icon: LucideIcon }[] = [
  { text: "Summarize the main points of an uploaded document", icon: FileText },
  { text: "What is the company leave and attendance policy?", icon: CalendarCheck },
  { text: "Explain the key terms in the uploaded agreement", icon: Scale },
  { text: "What are the latest guidelines for remote work?", icon: Laptop },
];

interface SuggestedPromptsProps {
  onSelect: (prompt: string) => void;
  disabled?: boolean;
}

export function SuggestedPrompts({ onSelect, disabled }: SuggestedPromptsProps) {
  return (
    <ul className="grid w-full gap-3 sm:grid-cols-2" aria-label="Suggested questions">
      {SUGGESTED_PROMPTS.map(({ text, icon: Icon }) => (
        <li key={text}>
          <button
            type="button"
            onClick={() => onSelect(text)}
            disabled={disabled}
            className="flex h-full w-full items-start gap-3 rounded-xl border bg-card p-4 text-left text-sm transition-colors duration-150 ease-out outline-none hover:bg-accent focus-visible:ring-2 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50"
          >
            <Icon className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
            <span>{text}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}
