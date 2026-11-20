"use client";

import { ArrowUp } from "lucide-react";
import { type KeyboardEvent, type RefObject, useLayoutEffect, useRef } from "react";

import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupText,
  InputGroupTextarea,
} from "@/components/ui/input-group";
import { Spinner } from "@/components/ui/spinner";
import { MESSAGE_MAX_LENGTH } from "@/lib/constants";
import { cn } from "@/lib/utils";

/** Show the character counter once the question gets close to the limit. */
const COUNTER_THRESHOLD = MESSAGE_MAX_LENGTH - 500;

interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  /** Called with the trimmed question on Enter or the send button. */
  onSubmit: (value: string) => void;
  /** True while the question is being sent; disables input (plan §7.4). */
  isBusy?: boolean;
  disabled?: boolean;
  placeholder?: string;
  autoFocus?: boolean;
  /** Lets the parent focus the textarea (e.g. after picking a suggested prompt). */
  textareaRef?: RefObject<HTMLTextAreaElement | null>;
  className?: string;
}

/**
 * Multiline question input (plan §7.4): grows with its content up to 6 rows,
 * then scrolls. Enter sends, Shift+Enter inserts a newline.
 */
export function ChatInput({
  value,
  onChange,
  onSubmit,
  isBusy = false,
  disabled = false,
  placeholder = "Ask a question about your documents…",
  autoFocus,
  textareaRef,
  className,
}: ChatInputProps) {
  const ownRef = useRef<HTMLTextAreaElement | null>(null);
  const innerRef = textareaRef ?? ownRef;
  const trimmed = value.trim();
  const isDisabled = disabled || isBusy;
  const canSubmit = trimmed.length > 0 && !isDisabled;

  // Auto-resize: measure the content height; CSS max-height caps it at 6 rows.
  useLayoutEffect(() => {
    const el = innerRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [value, innerRef]);

  const submit = () => {
    if (canSubmit) onSubmit(trimmed);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    // Ignore Enter while an IME composition (e.g. CJK input) is in progress.
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form
      className={cn("w-full", className)}
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <InputGroup className="rounded-2xl bg-card shadow-sm">
        <InputGroupTextarea
          ref={innerRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          aria-label="Your question"
          maxLength={MESSAGE_MAX_LENGTH}
          rows={1}
          autoFocus={autoFocus}
          disabled={isDisabled}
          className="max-h-[calc(6lh+1.25rem)] min-h-12 resize-none overflow-y-auto px-4 pt-3.5 text-base md:text-base"
        />
        <InputGroupAddon align="block-end" className="justify-between gap-2 px-3 pb-2.5">
          <InputGroupText className="text-xs font-normal text-muted-foreground">
            {value.length >= COUNTER_THRESHOLD ? (
              <span aria-live="polite">
                {value.length.toLocaleString()} / {MESSAGE_MAX_LENGTH.toLocaleString()}
              </span>
            ) : (
              <span className="hidden sm:inline">Enter to send · Shift+Enter for a new line</span>
            )}
          </InputGroupText>
          <InputGroupButton
            type="submit"
            variant="default"
            size="icon-sm"
            className="rounded-full"
            disabled={!canSubmit}
            aria-label={isBusy ? "Sending…" : "Send message"}
          >
            {isBusy ? <Spinner /> : <ArrowUp aria-hidden />}
          </InputGroupButton>
        </InputGroupAddon>
      </InputGroup>
    </form>
  );
}
