/** PerformancePanel: portfolio performance flagging with a Hermes-written "why".
 *  Each property ranks vs the portfolio average; outliers lead; the over/under
 *  verdict carries a Hermes summary explaining the drivers. */

import { usePoll } from "../../hooks/usePoll";
import { useLive, liveParam } from "./LiveContext";
import { StrPropertyPerformance, StrPerformanceResponse } from "../../types";
import { centsToUSD, EmptyState, SectionLabel, StatusPill } from "./shared";
import { ProvenanceBadge } from "./ProvenanceBadge";
import { cn } from "../../lib/utils";

function pctLabel(pct: number): string {
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${Math.round(pct * 100)}% vs avg`;
}

function PerfRow({ p }: { p: StrPropertyPerformance }) {
  const under = p.status === "under";
  return (
    <div className="flex flex-col gap-1.5 border-t border-border/50 py-3 first:border-t-0">
      <div className="flex items-center justify-between gap-3">
        <span className="font-serif text-sm text-foreground">{p.property_name}</span>
        <StatusPill ok={!under} label={p.status.replace("_", " ").toUpperCase()} />
      </div>
      <div className="flex items-center gap-4 font-mono text-xs text-muted-foreground">
        <span className="text-foreground">{centsToUSD(p.revenue_cents)}/mo</span>
        <span className={cn(p.pct_vs_avg >= 0 ? "text-verified" : "text-destructive")}>
          {pctLabel(p.pct_vs_avg)}
        </span>
        <span>{Math.round(p.occupancy * 100)}% occ</span>
      </div>
      <div className="mt-1 flex items-start justify-between gap-3">
        <p className="flex-1 font-serif text-sm leading-relaxed text-muted-foreground">
          {p.analysis.summary}
        </p>
        <ProvenanceBadge prov={p.reasoning_provenance} />
      </div>
    </div>
  );
}

export function PerformancePanel() {
  const { live } = useLive();
  const { data } = usePoll<StrPerformanceResponse>(`/str/performance${liveParam(live)}`, 3000);
  const properties = [...(data?.properties ?? [])].sort(
    (a, b) => Math.abs(b.pct_vs_avg) - Math.abs(a.pct_vs_avg),
  );

  return (
    <section id="section-performance" className="scroll-mt-24 rounded-[var(--radius)] border border-border bg-card p-4">
      <div className="mb-2 flex items-center gap-2">
        <SectionLabel>Portfolio performance</SectionLabel>
        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-heartbeat" aria-label="live polling" />
      </div>
      {properties.length === 0 ? (
        <EmptyState hint="GET /str/performance" />
      ) : (
        <div className="flex flex-col">
          {properties.map((p) => (
            <PerfRow key={p.property_id} p={p} />
          ))}
        </div>
      )}
    </section>
  );
}
