"use client";

import { useRouter } from "next/navigation";
import { type ReactNode, useEffect } from "react";

import { PageLoader } from "@/components/common/PageLoader";
import { HOME_PATH, LOGIN_PATH, useAuthGuard, useGuestGuard } from "@/hooks/useAuthGuard";
import { useAuthStore } from "@/store/useAuthStore";

/**
 * Renders children only for signed-in users; others are sent to /login.
 * Nothing inside (including queries) renders until auth is confirmed, so no
 * query runs during Next.js prerendering.
 */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isReady } = useAuthGuard();
  return isReady ? children : <PageLoader />;
}

/** Renders children only for signed-out users; signed-in users go to /chat. */
export function GuestOnly({ children }: { children: ReactNode }) {
  const { isReady } = useGuestGuard();
  return isReady ? children : <PageLoader />;
}

/** `/`: sends users to /chat or /login once the stored session is checked. */
export function RootRedirect() {
  const router = useRouter();
  const status = useAuthStore((state) => state.status);

  useEffect(() => {
    if (status === "authenticated") router.replace(HOME_PATH);
    if (status === "unauthenticated") router.replace(LOGIN_PATH);
  }, [status, router]);

  return <PageLoader />;
}
