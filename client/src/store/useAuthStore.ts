import { toast } from "sonner";
import { create } from "zustand";

import { getTokenExpiryMs, isTokenExpired } from "@/lib/jwt";
import { getQueryClient } from "@/lib/query-client";
import { clearStoredToken, getStoredToken, setStoredToken } from "@/lib/token-storage";
import { ERROR_MESSAGES } from "@/services/api";
import * as authService from "@/services/auth.service";
import { useChatUiStore } from "@/store/useChatUiStore";
import type { UserResponse } from "@/types/api";

/**
 * Authentication state (plan §6.2).
 *
 * - `initializing`: on first load, before the stored token has been checked.
 *   Server renders and prerenders always stay in this state.
 * - Redirects are not done here; `useAuthGuard` reacts to `status`.
 */
export type AuthStatus = "initializing" | "authenticated" | "unauthenticated";

/** `expired` shows a "session expired" toast; `user` is a normal sign-out. */
export type LogoutReason = "user" | "expired";

interface AuthState {
  status: AuthStatus;
  token: string | null;
  user: UserResponse | null;

  /** Validates the stored token once per page load. Safe to call repeatedly. */
  initialize: () => Promise<void>;
  /** Signs in, stores the token and loads the profile. Rejects with ApiError. */
  login: (email: string, password: string) => Promise<UserResponse>;
  logout: (reason?: LogoutReason) => void;
}

// Browser timers can't exceed 2^31-1 ms (~24.8 days).
const MAX_TIMEOUT_MS = 2_147_483_647;

let expiryTimer: ReturnType<typeof setTimeout> | undefined;
let initializePromise: Promise<void> | undefined;

function clearExpiryTimer(): void {
  if (expiryTimer !== undefined) clearTimeout(expiryTimer);
  expiryTimer = undefined;
}

/** Logs out when the JWT's `exp` passes, so an idle tab also returns to /login. */
function scheduleExpiry(token: string): void {
  clearExpiryTimer();
  const expiry = getTokenExpiryMs(token);
  if (expiry === null) return;
  const delay = Math.min(Math.max(expiry - Date.now(), 0), MAX_TIMEOUT_MS);
  expiryTimer = setTimeout(() => useAuthStore.getState().logout("expired"), delay);
}

export const useAuthStore = create<AuthState>()((set, get) => ({
  status: "initializing",
  token: null,
  user: null,

  initialize: () => {
    initializePromise ??= (async () => {
      const token = getStoredToken();
      if (!token || isTokenExpired(token)) {
        clearStoredToken();
        set({ status: "unauthenticated", token: null, user: null });
        return;
      }
      try {
        const user = await authService.getProfile();
        set({ status: "authenticated", token, user });
        scheduleExpiry(token);
      } catch {
        // 401 has already cleared the token via the API client. Any other
        // failure (e.g. server unreachable) also lands on the login page.
        get().logout("user");
      }
    })();
    return initializePromise;
  },

  login: async (email, password) => {
    const { access_token: token } = await authService.login(email, password);
    setStoredToken(token);
    try {
      const user = await authService.getProfile();
      // A previous user's cached data must never be shown to the next one.
      getQueryClient().clear();
      useChatUiStore.getState().reset();
      set({ status: "authenticated", token, user });
      scheduleExpiry(token);
      return user;
    } catch (error) {
      clearStoredToken();
      throw error;
    }
  },

  logout: (reason = "user") => {
    const wasAuthenticated = get().status === "authenticated";
    clearExpiryTimer();
    clearStoredToken();
    getQueryClient().clear();
    useChatUiStore.getState().reset();
    set({ status: "unauthenticated", token: null, user: null });
    // Several requests can 401 at once; toast only on the first.
    if (reason === "expired" && wasAuthenticated) {
      toast.error(ERROR_MESSAGES.sessionExpired);
    }
  },
}));
