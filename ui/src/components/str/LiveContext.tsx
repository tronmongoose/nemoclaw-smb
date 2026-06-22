/** Global DEMO/LIVE state for the STR views.
 *
 * Every STR API call threads the current toggle through as a `live` query
 * param. In LIVE mode reasoning results carry a real model id + latency; in
 * DEMO mode they carry the deterministic cached trace. The toggle is the
 * single source of truth a viewer flips to see the system is real, not canned.
 *
 * Exports:
 *   LiveProvider     context provider wrapping the STR view tree
 *   useLive()        read { live, setLive }
 *   liveParam(live)  build the "?live=true|false" query suffix
 */

import { createContext, useContext, useState, ReactNode } from "react";

interface LiveState {
  live: boolean;
  setLive: (v: boolean) => void;
}

const LiveCtx = createContext<LiveState>({ live: false, setLive: () => {} });

export function LiveProvider({ children }: { children: ReactNode }) {
  const [live, setLive] = useState(true);
  return <LiveCtx.Provider value={{ live, setLive }}>{children}</LiveCtx.Provider>;
}

export function useLive(): LiveState {
  return useContext(LiveCtx);
}

/** Return the query suffix that threads the toggle into a request path. */
export function liveParam(live: boolean): string {
  return `?live=${live ? "true" : "false"}`;
}
