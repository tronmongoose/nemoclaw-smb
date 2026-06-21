/** LicensedAssetsPanel: fleet roster of licensed agent assets, metered and governed by ConductorOne.
 * Polls /str/interactions?segment=agent at 2500ms; fetches /str/act3/metrics once.
 * Each asset derives activity from interaction stream ops; earn meter shows call share.
 */

import { useEffect, useRef } from "react";
import { usePoll } from "../../hooks/usePoll";
import { StrInteractionsResponse } from "../../types";
import {
  SectionLabel,
  StatusPill,
  Stat,
  KV,
  EmptyState,
  centsToUSD,
} from "./shared";
import { Progress } from "@/components/ui/progress";
import { cn } from "../../lib/utils";

// --- Asset definitions (deterministic; not runtime-random) ---

interface AssetDef {
  name: string;
  licenseId: string;
  capability: string;
  reasoner: string;
  match: (op: string, sponsor: string) => boolean;
}

const ASSETS: AssetDef[] = [
  {
    name: "Pricing agent",
    licenseId: "nhi://swarm/pricing-agent#a1f3",
    capability: "dynamic price",
    reasoner: "NVIDIA Nemotron",
    match: (op) => /pricing|price/i.test(op),
  },
  {
    name: "Audit agent",
    licenseId: "nhi://swarm/audit-agent#c7e2",
    capability: "machine-readability audit",
    reasoner: "NVIDIA Nemotron",
    match: (op) => /aeo|audit/i.test(op),
  },
  {
    name: "Orchestrator",
    licenseId: "nhi://swarm/orchestrator#f9b0",
    capability: "intent routing",
    reasoner: "Nous Hermes",
    match: (op, sponsor) => /orchestration/i.test(op) || sponsor === "Nous Research",
  },
];

// --- Helpers ---

function fmtLatency(ms: number): string {
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
}

function fmtTs(ts: string | undefined): string {
  if (!ts) return "";
  try {
    return new Date(ts).toISOString().slice(11, 19);
  } catch {
    return ts;
  }
}

// --- Sub-components ---

function DemoTag() {
  return (
    <span className="font-mono text-[0.6rem] uppercase tracking-widest text-muted-foreground/60 border border-border/50 rounded-[var(--radius)] px-1 py-0.5">
      DEMO
    </span>
  );
}

interface AssetMatch {
  def: AssetDef;
  callCount: number;
  lastTs: string | undefined;
  lastOp: string | undefined;
  lastLatency: number | null;
  isNew: boolean;
}

function AssetRow({ asset, totalCalls }: { asset: AssetMatch; totalCalls: number }) {
  /** Renders one fleet asset: license id, capability, govern pill, earn meter, call count. */
  const share = totalCalls > 0 ? Math.round((asset.callCount / totalCalls) * 100) : 0;

  return (
    <div
      className={cn(
        "rounded-[var(--radius)] border border-border bg-card/60 p-4",
        asset.isNew && "animate-flash",
      )}
      aria-label={`Licensed asset: ${asset.def.name}`}
    >
      <div className="mb-2 flex flex-wrap items-start justify-between gap-2">
        <div className="flex flex-col gap-0.5">
          <span className="font-serif text-sm font-semibold text-foreground">
            {asset.def.name}
          </span>
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-[0.65rem] text-muted-foreground break-all">
              {asset.def.licenseId}
            </span>
            <DemoTag />
          </div>
        </div>
        <StatusPill ok={true} label="C1 governed" />
      </div>

      <div className="mb-3 space-y-0.5">
        <KV label="capability" value={asset.def.capability} />
        <KV label="reasoner" value={asset.def.reasoner} />
        {asset.lastOp && <KV label="last op" value={asset.lastOp} />}
        {asset.lastTs && (
          <KV label="last call" value={<span className="tabular-nums">{fmtTs(asset.lastTs)}</span>} />
        )}
        {asset.lastLatency != null && (
          <KV label="latency" value={<span className="tabular-nums">{fmtLatency(asset.lastLatency)}</span>} />
        )}
      </div>

      <div className="space-y-1.5">
        <div className="flex items-center justify-between font-mono text-xs text-muted-foreground">
          <span>call share</span>
          <span className="tabular-nums text-primary">{asset.callCount} calls</span>
        </div>
        <Progress
          value={share}
          aria-label={`${asset.def.name} call share ${share}%`}
        />
      </div>
    </div>
  );
}

