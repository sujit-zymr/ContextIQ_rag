"use client";

import { RotateCw } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
  useSidebar,
} from "@/components/ui/sidebar";
import { useSessionsQuery } from "@/hooks/queries/useSessions";
import { useCurrentSessionId } from "@/hooks/useCurrentSession";

const SKELETON_ROWS = 5;

/**
 * "Recent" conversations (plan §7.5): every session of the user, newest
 * activity first, including `archived` ones (the backend archives all but the
 * most recently used session). Titles only, as plain text rows.
 */
export function SessionList() {
  const { data: sessions, isPending, isError, refetch, isFetching } = useSessionsQuery();
  const currentSessionId = useCurrentSessionId();
  const { isMobile, setOpenMobile } = useSidebar();

  if (isPending) {
    return (
      <SidebarMenu aria-busy="true" aria-label="Loading conversations">
        {Array.from({ length: SKELETON_ROWS }, (_, i) => (
          <SidebarMenuItem key={i}>
            <SidebarMenuSkeleton />
          </SidebarMenuItem>
        ))}
      </SidebarMenu>
    );
  }

  if (isError) {
    return (
      <div className="flex flex-col items-start gap-2 px-2 py-1 text-xs text-muted-foreground">
        <p>Couldn&apos;t load conversations.</p>
        <Button variant="outline" size="xs" onClick={() => refetch()} disabled={isFetching}>
          <RotateCw aria-hidden /> Retry
        </Button>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <p className="px-2 py-1 text-xs text-muted-foreground">
        No conversations yet. Ask your first question to start one.
      </p>
    );
  }

  return (
    <SidebarMenu>
      {sessions.map((session) => {
        const isActive = session.id === currentSessionId;
        return (
          <SidebarMenuItem key={session.id}>
            <SidebarMenuButton
              asChild
              isActive={isActive}
              className="h-8 text-[13px] text-sidebar-foreground/70 data-active:text-sidebar-accent-foreground"
            >
              <Link
                href={`/chat/${session.id}`}
                aria-current={isActive ? "page" : undefined}
                title={session.title}
                onClick={() => isMobile && setOpenMobile(false)}
              >
                <span>{session.title}</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        );
      })}
    </SidebarMenu>
  );
}
