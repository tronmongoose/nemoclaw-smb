/** Shared presentational primitives for the STR views (dark editorial system).
 *
 * Vocabulary the act views compose:
 *   centsToUSD(cents)   format integer cents as USD
 *   EmptyState          fail-soft empty body (API down or no data)
 *   SectionLabel        small-caps mono metadata heading
 *   Rule                hairline section break, optional small-caps label
 *   KV                  one key/value row (mono, dim key, bright value)
 *   Stat                a headline number (serif, amber) with a label
 *   StatusPill          semantic outline status (verified / fault)
 *   Plate               the rare boxed element (use sparingly, <=3 per view)
 */

import { ReactNode } from "react";
import { formatUSD } from "../../lib/format";
import { cn } from "../../lib/utils";

export function centsToUSD(cents: number): string {
  return formatUSD(cents / 100);
}

export function EmptyState({ hint }: { hint?: string }) {
  return (
    <div className="flex h-28 flex-col items-center justify-center gap-1.5 font-mono text-sm text-muted-foreground">
      <span>No data</span>
      {hint && <span className="text-xs text-muted-foreground/60">{hint}</span>}
    </div>
  );
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return (
    <h3 className="mb-3 font-mono text-[0.7rem] font-medium uppercase tracking-[0.22em] text-muted-foreground">
      {children}
    </h3>
  );
}

export function Rule({ label }: { label?: string }) {
  if (!label) return <div className="h-px w-full bg-border" />;
  return (
    <div className="flex items-center gap-3">
      <div className="h-px flex-1 bg-border" />
      <span className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-muted-foreground">
        {label}
      </span>
      <div className="h-px flex-1 bg-border" />
    </div>
  );
}

export function KV({ label, value, accent }: { label: string; value: ReactNode; accent?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5 font-mono text-xs">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <span className={cn("break-all text-right", accent ? "font-semibold text-primary" : "text-foreground")}>
        {value}
      </span>
    </div>
  );
}

export function Stat({ label, value, sub }: { label: string; value: ReactNode; sub?: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <span className="font-mono text-[0.7rem] uppercase tracking-[0.22em] text-muted-foreground">
        {label}
      </span>
      <span className="font-serif text-4xl font-semibold leading-none tabular-nums text-primary md:text-5xl">
        {value}
      </span>
      {sub && <span className="font-mono text-xs text-muted-foreground">{sub}</span>}
    </div>
  );
}

export function StatusPill({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-[var(--radius)] border px-2 py-1 font-mono text-xs",
        ok ? "border-verified text-verified" : "border-destructive text-destructive",
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", ok ? "bg-verified" : "bg-destructive")} />
      {label}
    </span>
  );
}

export function Plate({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("rounded-[var(--radius)] border border-border bg-card/60 p-4", className)}>
      {children}
    </div>
  );
}
