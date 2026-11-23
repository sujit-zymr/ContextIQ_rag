import { CircleCheck, CircleX, Clock } from "lucide-react";
import type { ReactNode } from "react";

import { Badge } from "@/components/ui/badge";
import { Spinner } from "@/components/ui/spinner";
import type { DocumentStatus } from "@/types/api";

const STATUS: Record<DocumentStatus, { label: string; icon: ReactNode; className: string }> = {
  completed: {
    label: "Completed",
    icon: <CircleCheck aria-hidden data-icon="inline-start" />,
    className: "bg-success/15 text-success",
  },
  processing: {
    label: "Processing",
    // Decorative here: the badge text already says "Processing".
    icon: <Spinner role="presentation" aria-label={undefined} aria-hidden data-icon="inline-start" />,
    className: "bg-warning/15 text-warning",
  },
  queued: {
    label: "Queued",
    icon: <Clock aria-hidden data-icon="inline-start" />,
    className: "bg-muted text-muted-foreground",
  },
  failed: {
    label: "Failed",
    icon: <CircleX aria-hidden data-icon="inline-start" />,
    className: "bg-destructive/15 text-destructive",
  },
};

/** Plan §7.7: completed (green), processing (amber + spinner), failed (red); queued (grey). */
export function DocumentStatusBadge({ status }: Readonly<{ status: DocumentStatus }>) {
  const config = STATUS[status] ?? { label: status, icon: null, className: "bg-muted text-muted-foreground" };
  return (
    <Badge className={config.className} data-status={status}>
      {config.icon}
      {config.label}
    </Badge>
  );
}
