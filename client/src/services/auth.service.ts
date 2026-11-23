import { apiRequest } from "@/services/api";
import type { TokenResponse, UserResponse } from "@/types/api";

/** POST /auth/register: creates an account. Does not sign in. */
export function register(email: string, password: string, signal?: AbortSignal) {
  return apiRequest<UserResponse>("/auth/register", {
    method: "POST",
    json: { email, password },
    auth: false,
    errorMessages: { 409: "An account with this email already exists." },
    signal,
  });
}

/**
 * POST /auth/token: OAuth2 password flow. The body is form-encoded, NOT JSON,
 * and the email goes in the field named `username`.
 *
 * Returns the token only; storing it is the auth store's job (Phase 3).
 */
export function login(email: string, password: string, signal?: AbortSignal) {
  return apiRequest<TokenResponse>("/auth/token", {
    method: "POST",
    form: { username: email, password },
    auth: false,
    errorMessages: { 401: "Incorrect email or password." },
    signal,
  });
}

/** GET /auth/me: the profile for the stored token. A 401 triggers logout. */
export function getProfile(signal?: AbortSignal) {
  return apiRequest<UserResponse>("/auth/me", { signal });
}
