/**
 * Centralized fetch client for the ContextIQ backend (plan §4.2).
 *
 * - Prefixes every path with NEXT_PUBLIC_API_BASE_URL.
 * - Attaches `Authorization: Bearer <token>` from localStorage on each call.
 * - Sends JSON, URL-encoded form (OAuth2 login) or multipart (upload) bodies.
 * - Normalizes every failure into an `ApiError` with a user-safe `message`.
 *   Raw backend details of 5xx responses (which can contain exception text and
 *   server paths) are never used as the message.
 * - On 401 for an authenticated request: clears the stored token and invokes
 *   the registered unauthorized handler (wired to the auth store in Phase 3).
 */

import { API_BASE_URL } from "@/lib/constants";
import { clearStoredToken, getStoredToken } from "@/lib/token-storage";
import type { ApiErrorBody, ValidationErrorItem } from "@/types/api";

// ─── Error type ──────────────────────────────────────────────────────────────

export type ApiErrorKind =
  /** The server could not be reached (offline, DNS, CORS, server down). */
  | "network"
  /** The server answered with a non-2xx status. */
  | "http"
  /** A 2xx response whose body was not the expected JSON. */
  | "parse"
  /** The request was cancelled through its AbortSignal. */
  | "aborted";

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  /** HTTP status, or 0 when no response was received. */
  readonly status: number;
  /** Raw `detail` from the response body, for debugging only. Never render it. */
  readonly detail: unknown;

  constructor(kind: ApiErrorKind, status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.detail = detail;
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}

/** User-facing messages from the plan's error matrix (§9). */
export const ERROR_MESSAGES = {
  network: "Could not connect to the ContextIQ server. Please try again.",
  sessionExpired: "Your session has expired. Please sign in again.",
  aiUnavailable: "The AI service is temporarily unavailable. Please try again.",
  serverError: "Something went wrong on the server. Please try again.",
  serviceUnavailable: "The ContextIQ server is not available right now. Please try again later.",
  unexpectedResponse: "The server returned an unexpected response. Please try again.",
  aborted: "The request was cancelled.",
} as const;

// ─── Unauthorized handling ───────────────────────────────────────────────────

type UnauthorizedHandler = () => void;

let unauthorizedHandler: UnauthorizedHandler | null = null;

/**
 * Registers the callback run after a 401 on an authenticated request (once the
 * stored token has been cleared). The auth store registers its logout here, so
 * this module does not import the store. Returns an unregister function.
 */
export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): () => void {
  unauthorizedHandler = handler;
  return () => {
    if (unauthorizedHandler === handler) unauthorizedHandler = null;
  };
}

// ─── Request ─────────────────────────────────────────────────────────────────

type HttpMethod = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

type QueryValue = string | number | boolean | null | undefined;

export interface RequestOptions {
  method?: HttpMethod;
  /** Query string parameters; `undefined` and `null` values are omitted. */
  query?: Record<string, QueryValue>;
  /** JSON body. Mutually exclusive with `form` and `formData`. */
  json?: unknown;
  /** application/x-www-form-urlencoded body (OAuth2 password flow). */
  form?: Record<string, string>;
  /** multipart/form-data body. The browser sets the boundary header itself. */
  formData?: FormData;
  /** Attach the bearer token. Default true; false for login/register. */
  auth?: boolean;
  /**
   * Per-status message overrides, e.g. `{ 404: "Conversation not found." }`.
   * Applied after the defaults, so they also replace 5xx messages.
   */
  errorMessages?: Partial<Record<number, string>>;
  signal?: AbortSignal;
}

