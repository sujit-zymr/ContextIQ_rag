"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { CircleAlert } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";

import { AuthCard } from "@/components/auth/AuthCard";
import { PasswordInput } from "@/components/auth/PasswordInput";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Field,
  FieldDescription,
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner";
import { PASSWORD_MIN_LENGTH } from "@/lib/constants";
import { getErrorMessage, isToastError } from "@/lib/errors";
import { type RegisterValues, registerSchema } from "@/lib/validation/auth";
import { isApiError } from "@/services/api";
import { register as registerAccount } from "@/services/auth.service";
import { useAuthStore } from "@/store/useAuthStore";

/**
 * Plan §7.2. Registers, then signs in automatically; the GuestOnly guard then
 * redirects to /chat.
 */
export function RegisterForm() {
  const router = useRouter();
  const login = useAuthStore((state) => state.login);
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<RegisterValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: { email: "", password: "", confirmPassword: "" },
    mode: "onTouched",
  });

  const onSubmit = handleSubmit(async ({ email, password }) => {
    try {
      await registerAccount(email, password);
    } catch (error) {
      if (isToastError(error)) {
        toast.error(getErrorMessage(error));
      } else if (isApiError(error) && error.status === 409) {
        setError("email", { message: getErrorMessage(error) }, { shouldFocus: true });
      } else {
        // 422 from the backend (e.g. email it considers invalid).
        setError("root.server", { message: getErrorMessage(error) });
      }
      return;
    }

    try {
      await login(email, password);
    } catch {
      // The account exists; only the automatic sign-in failed.
      toast.success("Account created. Please sign in.");
      router.replace("/login");
    }
  });

  return (
    <AuthCard
      title="Create an account"
      description="Get started with ContextIQ."
      footer={
        <span>
          Already have an account?{" "}
          <Link href="/login" className="font-medium text-primary hover:underline">
            Sign in
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
            <FieldLabel htmlFor="register-email">Email</FieldLabel>
            <Input
              id="register-email"
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
            <FieldLabel htmlFor="register-password">Password</FieldLabel>
            <PasswordInput
              id="register-password"
              autoComplete="new-password"
              aria-invalid={Boolean(errors.password)}
              aria-describedby="register-password-hint"
              disabled={isSubmitting}
              {...register("password")}
            />
            {errors.password ? (
              <FieldError errors={[errors.password]} />
            ) : (
              <FieldDescription id="register-password-hint">
                At least {PASSWORD_MIN_LENGTH} characters.
              </FieldDescription>
            )}
          </Field>

          <Field data-invalid={Boolean(errors.confirmPassword)}>
            <FieldLabel htmlFor="register-confirm-password">Confirm password</FieldLabel>
            <PasswordInput
              id="register-confirm-password"
              autoComplete="new-password"
              aria-invalid={Boolean(errors.confirmPassword)}
              disabled={isSubmitting}
              {...register("confirmPassword")}
            />
            <FieldError errors={[errors.confirmPassword]} />
          </Field>

          <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? <Spinner /> : null}
            {isSubmitting ? "Creating account…" : "Create account"}
          </Button>
        </FieldGroup>
      </form>
    </AuthCard>
  );
}
