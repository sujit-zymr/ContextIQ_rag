import { Suspense } from "react";

import { RequireAuth } from "@/components/auth/RouteGuards";
import { PageLoader } from "@/components/common/PageLoader";
import { AppShell } from "@/components/layout/AppShell";

/**
 * Layout for all signed-in screens (/chat, /chat/[id], /documents).
 * Suspense: the shell reads the URL (usePathname/useParams), which suspends
 * during prerendering on routes with unknown dynamic params (Cache Components).
 */
export default function AppLayout({ children }: LayoutProps<"/">) {
  return (
    <Suspense fallback={<PageLoader />}>
      <RequireAuth>
        <AppShell>{children}</AppShell>
      </RequireAuth>
    </Suspense>
  );
}
