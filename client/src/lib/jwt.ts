/**
 * Reads the `exp` claim (seconds since epoch) from a JWT and returns it in
 * milliseconds, or null if the token cannot be decoded.
 *
 * This does NOT verify the signature. It is only used to schedule a client-side
 * logout when the token expires; the backend still validates every request.
 */
export function getTokenExpiryMs(token: string): number | null {
  const payload = token.split(".")[1];
  if (!payload) return null;
  try {
    const base64 = payload.replaceAll("-", "+").replaceAll("_", "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    const claims: unknown = JSON.parse(atob(padded));
    if (typeof claims !== "object" || claims === null) return null;
    const exp = (claims as { exp?: unknown }).exp;
    return typeof exp === "number" && Number.isFinite(exp) ? exp * 1000 : null;
  } catch {
    return null;
  }
}

/** True when the token's `exp` has passed (with a small clock-skew margin). */
export function isTokenExpired(token: string, now: number = Date.now(), skewMs = 5_000): boolean {
  const expiry = getTokenExpiryMs(token);
  return expiry !== null && expiry - skewMs <= now;
}
