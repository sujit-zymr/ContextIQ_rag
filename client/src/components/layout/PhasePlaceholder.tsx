import { Construction } from "lucide-react";

/**
 * TEMPORARY: content area for screens built in later phases, so the shell's
 * navigation can be used and tested now. Remove when the last placeholder goes.
 */
export function PhasePlaceholder({ title, phase }: { title: string; phase: number }) {
  return (
    <div className="flex flex-1 items-center justify-center p-6">
      <div className="flex max-w-sm flex-col items-center gap-3 text-center">
        <Construction className="size-8 text-muted-foreground" aria-hidden />
        <h2 className="text-lg font-semibold tracking-tight">{title}</h2>
        <p className="text-sm text-muted-foreground">This screen arrives in Phase {phase}.</p>
      </div>
    </div>
  );
}
