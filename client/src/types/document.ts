/**
 * UI-layer document types. These are not sent to or returned by the backend.
 */

/** File categories accepted by POST /documents/upload, used for icons and labels. */
export type DocumentFileKind = "pdf" | "docx" | "txt" | "markdown";

/** Client-side upload validation failures (checked before any request is sent). */
export type UploadValidationError = "unsupported_extension" | "empty_file";
