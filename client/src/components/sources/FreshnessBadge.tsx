import { CalendarClock, CircleCheck, History, TriangleAlert, type LucideIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import type { SourceFreshness } from "@/types/api";

type ShownFreshness = Exclude<SourceFreshness, "undated">;

/** Plan §7.6: green current, amber outdated, red superseded, blue future. */
const FRESHNESS: Record<ShownFreshness, { label: string; icon: LucideIcon; className: string }> = {
  current: { label: "Current", icon: CircleCheck, className: "bg-success/15 text-success" },
  outdated: {
    label: "Outdated — newer version may exist",
    icon: TriangleAlert,
    className: "bg-warning/15 text-warning",
  },
  superseded: { label: "Superseded", icon: History, className: "bg-destructive/15 text-destructive" },
  future: { label: "Not yet effective", icon: CalendarClock, className: "bg-info/15 text-info" },
};

/** Source freshness badge; `undated` and missing values show nothing. */
export function FreshnessBadge({ freshness }: Readonly<{ freshness: SourceFreshness | null }>) {
  if (!freshness || freshness === "undated") return null;
  const config = FRESHNESS[freshness];
  if (!config) return null; // unknown value from a newer backend
  const Icon = config.icon;
  return (
    <Badge
      className={cn("h-auto min-h-5 max-w-full whitespace-normal", config.className)}
      data-freshness={freshness}
    >
      <Icon aria-hidden data-icon="inline-start" />
      <span>{config.label}</span>
    </Badge>
  );
}
