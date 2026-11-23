import { SUPPORTED_FILE_EXTENSIONS, SUPPORTED_FILE_TYPES_LABEL } from "@/lib/constants";

export type SupportedExtension = (typeof SUPPORTED_FILE_EXTENSIONS)[number];

export const UNSUPPORTED_FILE_MESSAGE = `Only ${SUPPORTED_FILE_TYPES_LABEL} files are supported.`;
export const EMPTY_FILE_MESSAGE = "The selected file is empty.";

/** Lower-case extension including the dot (".pdf"), or "" when there is none. */
export function getFileExtension(filename: string): string {
  const dot = filename.lastIndexOf(".");
  return dot > 0 ? filename.slice(dot).toLowerCase() : "";
}

export function isSupportedExtension(extension: string): extension is SupportedExtension {
  return (SUPPORTED_FILE_EXTENSIONS as readonly string[]).includes(extension);
}

/**
 * Client-side checks before POST /documents/upload (plan §7.7), mirroring the
 * backend's own 422 checks. Returns the error message, or null when valid.
 */
export function validateUploadFile(file: File): string | null {
  if (!isSupportedExtension(getFileExtension(file.name))) return UNSUPPORTED_FILE_MESSAGE;
  if (file.size === 0) return EMPTY_FILE_MESSAGE;
  return null;
}

/** Short type label shown next to a filename. */
export function getFileTypeLabel(filename: string): string {
  const extension = getFileExtension(filename);
  if (extension === ".md" || extension === ".markdown") return "MD";
  return extension ? extension.slice(1).toUpperCase() : "FILE";
}
