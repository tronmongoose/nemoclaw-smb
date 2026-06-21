/** Small shared presentational primitives for the STR views.
 *
 * Exports:
 *   centsToUSD(cents)   format an integer-cents amount as USD
 *   EmptyState          fail-soft empty panel body (API down or no data)
 *   SectionLabel        small-caps metadata heading inside a panel
 *   KV                  one key/value row (mono, dim key, bright value)
 *   StatusPill          semantic green/red/amber status text
 */

import { ReactNode } from "react";
import { formatUSD } from "../../lib/format";

export function centsToUSD(cents: number): string {
  return formatUSD(cents / 100);
}

export function EmptyState({ hint }: { hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center h-32 gap-2 text-slate-600 font-mono text-sm">
      <span>No data</span>
      {hint && <span className="text-xs text-slate-700">{hint}</span>}
    </div>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <h3 className="text-xs font-mono font-semibold uppercase tracking-widest text-slate-500 mb-3">
      {children}
    </h3>
  );
}

export function KV({ label, value, accent }: { label: string; value: ReactNode; accent?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1 font-mono text-xs">
      <span className="text-slate-500">{label}</span>
      <span className={accent ? "text-amber-300 font-bold text-right break-all" : "text-slate-200 text-right break-all"}>
        {value}
      </span>
    </div>
  );
}

export function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={[
        "font-mono text-xs px-2 py-1 rounded border",
        ok
          ? "border-emerald-700 bg-emerald-950 text-emerald-400"
          : "border-red-700 bg-red-950 text-red-400",
      ].join(" ")}
    >
      {label}
    </span>
  );
}
