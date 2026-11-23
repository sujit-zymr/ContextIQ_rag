import type { Metadata } from "next";

import { LoginForm } from "@/components/auth/LoginForm";
import { GuestOnly } from "@/components/auth/RouteGuards";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return (
    <GuestOnly>
      <LoginForm />
    </GuestOnly>
  );
}
