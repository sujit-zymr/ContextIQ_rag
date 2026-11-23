"use client";

import { ChevronsUpDown, FileText, LogOut, Monitor, Moon, Plus, Sun } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "next-themes";

import { Logo } from "@/components/common/Logo";
import { SessionList } from "@/components/layout/SessionList";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
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

/** Centre the 32px icon buttons in the 64px collapsed rail (plan §8.2). */
const ICON_MODE_CENTER = "group-data-[collapsible=icon]:items-center";
/** Navigation rows: a little taller than the shadcn default, muted until active. */
const NAV_BUTTON = "h-9 text-sidebar-foreground/70 data-active:text-sidebar-accent-foreground";

/**
 * Left sidebar (plan §7.5): logo, New chat, Documents, recent conversations,
 * user menu. There is no separate "Chat" item: New chat and the conversation
 * list already lead to the chat pages.
 */
export function AppSidebar() {
  const pathname = usePathname();
  const { isMobile, setOpenMobile } = useSidebar();
  const resetChatUi = useChatUiStore((state) => state.reset);
  const closeOnMobile = () => {
    if (isMobile) setOpenMobile(false);
  };
  const onDocuments = pathname.startsWith("/documents");

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="h-16 justify-center">
        <SidebarMenu className={ICON_MODE_CENTER}>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              tooltip="ContextIQ"
              className="h-10 hover:bg-transparent active:bg-transparent group-data-[collapsible=icon]:p-0!"
            >
              <Link href="/chat" onClick={closeOnMobile}>
                {/* Logo without the tagline when expanded; the "C" mark in the 64px rail. */}
                <Logo variant="wordmark" className="h-9 group-data-[collapsible=icon]:hidden" priority />
                <Logo
                  variant="mark"
                  className="hidden size-8 group-data-[collapsible=icon]:inline-flex"
                />
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu aria-label="Main navigation" className={ICON_MODE_CENTER}>
              <SidebarMenuItem>
                <SidebarMenuButton asChild tooltip="New chat" className={NAV_BUTTON}>
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
              <SidebarMenuItem>
                <SidebarMenuButton
                  asChild
                  isActive={onDocuments}
                  tooltip="Documents"
                  className={NAV_BUTTON}
                >
                  <Link
                    href="/documents"
                    aria-current={onDocuments ? "page" : undefined}
                    onClick={closeOnMobile}
                  >
                    <FileText aria-hidden />
                    <span>Documents</span>
                  </Link>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup className="group-data-[collapsible=icon]:hidden">
          <SidebarGroupLabel className="text-[11px] font-medium tracking-wider uppercase">
            Recent
          </SidebarGroupLabel>
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

const THEME_OPTIONS = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
] as const;

/** Signed-in user's email, theme choice and the Log out action. */
function UserMenu() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const { isMobile } = useSidebar();
  const { theme, setTheme } = useTheme();
  const email = user?.email ?? "";
  const initial = email.charAt(0).toUpperCase() || "?";

  return (
    <SidebarMenu className={ICON_MODE_CENTER}>
      <SidebarMenuItem>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <SidebarMenuButton size="lg" tooltip={email} aria-label={`Account: ${email}`}>
              <Avatar className="size-8">
                <AvatarFallback className="bg-muted text-xs font-medium text-muted-foreground">
                  {initial}
                </AvatarFallback>
              </Avatar>
              <span className="min-w-0 flex-1 truncate text-sm font-medium">{email}</span>
              <ChevronsUpDown className="ml-auto text-muted-foreground" aria-hidden />
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
            <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
              Theme
            </DropdownMenuLabel>
            <DropdownMenuRadioGroup value={theme ?? "light"} onValueChange={setTheme}>
              {THEME_OPTIONS.map(({ value, label, icon: Icon }) => (
                <DropdownMenuRadioItem key={value} value={value}>
                  <Icon aria-hidden /> {label}
                </DropdownMenuRadioItem>
              ))}
            </DropdownMenuRadioGroup>
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
