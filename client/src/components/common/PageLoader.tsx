import { Spinner } from "@/components/ui/spinner";

/** Full-area loading state, e.g. while the stored session is being checked. */
export function PageLoader({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex flex-1 items-center justify-center p-6" aria-busy="true">
      <span className="flex items-center gap-2 text-sm text-muted-foreground">
        <Spinner className="text-primary" />
        {label}
      </span>
    </div>
  );
}
