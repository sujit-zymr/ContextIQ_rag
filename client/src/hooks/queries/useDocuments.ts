"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import {
  deleteDocument,
  getDocumentDetail,
  listDocuments,
  uploadDocument,
} from "@/services/document.service";
import type { DocumentListParams, DocumentListResponse } from "@/types/api";

/** While any listed document is still being ingested, refresh the list this often. */
const PROCESSING_REFETCH_MS = 5000;

/**
 * GET /documents. The previous page stays visible while the next one loads,
 * and the list refreshes itself while a document is `queued` or `processing`.
 */
export function useDocumentsQuery(params: DocumentListParams = {}) {
  return useQuery({
    queryKey: queryKeys.documents.list(params),
    queryFn: ({ signal }) => listDocuments(params, signal),
    placeholderData: keepPreviousData,
    refetchInterval: (query) =>
      query.state.data?.items.some((doc) => doc.status === "processing" || doc.status === "queued")
        ? PROCESSING_REFETCH_MS
        : false,
  });
}

/** GET /documents/{id}. Pass null to skip. */
export function useDocumentDetailQuery(documentId: string | null) {
  return useQuery({
    queryKey: queryKeys.documents.detail(documentId ?? ""),
    queryFn: ({ signal }) => getDocumentDetail(documentId ?? "", signal),
    enabled: Boolean(documentId),
  });
}

/** POST /documents/upload, then refresh every document list. */
export function useUploadDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => uploadDocument(file),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.documents.all }),
  });
}

/** DELETE /documents/{id}, removing the row from every cached list immediately. */
export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (documentId: string) => deleteDocument(documentId),

    onMutate: async (documentId) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.documents.lists });
      const previousLists = queryClient.getQueriesData<DocumentListResponse>({
        queryKey: queryKeys.documents.lists,
      });
      queryClient.setQueriesData<DocumentListResponse>(
        { queryKey: queryKeys.documents.lists },
        (old) => {
          if (!old?.items.some((doc) => doc.id === documentId)) return old;
          return {
            ...old,
            total: Math.max(old.total - 1, 0),
            items: old.items.filter((doc) => doc.id !== documentId),
          };
        },
      );
      return { previousLists };
    },

    onError: (_error, _documentId, context) => {
      for (const [key, data] of context?.previousLists ?? []) {
        queryClient.setQueryData(key, data);
      }
    },

    onSuccess: (_response, documentId) => {
      queryClient.removeQueries({ queryKey: queryKeys.documents.detail(documentId) });
    },

    onSettled: () => queryClient.invalidateQueries({ queryKey: queryKeys.documents.lists }),
  });
}
