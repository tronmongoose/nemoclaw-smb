/** AgentsAtWorkPanel: autonomous worker agents visible as an operations floor.
 * Groups /str/interactions?segment=firm entries into named workers; flashes on new activity.
 */

import { useEffect, useRef } from "react";
import { usePoll } from "../../hooks/usePoll";
import { StrInteraction, StrInteractionsResponse } from "../../types";
import { EmptyState, SectionLabel, StatusPill } from "./shared";
import { cn } from "../../lib/utils";

// ----- worker classification -----

type WorkerName =
  | "Cleaner-card agent"
  | "Payout agent"
  | "Invoicing agent"
  | "Governance agent"
  | "Ops agent";

/** Map a single entry to its worker bucket. */
function classifyEntry(e: StrInteraction): WorkerName {
  const op = e.op.toLowerCase();
  if (op.includes("card issue") || op.includes("issuing")) return "Cleaner-card agent";
  if (op.includes("payout") || op.includes("connect") || op.includes("global payouts"))
    return "Payout agent";
  if (op.includes("ubp") || op.includes("metronome") || op.includes("invoice"))
    return "Invoicing agent";
  if (e.sponsor === "ConductorOne" || op.includes("nhi") || op.includes("authorize"))
    return "Governance agent";
  return "Ops agent";
}

// ----- per-worker data shape -----

interface WorkerRow {
  name: WorkerName;
  count: number;
  lastEntry: StrInteraction;
  lastHash: string | undefined;
}

/** Derive ordered worker rows from the full entry list (newest-last from API). */
function deriveWorkers(entries: StrInteraction[]): WorkerRow[] {
  const map = new Map<WorkerName, WorkerRow>();
  for (const e of entries) {
    const name = classifyEntry(e);
    const existing = map.get(name);
    if (!existing) {
      map.set(name, { name, count: 1, lastEntry: e, lastHash: e.entry_hash });
    } else {
      existing.count += 1;
      // entries are newest-last, so later iteration = more recent
      existing.lastEntry = e;
      existing.lastHash = e.entry_hash;
    }
  }
  // Sort by count descending so the busiest agent leads
  return Array.from(map.values()).sort((a, b) => b.count - a.count);
}

// ----- formatting helpers -----

function fmtTs(ts: string | undefined): string {
  if (!ts) return "";
  try {
    return new Date(ts).toISOString().slice(11, 19);
  } catch {
    return ts;
  }
}

function fmtLatency(ms: number): string {
  return ms < 1000 ? `${ms}ms` : `${(ms / 1000).toFixed(1)}s`;
}

// ----- sub-components -----

function ModeBadge({ mode }: { mode: string | null | undefined }) {
  if (mode === "live") {
    return (
      <span className="inline-flex items-center gap-1 rounded border border-primary bg-[hsl(var(--primary)/0.1)] px-1.5 py-0.5 font-mono text-[0.65rem] text-primary">
        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-heartbeat" />
        LIVE
      </span>
    );
  }
  if (mode === "demo") {
    return <span className="font-mono text-[0.65rem] text-muted-foreground">DEMO</span>;
  }
  return null;
}

function WorkerRowItem({
  row,
  isNew,
}: {
  row: WorkerRow;
  isNew: boolean;
}) {
  const e = row.lastEntry;
  const latency = e.latency_ms != null ? fmtLatency(e.latency_ms) : null;
  const statusOk = e.status === "ok" || e.status === "cached";

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-3 gap-y-0.5 border-b border-border/50 py-2",
        isNew && "animate-flash",
      )}
      role="row"
    >
      {/* worker name */}
      <span className="w-36 shrink-0 text-sm font-medium text-foreground">
        {row.name}
      </span>

      {/* status dot */}
      <span
        aria-label={e.status ?? "unknown"}
        className={cn(
          "h-2 w-2 shrink-0 rounded-full",
          statusOk ? "bg-verified" : "bg-muted-foreground",
        )}
      />

      {/* last op */}
      <span className="flex-1 truncate font-mono text-xs text-muted-foreground">
        {e.op}
      </span>

      {/* mode badge */}
      <ModeBadge mode={e.mode} />

      {/* time */}
      <span className="font-mono text-xs text-muted-foreground/60 tabular-nums">
        {fmtTs(e.ts)}
      </span>

      {/* throughput */}
      <span
        className="w-14 text-right font-mono text-xs font-semibold text-primary tabular-nums"
        aria-label="ops count"
      >
        {row.count}x
      </span>

      {/* latency */}
      {latency && (
        <span className="w-14 text-right font-mono text-xs text-muted-foreground tabular-nums">
          {latency}
        </span>
      )}
    </div>
  );
}

// ----- main export -----

/** Renders a live operations-floor view of autonomous worker agents grouped from the firm feed. */
export function AgentsAtWorkPanel(): JSX.Element {
  const { data } = usePoll<StrInteractionsResponse>(
    "/str/interactions?segment=firm",
    2500,
  );

  const entries = data?.entries ?? [];
  const workers = deriveWorkers(entries);

  // Flash detection: track lastHash per worker name across renders
  const prevHashRef = useRef<Map<string, string | undefined>>(new Map());
  const firstLoad = useRef(true);

  const isNew = (row: WorkerRow): boolean => {
    if (firstLoad.current) return false;
    const prev = prevHashRef.current.get(row.name);
    return prev !== undefined && prev !== row.lastHash;
  };

  useEffect(() => {
    if (entries.length === 0) return;
    if (firstLoad.current) {
      firstLoad.current = false;
    }
    const next = new Map<string, string | undefined>();
    for (const w of workers) next.set(w.name, w.lastHash);
    prevHashRef.current = next;
  });

  if (!data || workers.length === 0) {
    return (
      <div className="rounded-[var(--radius)] border border-border bg-card p-4">
        <SectionLabel>Agents at work</SectionLabel>
        <EmptyState hint="Waiting for firm activity" />
      </div>
    );
  }

  const verify = data.verify;

  return (
    <div className="rounded-[var(--radius)] border border-border bg-card p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <SectionLabel>Agents at work</SectionLabel>
          <span
            className="h-1.5 w-1.5 rounded-full bg-primary animate-heartbeat"
            aria-label="live polling"
          />
        </div>
        <StatusPill
          ok={verify.ok}
          label={verify.ok ? "CHAIN VERIFIED" : "CHAIN FAULT"}
        />
      </div>

      <div
        role="table"
        aria-label="Autonomous agent worker status"
        className="divide-y divide-border/0"
      >
        {workers.map((row) => (
          <WorkerRowItem key={row.name} row={row} isNew={isNew(row)} />
        ))}
      </div>
    </div>
  );
}
