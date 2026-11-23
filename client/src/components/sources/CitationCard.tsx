import { FileText, Layers } from "lucide-react";
import type { ReactNode } from "react";

import { FreshnessBadge } from "@/components/sources/FreshnessBadge";
import { getCompetingVersions } from "@/lib/citations";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { Citation } from "@/types/api";

/** DOM id of a card, so the panel can scroll to the clicked citation. */
export function citationCardId(messageId: string, sourceId: string) {
  return `source-${messageId}-${sourceId}`;
}

/**
 * One cited source (plan §7.6): label, document, page/section, version,
 * dates and freshness. Chunk text is not returned by the API, so none is shown.
 */
export function CitationCard({
  messageId,
  citation,
  isActive,
}: Readonly<{ messageId: string; citation: Citation; isActive: boolean }>) {
  const showFilename = citation.filename && citation.filename !== citation.title;
  const competing = getCompetingVersions(citation);

  const details: [string, ReactNode][] = [];
  if (citation.page !== null) details.push(["Page", citation.page]);
  if (citation.section) details.push(["Section", citation.section]);
  if (citation.version) details.push(["Version", citation.version]);
  if (citation.effective_date) details.push(["Effective", formatDate(citation.effective_date)]);
  if (citation.expiry_date) details.push(["Expires", formatDate(citation.expiry_date)]);
  if (citation.as_of_date) details.push(["Checked", formatDate(citation.as_of_date)]);

  return (
    <li
      id={citationCardId(messageId, citation.source_id)}
      data-active={isActive || undefined}
      aria-current={isActive || undefined}
      className={cn(
        "scroll-m-3 rounded-lg border bg-background/50 p-3 transition-colors duration-150 ease-out",
        "data-active:border-primary/60 data-active:bg-primary/5 data-active:ring-1 data-active:ring-primary/40",
      )}
    >
      <article aria-label={`Source ${citation.source_id}`} className="flex flex-col gap-2.5">
        <div className="flex items-start gap-2.5">
          <span className="mt-0.5 inline-flex h-5 shrink-0 items-center rounded-md bg-primary/15 px-1.5 text-[11px] font-semibold text-primary">
            {citation.source_id}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium break-words">{citation.title}</p>
            {showFilename ? (
              <p className="mt-0.5 flex items-center gap-1 text-xs text-muted-foreground">
                <FileText className="size-3 shrink-0" aria-hidden />
                <span className="truncate" title={citation.filename ?? undefined}>
                  {citation.filename}
                </span>
              </p>
            ) : null}
          </div>
        </div>

        <FreshnessBadge freshness={citation.source_freshness} />

        {details.length > 0 ? (
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
            {details.map(([label, value]) => (
              <div key={label} className="contents">
                <dt className="text-muted-foreground">{label}</dt>
                <dd className="min-w-0 break-words">{value}</dd>
              </div>
            ))}
          </dl>
        ) : null}

        {competing.length > 0 ? (
          <p className="flex gap-1.5 text-xs text-muted-foreground">
            <Layers className="mt-0.5 size-3 shrink-0" aria-hidden />
            <span>Versions found: {competing.join(", ")}</span>
          </p>
        ) : null}
      </article>
    </li>
  );
}
