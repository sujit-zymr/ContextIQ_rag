"use client";

import { usePathname } from "next/navigation";

import { SidebarTrigger } from "@/components/ui/sidebar";
import { useCurrentSession } from "@/hooks/useCurrentSession";

/** Title shown in the header for the current route. */
function useHeaderTitle(): string {
  const pathname = usePathname();
  const { sessionId, session } = useCurrentSession();
  if (pathname.startsWith("/documents")) return "Knowledge Base";
  if (sessionId) return session?.title ?? "Conversation";
  return "New chat";
}

/** Top bar (plan §7.5): sidebar toggle (drawer on mobile) and the page title. */
export function Header() {
  const title = useHeaderTitle();

  return (
    <header className="sticky top-0 z-10 flex h-16 shrink-0 items-center gap-2 border-b bg-background px-3 md:px-6">
      <SidebarTrigger aria-label="Toggle sidebar" className="-ml-1 text-muted-foreground md:-ml-3" />
      <h1 className="min-w-0 truncate text-lg font-semibold tracking-tight" title={title}>
        {title}
      </h1>
    </header>
  );
}
