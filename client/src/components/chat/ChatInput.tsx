"use client";

import { ArrowUp, Plus } from "lucide-react";
import { type KeyboardEvent, type RefObject, useLayoutEffect, useRef, useState } from "react";

import { UploadDocumentDialog } from "@/components/documents/UploadDocumentDialog";
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

const DISCLAIMER = "ContextIQ can make mistakes. Verify important information in the cited source.";

/**
 * Multiline question input (plan §7.4): grows with its content up to 6 rows,
 * then scrolls. Enter sends, Shift+Enter inserts a newline. "Attach document"
 * opens the upload dialog (the file joins the shared knowledge base).
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
  const [attachOpen, setAttachOpen] = useState(false);
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
    <div className={cn("flex w-full flex-col gap-2", className)}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
      >
        {/* The group dims itself when anything inside is disabled, including the
            send button on an empty question; dim only when the input is disabled. */}
        <InputGroup
          className={cn(
            "rounded-xl bg-card shadow-xs has-disabled:bg-card has-disabled:opacity-100",
            isDisabled && "opacity-60",
          )}
        >
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
            className="max-h-[calc(6lh+1.25rem)] min-h-12 resize-none overflow-y-auto px-4 pt-3.5 text-base md:text-sm"
          />
          <InputGroupAddon align="block-end" className="justify-between gap-2 px-2.5 pb-2.5">
            <InputGroupButton
              type="button"
              variant="ghost"
              size="xs"
              className="text-muted-foreground"
              onClick={() => setAttachOpen(true)}
            >
              <Plus aria-hidden /> Attach document
            </InputGroupButton>
            <div className="flex items-center gap-2">
              {value.length >= COUNTER_THRESHOLD ? (
                <InputGroupText className="text-xs font-normal text-muted-foreground">
                  <span aria-live="polite">
                    {value.length.toLocaleString()} / {MESSAGE_MAX_LENGTH.toLocaleString()}
                  </span>
                </InputGroupText>
              ) : null}
              <InputGroupButton
                type="submit"
                variant="default"
                size="icon-sm"
                className="rounded-lg"
                disabled={!canSubmit}
                aria-label={isBusy ? "Sending…" : "Send message"}
              >
                {isBusy ? <Spinner /> : <ArrowUp aria-hidden />}
              </InputGroupButton>
            </div>
          </InputGroupAddon>
        </InputGroup>
      </form>
      <p className="text-center text-xs text-muted-foreground">{DISCLAIMER}</p>
      <UploadDocumentDialog open={attachOpen} onOpenChange={setAttachOpen} />
    </div>
  );
}
