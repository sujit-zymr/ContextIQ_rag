"use client";

import { LogOut } from "lucide-react";

import { Logo } from "@/components/common/Logo";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuthStore } from "@/store/useAuthStore";

/** TEMPORARY (Phase 4): replaced by the New Chat screen in Phase 6. */
export function ChatPlaceholder() {
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);

  return (
    <main className="flex flex-1 flex-col items-center justify-center gap-8 px-4 py-10">
      <Logo />
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>You&apos;re signed in</CardTitle>
          <CardDescription>
            Signed in as <span className="font-medium text-foreground">{user?.email}</span>.
            The chat interface arrives in a later phase.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="outline" className="w-full" onClick={() => logout("user")}>
            <LogOut aria-hidden /> Log out
          </Button>
        </CardContent>
      </Card>
    </main>
  );
}
