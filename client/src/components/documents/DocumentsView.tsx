"use client";

import { ChevronLeft, ChevronRight, CircleAlert, FileText, RotateCw, Upload } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/common/EmptyState";
import { DeleteConfirmDialog } from "@/components/documents/DeleteConfirmDialog";
import { DocumentTable } from "@/components/documents/DocumentTable";
import { UploadDocumentDialog } from "@/components/documents/UploadDocumentDialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useDeleteDocument, useDocumentsQuery } from "@/hooks/queries/useDocuments";
import { DOCUMENTS_PAGE_SIZE } from "@/lib/constants";
import { getErrorMessage } from "@/lib/errors";
import type { DocumentSummary } from "@/types/api";

/** /documents (plan §7.7): the shared knowledge base. */
export function DocumentsView() {
  const [offset, setOffset] = useState(0);
  const { data, isPending, isError, error, refetch, isFetching } = useDocumentsQuery({
    limit: DOCUMENTS_PAGE_SIZE,
    offset,
  });
  const { mutate: deleteDocument } = useDeleteDocument();

  const [uploadOpen, setUploadOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<DocumentSummary | null>(null);

  const askDelete = (document: DocumentSummary) => {
    setDeleteTarget(document);
    setDeleteOpen(true);
  };

  const confirmDelete = (document: DocumentSummary) => {
    setDeleteOpen(false);
    // The row disappears at once (optimistic); it comes back if the delete fails.
    const wasLastOnPage = data?.items.length === 1 && offset > 0;
    deleteDocument(document.id, {
      onSuccess: (response) => {
        toast.success(response.message);
        if (wasLastOnPage) setOffset((current) => Math.max(0, current - DOCUMENTS_PAGE_SIZE));
      },
      onError: (deleteError) => toast.error(getErrorMessage(deleteError)),
    });
  };

  const uploadButton = (
    <Button onClick={() => setUploadOpen(true)}>
      <Upload aria-hidden /> Upload document
    </Button>
  );

  const renderBody = () => {
    if (data) {
      if (data.total === 0) {
        return (
          <EmptyState
            icon={FileText}
            title="No documents yet."
            description="Upload your first document to get started."
            action={uploadButton}
          />
        );
      }
      return (
        <>
          <DocumentTable documents={data.items} onDelete={askDelete} />
          {/* Range comes from the page actually shown: while the next page loads,
              the previous one stays visible (keepPreviousData). */}
          <Pagination
            offset={data.offset}
            shown={data.items.length}
            pageSize={DOCUMENTS_PAGE_SIZE}
            total={data.total}
            onChange={setOffset}
            disabled={isFetching}
          />
        </>
      );
    }
    if (isError) {
      return (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border p-10 text-center">
          <CircleAlert className="size-8 text-destructive" aria-hidden />
          <p className="text-sm text-muted-foreground">{getErrorMessage(error)}</p>
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RotateCw aria-hidden /> Try again
          </Button>
        </div>
      );
    }
    if (isPending) return <TableSkeleton />;
    return null;
  };

  return (
    <div className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-6 md:px-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-semibold tracking-tight">Documents</h2>
          <p className="text-sm text-muted-foreground">
            Documents here are shared by all users and used to answer everyone&apos;s questions.
            {data && data.total > 0 ? ` ${data.total.toLocaleString()} ${data.total === 1 ? "document" : "documents"}.` : null}
          </p>
        </div>
        {data && data.total > 0 ? uploadButton : null}
      </div>

      {renderBody()}

      <UploadDocumentDialog open={uploadOpen} onOpenChange={setUploadOpen} />

      <DeleteConfirmDialog
        open={deleteOpen}
        document={deleteTarget}
        onOpenChange={setDeleteOpen}
        onConfirm={confirmDelete}
      />
    </div>
  );
}

function Pagination({
  offset,
  shown,
  pageSize,
  total,
  onChange,
  disabled,
}: Readonly<{
  offset: number;
  shown: number;
  pageSize: number;
  total: number;
  onChange: (offset: number) => void;
  disabled: boolean;
}>) {
  if (total <= pageSize) return null;
  const from = offset + 1;
  const to = offset + shown;
  return (
    <nav aria-label="Documents pages" className="flex items-center justify-between gap-3 text-sm">
      <p className="text-muted-foreground">
        {from}–{to} of {total.toLocaleString()}
      </p>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange(Math.max(0, offset - pageSize))}
          disabled={disabled || offset === 0}
        >
          <ChevronLeft aria-hidden /> Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange(offset + pageSize)}
          disabled={disabled || to >= total}
        >
          Next <ChevronRight aria-hidden />
        </Button>
      </div>
    </nav>
  );
}

function TableSkeleton() {
  return (
    <div className="flex flex-col gap-3 rounded-xl border p-4" aria-busy="true">
      <span className="sr-only">Loading documents…</span>
      {[0, 1, 2, 3].map((row) => (
        <div key={row} className="flex items-center gap-3">
          <Skeleton className="h-8 w-11 rounded-md" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-5 w-24 rounded-full" />
          <Skeleton className="hidden h-4 w-20 md:block" />
        </div>
      ))}
    </div>
  );
}
