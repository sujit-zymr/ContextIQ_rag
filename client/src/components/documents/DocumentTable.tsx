import { Trash2 } from "lucide-react";

import { DocumentStatusBadge } from "@/components/documents/DocumentStatusBadge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { getFileTypeLabel } from "@/lib/documents";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { DocumentSummary } from "@/types/api";

const TYPE_COLORS: Record<string, string> = {
  PDF: "bg-destructive/10 text-destructive",
  DOCX: "bg-info/10 text-info",
  MD: "bg-success/10 text-success",
};

/** File type tag by extension (PDF, DOCX, TXT, MD). Decorative: the filename includes it. */
function FileTypeTag({ filename }: Readonly<{ filename: string }>) {
  const label = getFileTypeLabel(filename);
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex h-8 w-11 shrink-0 items-center justify-center rounded-md text-[10px] font-semibold tracking-wide",
        TYPE_COLORS[label] ?? "bg-muted text-muted-foreground",
      )}
    >
      {label}
    </span>
  );
}

function chunkLabel(count: number) {
  return `${count.toLocaleString()} ${count === 1 ? "chunk" : "chunks"}`;
}

/**
 * Shared knowledge-base documents (plan §7.7): type, filename, status, chunks,
 * upload date, delete. On small screens status, chunks and date move under
 * the filename so it keeps most of the width.
 */
export function DocumentTable({
  documents,
  onDelete,
}: Readonly<{ documents: DocumentSummary[]; onDelete: (document: DocumentSummary) => void }>) {
  return (
    <div className="overflow-hidden rounded-xl border bg-card">
      <Table className="table-fixed">
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="pl-4">Document</TableHead>
            <TableHead className="hidden w-32 sm:table-cell">Status</TableHead>
            <TableHead className="hidden w-24 text-right sm:table-cell">Chunks</TableHead>
            <TableHead className="hidden w-32 md:table-cell">Uploaded</TableHead>
            <TableHead className="w-14 pr-4">
              <span className="sr-only">Actions</span>
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {documents.map((doc) => (
            <TableRow key={doc.id} data-document-id={doc.id}>
              <TableCell className="pl-4">
                <div className="flex min-w-0 items-center gap-3">
                  <FileTypeTag filename={doc.filename} />
                  <div className="min-w-0">
                    <p className="truncate font-medium" title={doc.filename}>
                      {doc.filename}
                    </p>
                    {/* Chunks + date for screens where their columns are hidden. */}
                    <p className="truncate text-xs text-muted-foreground md:hidden">
                      <span className="sm:hidden">{chunkLabel(doc.chunk_count)} · </span>
                      {formatDate(doc.created_at)}
                    </p>
                    {/* Status for phones, where its column is hidden. */}
                    <div className="mt-1 sm:hidden">
                      <DocumentStatusBadge status={doc.status} />
                    </div>
                    {doc.status === "failed" && doc.status_message ? (
                      <p className="truncate text-xs text-destructive" title={doc.status_message}>
                        {doc.status_message}
                      </p>
                    ) : null}
                  </div>
                </div>
              </TableCell>
              <TableCell className="hidden sm:table-cell">
                <DocumentStatusBadge status={doc.status} />
              </TableCell>
              <TableCell className="hidden text-right tabular-nums sm:table-cell">
                {doc.chunk_count.toLocaleString()}
              </TableCell>
              <TableCell className="hidden text-muted-foreground md:table-cell">
                <time dateTime={doc.created_at}>{formatDate(doc.created_at)}</time>
              </TableCell>
              <TableCell className="pr-4 text-right">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                  onClick={() => onDelete(doc)}
                  aria-label={`Delete ${doc.filename}`}
                >
                  <Trash2 aria-hidden />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
