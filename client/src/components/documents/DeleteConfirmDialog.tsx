"use client";

import { Trash2 } from "lucide-react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogMedia,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import type { DocumentSummary } from "@/types/api";

/**
 * Confirms deleting a document from the SHARED knowledge base (plan §7.7).
 * `document` is kept while closing so the text doesn't change during the
 * close animation; `onConfirm` runs the delete.
 */
export function DeleteConfirmDialog({
  open,
  document,
  onConfirm,
  onOpenChange,
}: Readonly<{
  open: boolean;
  document: DocumentSummary | null;
  onConfirm: (document: DocumentSummary) => void;
  onOpenChange: (open: boolean) => void;
}>) {
  return (
    <AlertDialog open={open} onOpenChange={onOpenChange}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogMedia className="bg-destructive/10 text-destructive">
            <Trash2 aria-hidden />
          </AlertDialogMedia>
          <AlertDialogTitle className="break-all">Delete {document?.filename}?</AlertDialogTitle>
          <AlertDialogDescription>
            This will remove the document and all its indexed chunks from the shared knowledge
            base for all users. This cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            onClick={() => {
              if (document) onConfirm(document);
            }}
          >
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
