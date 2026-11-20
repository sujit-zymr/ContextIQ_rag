"use client";

import { ChevronsUpDown, FileText, LogOut, MessageSquare, Plus } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { Logo } from "@/components/common/Logo";
import { SessionList } from "@/components/layout/SessionList";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from "@/components/ui/sidebar";
import { useAuthStore } from "@/store/useAuthStore";
import { useChatUiStore } from "@/store/useChatUiStore";

const ACTIVE_ITEM = "data-[active=true]:shadow-[inset_2px_0_0_var(--sidebar-primary)]";
/** Centre the 32px icon buttons in the 64px collapsed rail (plan §8.2). */
const ICON_MODE_CENTER = "group-data-[collapsible=icon]:items-center";

const NAV_ITEMS = [
  { href: "/chat", label: "Chat", icon: MessageSquare, match: (p: string) => p.startsWith("/chat") },
  {
    href: "/documents",
    label: "Documents",
    icon: FileText,
    match: (p: string) => p.startsWith("/documents"),
  },
] as const;

/** Left sidebar (plan §7.5): logo, New Chat, navigation, recent conversations, user menu. */
export function AppSidebar() {
  const pathname = usePathname();
  const { isMobile, setOpenMobile } = useSidebar();
  const resetChatUi = useChatUiStore((state) => state.reset);
  const closeOnMobile = () => {
    if (isMobile) setOpenMobile(false);
  };

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <SidebarMenu className={ICON_MODE_CENTER}>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" asChild tooltip="ContextIQ">
              <Link href="/chat" onClick={closeOnMobile}>
                <Logo wordmarkClassName="group-data-[collapsible=icon]:hidden" />
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              tooltip="New chat"
              className="bg-primary text-primary-foreground hover:bg-primary-hover hover:text-primary-foreground"
            >
              <Link
                href="/chat"
                onClick={() => {
                  resetChatUi();
                  closeOnMobile();
                }}
              >
                <Plus aria-hidden />
                <span>New chat</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu aria-label="Main navigation" className={ICON_MODE_CENTER}>
              {NAV_ITEMS.map(({ href, label, icon: Icon, match }) => {
                const isActive = match(pathname);
                return (
                  <SidebarMenuItem key={href}>
                    <SidebarMenuButton asChild isActive={isActive} tooltip={label} className={ACTIVE_ITEM}>
                      <Link
                        href={href}
                        aria-current={isActive ? "page" : undefined}
                        onClick={closeOnMobile}
                      >
                        <Icon aria-hidden />
                        <span>{label}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="group-data-[collapsible=icon]:hidden">
          <SidebarGroupLabel>Recent conversations</SidebarGroupLabel>
          <SidebarGroupContent>
            <SessionList />
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <UserMenu />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

/** Signed-in user's email and the Log out action. */
function UserMenu() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const { isMobile } = useSidebar();
  const email = user?.email ?? "";
  const initial = email.charAt(0).toUpperCase() || "?";

  return (
    <SidebarMenu className={ICON_MODE_CENTER}>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton size="lg" tooltip={email} aria-label={`Account: ${email}`}>
              <Avatar className="size-8 rounded-lg">
                <AvatarFallback className="rounded-lg bg-primary/15 text-primary">
                  {initial}
                </AvatarFallback>
              </Avatar>
              <span className="min-w-0 flex-1 truncate text-sm">{email}</span>
              <ChevronsUpDown className="ml-auto" aria-hidden />
            </SidebarMenuButton>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            side={isMobile ? "top" : "right"}
            align="end"
            className="min-w-56"
          >
            <DropdownMenuLabel className="truncate font-normal text-muted-foreground">
              {email}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onSelect={() => logout("user")}>
              <LogOut aria-hidden /> Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </SidebarMenuItem>
    </SidebarMenu>
  );
}