/** Builds `<API_BASE_URL><path>?<query>` with encoded parameters. */
export function buildUrl(path: string, query?: Record<string, QueryValue>): string {
  const normalizedPath = path.startsWith("/") ? path : "/" + path;
  const url = API_BASE_URL + normalizedPath;
  if (!query) return url;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null) params.append(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${url}?${qs}` : url;
}

/** Encodes a dynamic path segment such as a session or document id. */
export function segment(value: string): string {
  return encodeURIComponent(value);
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", query, auth = true, errorMessages, signal } = options;

  const { headers, body } = buildBody(options);
  const token = auth ? getStoredToken() : null;
  if (token) headers.set("Authorization", "Bearer " + token);

  const response = await send(buildUrl(path, query), { method, headers, body, signal });
  const payload = await readBody(response);

  if (!response.ok) {
    throw toHttpError(response.status, payload, auth, errorMessages);
  }
  if (response.status === 204 || payload.kind === "empty") {
    return undefined as T;
  }
  if (payload.kind !== "json") {
    throw new ApiError("parse", response.status, ERROR_MESSAGES.unexpectedResponse, payload.value);
  }
  return payload.value as T;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function buildBody({ json, form, formData }: RequestOptions): { headers: Headers; body?: BodyInit } {
  const headers = new Headers({ Accept: "application/json" });
  if (json !== undefined) {
    headers.set("Content-Type", "application/json");
    return { headers, body: JSON.stringify(json) };
  }
  if (form) {
    headers.set("Content-Type", "application/x-www-form-urlencoded");
    return { headers, body: new URLSearchParams(form) };
  }
  // multipart: no Content-Type, fetch must add the boundary itself.
  return { headers, body: formData };
}

/** fetch() that converts transport failures into ApiError. */
async function send(url: string, init: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (error) {
    const aborted =
      init.signal?.aborted || (error instanceof DOMException && error.name === "AbortError");
    if (aborted) throw new ApiError("aborted", 0, ERROR_MESSAGES.aborted);
    throw new ApiError("network", 0, ERROR_MESSAGES.network);
  }
}

function toHttpError(
  status: number,
  payload: ParsedBody,
  auth: boolean,
  errorMessages?: Partial<Record<number, string>>,
): ApiError {
  // Only an authenticated request means "session expired". A 401 from the
  // login endpoint (auth: false) is a wrong-password error for the form.
  if (status === 401 && auth) {
    clearStoredToken();
    unauthorizedHandler?.();
  }
  // Only a FastAPI JSON body's `detail` can become the message. A non-JSON
  // body (e.g. an HTML page from a proxy) is kept for debugging only.
  const detail =
    payload.kind === "json" && isErrorBody(payload.value) ? payload.value.detail : undefined;
  const message = errorMessages?.[status] ?? defaultErrorMessage(status, detail, auth);
  return new ApiError("http", status, message, detail ?? payload.value);
}

type ParsedBody =
  | { kind: "json"; value: unknown }
  | { kind: "text"; value: string }
  | { kind: "empty"; value: null };

async function readBody(response: Response): Promise<ParsedBody> {
  let text: string;
  try {
    text = await response.text();
  } catch {
    return { kind: "empty", value: null };
  }
  if (!text) return { kind: "empty", value: null };
  try {
    return { kind: "json", value: JSON.parse(text) as unknown };
  } catch {
    return { kind: "text", value: text };
  }
}

function isErrorBody(value: unknown): value is ApiErrorBody {
  return typeof value === "object" && value !== null && "detail" in value;
}

function isValidationList(detail: unknown): detail is ValidationErrorItem[] {
  return (
    Array.isArray(detail) &&
    detail.every((item) => typeof item === "object" && item !== null && "msg" in item)
  );
}

/** Turns FastAPI's 422 list into one readable line, e.g. "password: String should have at least 12 characters". */
function formatValidationErrors(items: ValidationErrorItem[]): string {
  return items
    .slice(0, 3)
    .map((item) => {
      // loc looks like ["body", "password"]; drop the location prefix.
      const field = item.loc.filter((part) => !["body", "query", "path", "header"].includes(String(part))).join(".");
      return field ? `${field}: ${item.msg}` : item.msg;
    })
    .join("; ");
}

function defaultErrorMessage(status: number, detail: unknown, auth: boolean): string {
  if (status === 401 && auth) return ERROR_MESSAGES.sessionExpired;
  if (status === 502) return ERROR_MESSAGES.aiUnavailable;
  if (status === 503) return ERROR_MESSAGES.serviceUnavailable;
  if (status >= 500) return ERROR_MESSAGES.serverError;

  // 4xx details are produced by our own backend code and are safe to show.
  if (typeof detail === "string" && detail.trim()) return detail;
  if (isValidationList(detail) && detail.length > 0) return formatValidationErrors(detail);
  return `Request failed (${status}).`;
}
