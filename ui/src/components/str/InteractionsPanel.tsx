/** InteractionsPanel: calm editorial live activity feed of sponsor interactions.
 * Polls GET /str/interactions every 2500ms; newest 8 entries, newest first.
 */

import { useEffect, useRef } from "react";
import { usePoll } from "../../hooks/usePoll";
import { StrSegment, StrInteraction, StrInteractionsResponse } from "../../types";
import { EmptyState, SectionLabel, StatusPill } from "./shared";
import { cn } from "../../lib/utils";

function fmtLatency(latency_ms: number): string {
  /** Format milliseconds to a compact human label. */
  if (latency_ms < 1000) return `${latency_ms}ms`;
  return `${(latency_ms / 1000).toFixed(1)}s`;
}

function ModeBadge({ mode }: { mode: string | null | undefined }) {
  /** Inline live/demo provenance badge. */
  if (mode === "live") {
    return (
      <span className="inline-flex items-center gap-1 rounded-[var(--radius)] border border-primary bg-[hsl(var(--primary)/0.08)] px-1.5 py-0.5 font-mono text-[0.65rem] text-primary">
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

function InteractionRow({ entry, isNew }: { entry: StrInteraction; isNew: boolean }) {
  /** One editorial feed row: sponsor + op label, right-aligned meta. */
  const latency =
    entry.model != null && entry.latency_ms != null
      ? fmtLatency(entry.latency_ms)
      : null;

  return (
    <div
      className={cn(
        "flex items-center gap-3 border-b border-border py-3",
        isNew && "animate-flash",
      )}
    >
      <span className="w-28 shrink-0 font-mono text-[0.7rem] text-muted-foreground">
        {entry.sponsor}
      </span>
      <span className="flex-1 font-mono text-xs text-foreground truncate">
        {entry.op}
      </span>
      <div className="flex shrink-0 items-center gap-2">
        {latency && (
          <span className="font-mono text-[0.65rem] text-muted-foreground tabular-nums">
            {latency}
          </span>
        )}
        {entry.mode != null && <ModeBadge mode={entry.mode} />}
      </div>
    </div>
  );
}

interface InteractionsPanelProps {
  segment?: StrSegment;
}

export function InteractionsPanel({ segment }: InteractionsPanelProps) {
  /** Polled feed card: header with heartbeat + chain pill, then the 8 most-recent rows. */
  const path =
    `/str/interactions?limit=80` +
    (segment ? `&segment=${encodeURIComponent(segment)}` : "");

  const { data } = usePoll<StrInteractionsResponse>(path, 2500);

  const entries = data?.entries ?? [];
  const reversed = [...entries].reverse().slice(0, 8);

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

  const threshold = prevMaxRef.current;

  const isNew = (entry: StrInteraction): boolean => {
    if (firstLoad.current || threshold === null) return false;
    return (entry.seq ?? -1) > threshold;
  };

  if (!data || entries.length === 0) {
    return (
      <div className="bg-card border border-border rounded-[var(--radius)] p-6">
        <div className="mb-4 flex items-center justify-between gap-3">
          <SectionLabel>Live interactions</SectionLabel>
        </div>
        <EmptyState hint="GET /str/interactions" />
      </div>
    );
  }

  const verify = data.verify;

  return (
    <div className="bg-card border border-border rounded-[var(--radius)] p-6">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <SectionLabel>Live interactions</SectionLabel>
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
      <div>
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
