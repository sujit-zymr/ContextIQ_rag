"use client";

import { CircleAlert, Upload } from "lucide-react";
import { type DragEvent, useId, useState } from "react";
import { toast } from "sonner";

import { Spinner } from "@/components/ui/spinner";
import { useUploadDocument } from "@/hooks/queries/useDocuments";
import { SUPPORTED_FILE_EXTENSIONS, SUPPORTED_FILE_TYPES_LABEL } from "@/lib/constants";
import { validateUploadFile } from "@/lib/documents";
import { getErrorMessage } from "@/lib/errors";
import { cn } from "@/lib/utils";
import type { DocumentUploadResponse } from "@/types/api";

const ACCEPT = SUPPORTED_FILE_EXTENSIONS.join(",");

/**
 * Drag-and-drop area / file picker that uploads one document (plan §7.7).
 * Extension and empty-file problems are shown inline before anything is
 * sent; server and network errors are shown as toasts (plan §9).
 */
export function DocumentUploadZone({
  onUploaded,
  onBusyChange,
}: Readonly<{
  onUploaded: (response: DocumentUploadResponse) => void;
  onBusyChange?: (busy: boolean) => void;
}>) {
  const inputId = useId();
  const errorId = useId();
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadingName, setUploadingName] = useState<string | null>(null);
  const { mutate: upload } = useUploadDocument();

  const start = (file: File | undefined) => {
    if (!file || uploadingName) return;
    const problem = validateUploadFile(file);
    setError(problem);
    if (problem) return;

    setUploadingName(file.name);
    onBusyChange?.(true);
    upload(file, {
      onSuccess: (response) => {
        toast.success(response.message);
        onUploaded(response);
      },
      onError: (uploadError) => toast.error(getErrorMessage(uploadError)),
      onSettled: () => {
        setUploadingName(null);
        onBusyChange?.(false);
      },
    });
  };

  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragging(false);
    if (event.dataTransfer.files.length > 1) {
      setError("Please upload one file at a time.");
      return;
    }
    start(event.dataTransfer.files[0]);
  };

  if (uploadingName) {
    return (
      <div
        className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed bg-muted/30 p-8 text-center"
        aria-live="polite"
      >
        <Spinner className="size-6 text-primary" />
        <div className="flex max-w-full flex-col gap-1">
          <p className="truncate text-sm font-medium" title={uploadingName}>
            Uploading {uploadingName}
          </p>
          <p className="text-xs text-muted-foreground">
            The document is indexed during upload. Large files can take a minute.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <label
        htmlFor={inputId}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        data-dragging={dragging || undefined}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border border-dashed p-8 text-center transition-colors duration-150 ease-out",
          "hover:border-primary/60 hover:bg-primary/5",
          "has-[input:focus-visible]:ring-2 has-[input:focus-visible]:ring-ring",
          "data-dragging:border-primary data-dragging:bg-primary/10",
          error && "border-destructive/60",
        )}
      >
        <span className="flex size-10 items-center justify-center rounded-lg bg-primary/15 text-primary">
          <Upload className="size-5" aria-hidden />
        </span>
        <span className="flex flex-col gap-1">
          <span className="text-sm font-medium">
            Drag and drop a file here, or <span className="text-primary">browse</span>
          </span>
          <span className="text-xs text-muted-foreground">{SUPPORTED_FILE_TYPES_LABEL}</span>
        </span>
        <input
          id={inputId}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          aria-label="Choose a document to upload"
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          onChange={(event) => {
            start(event.target.files?.[0]);
            event.target.value = ""; // allow picking the same file again
          }}
        />
      </label>
      {error ? (
        <p id={errorId} role="alert" className="flex items-center gap-1.5 text-sm text-destructive">
          <CircleAlert className="size-4 shrink-0" aria-hidden />
          {error}
        </p>
      ) : null}
    </div>
  );
}
