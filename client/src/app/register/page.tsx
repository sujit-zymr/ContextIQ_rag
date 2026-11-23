import type { Metadata } from "next";

import { RegisterForm } from "@/components/auth/RegisterForm";
import { GuestOnly } from "@/components/auth/RouteGuards";

export const metadata: Metadata = { title: "Create account" };

export default function RegisterPage() {
  return (
    <GuestOnly>
      <RegisterForm />
    </GuestOnly>
  );
}
