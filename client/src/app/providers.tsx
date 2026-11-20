"use client";

import { QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { type ReactNode, useEffect } from "react";

import { TOKEN_STORAGE_KEY } from "@/lib/constants";
import { getQueryClient } from "@/lib/query-client";
import { setUnauthorizedHandler } from "@/services/api";
import { useAuthStore } from "@/store/useAuthStore";

/**
 * Client-side app wiring:
 * - TanStack Query provider (one browser-wide client).
 * - Auth bootstrap: connects the API client's 401 handling to logout, validates
 *   the stored token once, and signs this tab out when another tab signs out.
 */
export function Providers({ children }: { children: ReactNode }) {
  useEffect(() => {
    const unregister = setUnauthorizedHandler(() =>
      useAuthStore.getState().logout("expired"),
    );
    void useAuthStore.getState().initialize();

    const onStorage = (event: StorageEvent) => {
      if (event.key === TOKEN_STORAGE_KEY && event.newValue === null) {
        useAuthStore.getState().logout("user");
      }
    };
    window.addEventListener("storage", onStorage);

    return () => {
      unregister();
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  return (
    <QueryClientProvider client={getQueryClient()}>
      {children}
      {/* Renders only in development; replaced by a no-op in production builds. */}
      <ReactQueryDevtools initialIsOpen={false} buttonPosition="bottom-left" />
    </QueryClientProvider>
  );
}
