/** TurnoverLoopPanel: the connective tissue — a property's turnover loop
 *  (checkout -> clean -> inspect -> ready-to-book) with per-stage status and the
 *  actor who owns each handoff. Pass a propertyId for one property (owner view);
 *  omit it to show the whole portfolio (company view). */

import { usePoll } from "../../hooks/usePoll";
import { useLive } from "./LiveContext";
import { StrTurnoverEvent, StrTurnoverResponse, StrTurnoverStageRow } from "../../types";
import { EmptyState, SectionLabel, StatusPill } from "./shared";
import { cn } from "../../lib/utils";

const STATUS_DOT: Record<string, string> = {
  done: "bg-verified",
  in_progress: "bg-primary animate-heartbeat",
  waiting: "bg-muted-foreground/40",
  blocked: "bg-destructive animate-heartbeat",
};

function StageRow({ s }: { s: StrTurnoverStageRow }) {
  return (
    <div className="flex items-center gap-3 py-1.5 font-mono text-xs">
      <span className={cn("h-1.5 w-1.5 shrink-0 rounded-full", STATUS_DOT[s.status] ?? "bg-muted-foreground")} />
      <span className="w-20 shrink-0 uppercase tracking-wider text-foreground">{s.stage}</span>
      <span className="w-24 shrink-0 text-muted-foreground">{s.status.replace("_", " ")}</span>
      <span className="flex-1 truncate text-muted-foreground">{s.actor}</span>
      {s.status !== "waiting" && (
        <span className="shrink-0 tabular-nums text-muted-foreground/60">{s.hours_in_stage}h</span>
      )}
    </div>
  );
}

function PropertyLoop({ ev }: { ev: StrTurnoverEvent }) {
  const stalled = ev.overall_status === "stalled";
  return (
    <div className="flex flex-col gap-1">
      <div className="mb-1 flex items-center justify-between gap-3">
        <span className="font-serif text-sm text-foreground">{ev.property_name}</span>
        <StatusPill ok={!stalled} label={ev.overall_status.replace("_", " ").toUpperCase()} />
      </div>
      {ev.stages.map((s) => (
        <StageRow key={s.stage} s={s} />
      ))}
    </div>
  );
}

export function TurnoverLoopPanel({ propertyId }: { propertyId?: string }) {
  const { live } = useLive();
  const query = propertyId
    ? `?property_id=${propertyId}&live=${live}`
    : `?live=${live}`;
  const { data } = usePoll<StrTurnoverResponse>(`/str/turnover${query}`, 3000);
  const properties = data?.properties ?? [];

  return (
    <section id="section-turnover" className="scroll-mt-24 rounded-[var(--radius)] border border-border bg-card p-4">
      <div className="mb-3 flex items-center gap-2">
        <SectionLabel>Turnover pipeline</SectionLabel>
        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-heartbeat" aria-label="live polling" />
      </div>
      {properties.length === 0 ? (
        <EmptyState hint="GET /str/turnover" />
      ) : (
        <div className="flex flex-col gap-5">
          {properties.map((ev) => (
            <PropertyLoop key={ev.property_id} ev={ev} />
          ))}
        </div>
      )}
    </section>
  );
}
