"use client";

import { usePathname } from "next/navigation";

import { Separator } from "@/components/ui/separator";
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
    <header className="sticky top-0 z-10 flex h-14 shrink-0 items-center gap-2 border-b bg-background/95 px-3 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <SidebarTrigger aria-label="Toggle sidebar" />
      <Separator orientation="vertical" className="mr-1 data-[orientation=vertical]:h-4" />
      <h1 className="min-w-0 truncate text-sm font-medium" title={title}>
        {title}
      </h1>
    </header>
  );
}
