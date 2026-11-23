"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { CircleAlert } from "lucide-react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { AuthCard } from "@/components/auth/AuthCard";
import { PasswordInput } from "@/components/auth/PasswordInput";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field, FieldError, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { getErrorMessage, isToastError } from "@/lib/errors";
import { type LoginValues, loginSchema } from "@/lib/validation/auth";
import { useAuthStore } from "@/store/useAuthStore";

/**
 * Plan §7.1. On success the auth store becomes `authenticated` and the
 * GuestOnly guard redirects to /chat.
 */
export function LoginForm() {
  const login = useAuthStore((state) => state.login);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: "", password: "" },
    mode: "onTouched",
  });

  const onSubmit = handleSubmit(async ({ email, password }) => {
    try {
      await login(email, password);
    } catch (error) {
      if (isToastError(error)) {
        toast.error(getErrorMessage(error));
      } else {
        // 401 → "Incorrect email or password." (set in auth.service)
        setError("root.server", { message: getErrorMessage(error) });
      }
    }
  });

  return (
    <AuthCard
      title="Sign in"
      description="Welcome back. Sign in to ask questions about your documents."
      footer={
        <span>
          Don&apos;t have an account?{" "}
          <Link href="/register" className="font-medium text-primary hover:underline">
            Create one
          </Link>
        </span>
      }
    >
      <form onSubmit={onSubmit} noValidate>
        <FieldGroup>
          {errors.root?.server?.message ? (
            <Alert variant="destructive">
              <CircleAlert aria-hidden />
              <AlertDescription>{errors.root.server.message}</AlertDescription>
            </Alert>
          ) : null}

          <Field data-invalid={Boolean(errors.email)}>
            <FieldLabel htmlFor="login-email">Email</FieldLabel>
            <Input
              id="login-email"
              type="email"
              autoComplete="email"
              placeholder="you@company.com"
              aria-invalid={Boolean(errors.email)}
              disabled={isSubmitting}
              {...register("email")}
            />
            <FieldError errors={[errors.email]} />
          </Field>

          <Field data-invalid={Boolean(errors.password)}>
            <FieldLabel htmlFor="login-password">Password</FieldLabel>
            <PasswordInput
              id="login-password"
              autoComplete="current-password"
              aria-invalid={Boolean(errors.password)}
              disabled={isSubmitting}
              {...register("password")}
            />
            <FieldError errors={[errors.password]} />
          </Field>

          <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null}
            {isSubmitting ? "Signing in…" : "Sign in"}
          </Button>
        </FieldGroup>
      </form>
    </AuthCard>
  );
}