function FleetTotals({
  earningsCents,
  callsServed,
}: {
  earningsCents: number;
  callsServed: number;
}) {
  /** Top-of-panel headline stats: total fleet earnings and total calls. */
  return (
    <div className="mb-4 flex flex-wrap gap-6">
      <Stat
        label="Fleet earnings"
        value={centsToUSD(earningsCents)}
        sub="HTTP-402 metered revenue"
      />
      <Stat
        label="Calls served"
        value={<span className="tabular-nums">{callsServed}</span>}
        sub="across all licensed assets"
      />
    </div>
  );
}

// --- Main export ---

export function LicensedAssetsPanel(): JSX.Element {
  /** Fleet roster of licensed agent assets governed by ConductorOne.
   * Derives per-asset activity from the agent interaction stream.
   */
  const { data: interData } = usePoll<StrInteractionsResponse>(
    "/str/interactions?segment=agent",
    2500,
  );
  const entries = interData?.entries ?? [];
  const maxSeq = entries.reduce((m, e) => Math.max(m, e.seq ?? -1), -1);
  const prevMaxRef = useRef<number | null>(null);
  const firstLoad = useRef(true);

  useEffect(() => {
    if (entries.length > 0) {
      if (firstLoad.current) firstLoad.current = false;
      prevMaxRef.current = maxSeq;
    }
  }, [maxSeq, entries.length]);

  const threshold = prevMaxRef.current;

  const assetMatches: AssetMatch[] = ASSETS.map((def) => {
    const matched = entries.filter((e) => def.match(e.op, e.sponsor));
    const latest = matched.length > 0 ? matched[matched.length - 1] : null;
    const hasNew =
      !firstLoad.current &&
      threshold !== null &&
      matched.some((e) => (e.seq ?? -1) > threshold);

    return {
      def,
      callCount: matched.length,
      lastTs: latest?.ts,
      lastOp: latest?.op,
      lastLatency: latest?.latency_ms ?? null,
      isNew: hasNew,
    };
  });

  const totalCalls = assetMatches.reduce((s, a) => s + a.callCount, 0);

  // Earnings come from the same stream as the asset counts, so the headline stays
  // consistent with the rows (HTTP-402 amounts are logged on each earn).
  const earningsCents = entries.reduce(
    (s, e) => s + Number(e.metadata?.amount_cents ?? 0),
    0,
  );
  const verify = interData?.verify;

  return (
    <div
      className="rounded-[var(--radius)] border border-border bg-card p-4"
      aria-label="Licensed assets panel"
    >
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <SectionLabel>Licensed assets</SectionLabel>
          <span
            className="h-1.5 w-1.5 rounded-full bg-primary animate-heartbeat"
            aria-label="live polling"
          />
        </div>
        {verify && (
          <StatusPill
            ok={verify.ok}
            label={verify.ok ? "CHAIN VERIFIED" : "CHAIN FAULT"}
          />
        )}
      </div>

      <FleetTotals earningsCents={earningsCents} callsServed={entries.length} />

      {entries.length === 0 ? (
        <EmptyState hint="Waiting for agent interactions on GET /str/interactions?segment=agent" />
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {assetMatches.map((asset) => (
            <AssetRow
              key={asset.def.licenseId}
              asset={asset}
              totalCalls={totalCalls}
            />
          ))}
        </div>
      )}
    </div>
  );
}
