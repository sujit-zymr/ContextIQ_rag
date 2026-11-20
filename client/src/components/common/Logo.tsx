import { Sparkles } from "lucide-react";

import { APP_NAME } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface LogoProps {
  /** Show the "ContextIQ" wordmark next to the icon. */
  withWordmark?: boolean;
  className?: string;
  /** Extra classes for the wordmark, e.g. hiding it in the collapsed sidebar. */
  wordmarkClassName?: string;
}

/** ContextIQ brand mark (icon + optional wordmark). */
export function Logo({ withWordmark = true, className, wordmarkClassName }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <Sparkles className="size-4" aria-hidden />
      </span>
      {withWordmark ? (
        <span className={cn("text-lg font-semibold tracking-tight", wordmarkClassName)}>
          {APP_NAME}
        </span>
      ) : (
        <span className="sr-only">{APP_NAME}</span>
      )}
    </span>
  );
}
