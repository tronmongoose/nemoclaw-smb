/** InteractionsPanel: live + historical feed of sponsor interactions.
 * Polls GET /str/interactions every 2500ms; new entries flash on arrival.
 * Sponsors: Nous Research, NVIDIA, Stripe, ConductorOne.
 */

import { useEffect, useRef } from "react";
import { usePoll } from "../../hooks/usePoll";
import { StrSegment, StrInteraction, StrInteractionsResponse } from "../../types";
import { EmptyState, SectionLabel, StatusPill } from "./shared";
import { cn } from "../../lib/utils";

function fmtTs(ts: string | undefined): string {
  if (!ts) return "";
  try {
    const d = new Date(ts);
    return d.toISOString().slice(11, 19);
  } catch {
    return ts;
  }
}

function fmtLatency(latency_ms: number): string {
  if (latency_ms < 1000) return `${latency_ms}ms`;
  return `${(latency_ms / 1000).toFixed(1)}s`;
}

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
    return (
      <span className="font-mono text-[0.65rem] text-muted-foreground">DEMO</span>
    );
  }
  return null;
}

function InteractionRow({
  entry,
  isNew,
}: {
  entry: StrInteraction;
  isNew: boolean;
}) {
  const latency =
    entry.model != null && entry.latency_ms != null
      ? fmtLatency(entry.latency_ms)
      : null;

  return (
    <div
      className={cn(
        "flex flex-wrap items-center gap-x-3 gap-y-0.5 border-b border-border/50 py-2 font-mono text-xs",
        isNew && "animate-flash",
      )}
    >
      <span className="text-foreground">{entry.sponsor}</span>
      <span className="text-muted-foreground">{entry.op}</span>
      {entry.mode != null && <ModeBadge mode={entry.mode} />}
      {latency && (
        <span className="text-muted-foreground tabular-nums">{latency}</span>
      )}
      {entry.status && (
        <span className="text-muted-foreground">{entry.status}</span>
      )}
      <span className="ml-auto text-muted-foreground/60 tabular-nums">
        {fmtTs(entry.ts)}
      </span>
    </div>
  );
}

interface InteractionsPanelProps {
  segment?: StrSegment;
}

export function InteractionsPanel({ segment }: InteractionsPanelProps) {
  const path =
    `/str/interactions?limit=80` +
    (segment ? `&segment=${encodeURIComponent(segment)}` : "");

  const { data } = usePoll<StrInteractionsResponse>(path, 2500);

  const entries = data?.entries ?? [];
  // Entries arrive newest-last; render newest-first.
  const reversed = [...entries].reverse();

  const maxSeq = entries.reduce((m, e) => Math.max(m, e.seq ?? -1), -1);
  const prevMaxRef = useRef<number | null>(null);
  const firstLoad = useRef(true);

  useEffect(() => {
    if (entries.length > 0) {
      if (firstLoad.current) {
        firstLoad.current = false;
      }
      prevMaxRef.current = maxSeq;
    }
  }, [maxSeq, entries.length]);

  // On first load prevMaxRef is null => no flash. After that, flash entries > prevMax.
  const threshold = prevMaxRef.current;

  const isNew = (entry: StrInteraction): boolean => {
    if (firstLoad.current || threshold === null) return false;
    return (entry.seq ?? -1) > threshold;
  };

  if (!data || entries.length === 0) {
    return (
      <div className="bg-card border border-border rounded-[var(--radius)] p-4">
        <div className="mb-3 flex items-center justify-between gap-3">
          <SectionLabel>Live and historical interactions</SectionLabel>
        </div>
        <EmptyState hint="GET /str/interactions" />
      </div>
    );
  }

  const verify = data.verify;

  return (
    <div className="bg-card border border-border rounded-[var(--radius)] p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <SectionLabel>Live and historical interactions</SectionLabel>
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

      <div className="max-h-[440px] overflow-auto">
        {reversed.map((entry, i) => (
          <InteractionRow
            key={entry.seq != null ? entry.seq : `${entry.ts}-${i}`}
            entry={entry}
            isNew={isNew(entry)}
          />
        ))}
      </div>
    </div>
  );
}
