"use client";

import { type CSSProperties, type ReactNode, useState } from "react";

import { Header } from "@/components/layout/Header";
import { AppSidebar } from "@/components/layout/Sidebar";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";

/** Cookie written by the shadcn SidebarProvider when the sidebar is toggled. */
const SIDEBAR_COOKIE = "sidebar_state";

/** Plan §8.2: 260px expanded, 64px collapsed (icon-only). */
const SIDEBAR_WIDTHS = {
  "--sidebar-width": "260px",
  "--sidebar-width-icon": "64px",
} as CSSProperties;

/**
 * Restores the desktop collapsed/expanded preference. Safe to read during
 * render: the shell only renders on the client, after authentication.
 */
function readSidebarOpenPreference(): boolean {
  if (typeof document === "undefined") return true;
  const match = document.cookie.match(new RegExp(`(?:^|; )${SIDEBAR_COOKIE}=(true|false)`));
  return match ? match[1] === "true" : true;
}

/**
 * Authenticated app layout (plan §7.5): Sidebar | main content.
 * The Sources panel (right side) is added in Phase 8.
 */
export function AppShell({ children }: { children: ReactNode }) {
  const [defaultOpen] = useState(readSidebarOpenPreference);

  return (
    <SidebarProvider defaultOpen={defaultOpen} style={SIDEBAR_WIDTHS}>
      <AppSidebar />
      <SidebarInset className="min-w-0">
        <Header />
        <div className="flex min-h-0 flex-1 flex-col">{children}</div>
      </SidebarInset>
    </SidebarProvider>
  );
}
