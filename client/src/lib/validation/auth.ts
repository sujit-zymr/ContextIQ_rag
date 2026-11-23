import { z } from "zod";

import { PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH } from "@/lib/constants";

/** Mirrors the backend rules in server/app/api/schemas.py (RegisterRequest). */
const email = z
  .string()
  .trim()
  .min(1, "Email is required.")
  .pipe(z.email("Enter a valid email address."));

export const loginSchema = z.object({
  email,
  // Only "required" on login: the backend decides whether the password is right.
  password: z.string().min(1, "Password is required."),
});

export const registerSchema = z
  .object({
    email,
    password: z
      .string()
      .min(PASSWORD_MIN_LENGTH, `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`)
      .max(PASSWORD_MAX_LENGTH, `Password must be at most ${PASSWORD_MAX_LENGTH} characters.`),
    confirmPassword: z.string().min(1, "Please confirm your password."),
  })
  .refine((values) => values.password === values.confirmPassword, {
    path: ["confirmPassword"],
    message: "Passwords do not match.",
  });

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
