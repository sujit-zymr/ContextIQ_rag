import Image, { type StaticImageData } from "next/image";

import fullDark from "@/assets/logo-full-dark.png";
import fullLight from "@/assets/logo-full-light.png";
import markDark from "@/assets/logo-mark-dark.png";
import markLight from "@/assets/logo-mark.png";
import wordmarkDark from "@/assets/logo-wordmark-dark.png";
import wordmarkLight from "@/assets/logo-wordmark-light.png";
import { APP_NAME } from "@/lib/constants";
import { cn } from "@/lib/utils";

/**
 * - `full`: mark + "ContextIQ" + tagline, for large spaces (sign-in pages).
 * - `wordmark`: mark + "ContextIQ" without the tagline (expanded sidebar).
 * - `mark`: the "C" with three dots only (collapsed sidebar, welcome screen, avatars).
 * Generated from src/assets/ContextIQ_Logo.png with transparent backgrounds.
 */
export type LogoVariant = "full" | "wordmark" | "mark";

const IMAGES: Record<LogoVariant, { light: StaticImageData; dark: StaticImageData }> = {
  full: { light: fullLight, dark: fullDark },
  wordmark: { light: wordmarkLight, dark: wordmarkDark },
  mark: { light: markLight, dark: markDark },
};

interface LogoProps {
  variant?: LogoVariant;
  /** Size the logo by height (e.g. `h-9`); the width follows the image. */
  className?: string;
  /** Decorative uses (next to visible text) pass true to hide it from screen readers. */
  decorative?: boolean;
  priority?: boolean;
}

/**
 * ContextIQ logo. Both theme versions are rendered and CSS shows the right one,
 * so the logo is correct on first paint without waiting for the theme to load.
 */
export function Logo({ variant = "wordmark", className, decorative = false, priority }: LogoProps) {
  const { light, dark } = IMAGES[variant];
  const alt = decorative ? "" : APP_NAME;
  const imageClass = "h-full w-auto max-w-none select-none";

  return (
    <span className={cn("inline-flex h-8 shrink-0 items-center", className)}>
      <Image src={light} alt={alt} priority={priority} className={cn(imageClass, "dark:hidden")} />
      <Image src={dark} alt={alt} priority={priority} className={cn(imageClass, "hidden dark:block")} />
    </span>
  );
}
