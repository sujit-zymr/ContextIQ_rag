"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { type AuthStatus, useAuthStore } from "@/store/useAuthStore";

export const LOGIN_PATH = "/login";
export const HOME_PATH = "/chat";

interface GuardResult {
  status: AuthStatus;
  /** True once the page may render its content. */
  isReady: boolean;
}

/**
 * For protected pages (/chat, /chat/[id], /documents), plan §6.4.
 *
 * Render the page's content only when `isReady` is true. Until then the
 * stored token is still being checked (or the redirect is happening), and no
 * query should run. That also keeps queries out of Next.js prerendering.
 */
export function useAuthGuard(): GuardResult {
  const router = useRouter();
  const status = useAuthStore((state) => state.status);

  useEffect(() => {
    if (status === "unauthenticated") router.replace(LOGIN_PATH);
  }, [status, router]);

  return { status, isReady: status === "authenticated" };
}

/**
 * For guest-only pages (/login, /register): signed-in users go to /chat.
 * `isReady` is true when the form should be shown.
 */
export function useGuestGuard(): GuardResult {
  const router = useRouter();
  const status = useAuthStore((state) => state.status);

  useEffect(() => {
    if (status === "authenticated") router.replace(HOME_PATH);
  }, [status, router]);

  return { status, isReady: status === "unauthenticated" };
}
