import { Sparkles } from "lucide-react";

import { APP_NAME } from "@/lib/constants";
import { cn } from "@/lib/utils";

interface LogoProps {
  /** Show the "ContextIQ" wordmark next to the icon. */
  withWordmark?: boolean;
  className?: string;
}

/** ContextIQ brand mark (icon + optional wordmark). */
export function Logo({ withWordmark = true, className }: LogoProps) {
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <span className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
        <Sparkles className="size-4" aria-hidden />
      </span>
      {withWordmark ? (
        <span className="text-lg font-semibold tracking-tight">{APP_NAME}</span>
      ) : (
        <span className="sr-only">{APP_NAME}</span>
      )}
    </span>
  );
}
