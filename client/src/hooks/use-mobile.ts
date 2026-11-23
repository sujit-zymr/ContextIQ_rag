import * as React from "react"

const MOBILE_BREAKPOINT = 768
const QUERY = `(max-width: ${MOBILE_BREAKPOINT - 1}px)`

function subscribe(onChange: () => void) {
  const mql = window.matchMedia(QUERY)
  mql.addEventListener("change", onChange)
  return () => mql.removeEventListener("change", onChange)
}

const getSnapshot = () => window.matchMedia(QUERY).matches
// No viewport on the server: render the desktop layout until hydration.
const getServerSnapshot = () => false

/**
 * True below the `md` breakpoint (768px).
 * Adapted from the shadcn `use-mobile` hook to use useSyncExternalStore
 * instead of setting state inside an effect (react-hooks/set-state-in-effect).
 */
export function useIsMobile() {
  return React.useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)
}
