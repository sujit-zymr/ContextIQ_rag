"use client";

import { useState } from "react";

import { DocumentUploadZone } from "@/components/documents/DocumentUploadZone";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

/**
 * Upload dialog (plan §7.7), used by the Documents page and by "Attach
 * document" in the chat input. It cannot be closed while the server is
 * indexing the file, because the result is reported here.
 */
export function UploadDocumentDialog({
  open,
  onOpenChange,
}: Readonly<{ open: boolean; onOpenChange: (open: boolean) => void }>) {
  const [busy, setBusy] = useState(false);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && busy) return;
        onOpenChange(next);
      }}
    >
      <DialogContent showCloseButton={!busy} className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Upload document</DialogTitle>
          <DialogDescription>
            The document is added to the shared knowledge base, available to all users.
          </DialogDescription>
        </DialogHeader>
        <DocumentUploadZone onBusyChange={setBusy} onUploaded={() => onOpenChange(false)} />
      </DialogContent>
    </Dialog>
  );
}
