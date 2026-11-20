import { apiRequest, segment } from "@/services/api";
import type {
  DocumentDeleteResponse,
  DocumentDetail,
  DocumentListParams,
  DocumentListResponse,
  DocumentUploadResponse,
} from "@/types/api";

const DOCUMENT_NOT_FOUND = "Document not found.";

/** GET /documents: paginated list of the shared knowledge base. */
export function listDocuments(params: DocumentListParams = {}, signal?: AbortSignal) {
  return apiRequest<DocumentListResponse>("/documents", {
    query: { status: params.status, limit: params.limit, offset: params.offset },
    signal,
  });
}

/** GET /documents/{id} */
export function getDocumentDetail(documentId: string, signal?: AbortSignal) {
  return apiRequest<DocumentDetail>(`/documents/${segment(documentId)}`, {
    errorMessages: { 404: DOCUMENT_NOT_FOUND },
    signal,
  });
}

/**
 * POST /documents/upload as multipart/form-data with the field `file`.
 * Ingestion runs synchronously on the server, so this resolves once the
 * document is fully indexed. Client-side extension and empty-file checks
 * happen in the UI (Phase 9) before this is called.
 *
 * 422 shows the backend's message (empty file, unsupported type, unreadable
 * content); 500 shows a generic message because its detail contains raw
 * exception text.
 */
export function uploadDocument(file: File, signal?: AbortSignal) {
  const formData = new FormData();
  formData.append("file", file, file.name);
  return apiRequest<DocumentUploadResponse>("/documents/upload", {
    method: "POST",
    formData,
    errorMessages: { 500: "Document upload failed. Please try a different file." },
    signal,
  });
}

/** DELETE /documents/{id}: removes the document and its chunks for all users. */
export function deleteDocument(documentId: string, signal?: AbortSignal) {
  return apiRequest<DocumentDeleteResponse>(`/documents/${segment(documentId)}`, {
    method: "DELETE",
    errorMessages: { 404: DOCUMENT_NOT_FOUND },
    signal,
  });
}
