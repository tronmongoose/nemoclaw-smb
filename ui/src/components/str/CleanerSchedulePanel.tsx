/** CleanerSchedulePanel: pay + schedule, not just issue a card. When a clean
 *  stage stalls, Hermes proposes reassigning to a free cleaner; "Assign + issue
 *  card" pre-authorizes that cleaner's single-use card. */

import { useState } from "react";
import { usePoll } from "../../hooks/usePoll";
import { useLive, liveParam } from "./LiveContext";
import { apiPost } from "../../lib/api";
import {
  StrCleanerStall,
  StrSchedulingResponse,
  StrSchedulingAssignResult,
} from "../../types";
import { EmptyState, KV, Plate, SectionLabel, StatusPill } from "./shared";
import { ProvenanceBadge } from "./ProvenanceBadge";
import { Button } from "@/components/ui/button";

function CrewAvailability({ crew }: { crew: StrCleanerStall["crew_availability"] }) {
  if (crew.length === 0) return null;
  return (
    <div className="mb-3 flex flex-wrap gap-3">
      {crew.map((c) => (
        <span key={c.id} className="inline-flex items-center gap-1.5 font-mono text-xs">
          <span className={`h-1.5 w-1.5 rounded-full ${c.available ? "bg-verified" : "bg-muted-foreground/40"}`} />
          <span className="text-foreground">{c.name}</span>
          <span className="text-muted-foreground">{c.available ? "free" : "busy"}</span>
        </span>
      ))}
    </div>
  );
}

function ScheduleRow({ stall }: { stall: StrCleanerStall }) {
  const { live } = useLive();
  const [busy, setBusy] = useState(false);
  const [card, setCard] = useState<string | null>(null);

  async function assign() {
    setBusy(true);
    const res = await apiPost<StrSchedulingAssignResult>(
      `/str/scheduling/assign${liveParam(live)}`,
      { handoff_id: stall.handoff_id },
    );
    if (res?.ok && res.card_token) setCard(res.card_token);
    setBusy(false);
  }

  return (
    <Plate>
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="font-mono text-xs font-semibold text-foreground">
          {stall.assigned_to} <span className="text-muted-foreground">&rarr;</span>{" "}
          {stall.suggested_cleaner?.name ?? "unassigned"}
        </span>
        <StatusPill ok={false} label={`STALLED ${stall.hours_stalled}h`} />
      </div>
      <KV label="property" value={stall.property_name} />
      <KV label="proposed start" value={stall.schedule.scheduled_start} />

      <div className="mt-3 border-t border-border pt-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="font-mono text-[0.65rem] uppercase tracking-[0.2em] text-muted-foreground/60">
            Hermes schedule
          </span>
          <ProvenanceBadge prov={stall.reasoning_provenance} />
        </div>
        <p className="font-serif text-sm leading-relaxed text-foreground">{stall.schedule.reason}</p>

        {card ? (
          <div className="mt-3 flex items-center gap-3">
            <StatusPill ok={true} label="CARD PRE-AUTHORIZED" />
            <span className="font-mono text-xs text-muted-foreground">{card}</span>
          </div>
        ) : (
          <div className="mt-3 flex items-center gap-3">
            <Button size="sm" disabled={busy} onClick={() => void assign()} className="font-mono text-xs">
              {busy ? "Assigning..." : "Assign + issue card"}
            </Button>
            <span className="font-mono text-[0.65rem] text-muted-foreground">{stall.schedule.card_action}</span>
          </div>
        )}
      </div>
    </Plate>
  );
}

export function CleanerSchedulePanel() {
  const { live } = useLive();
  const { data } = usePoll<StrSchedulingResponse>(`/str/scheduling${liveParam(live)}`, 2500);
  const stalls = data?.stalls ?? [];

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <SectionLabel>Cleaner scheduling</SectionLabel>
        {data && <StatusPill ok={stalls.length === 0} label={`${stalls.length} to reassign`} />}
      </div>
      {!data ? (
        <EmptyState hint="GET /str/scheduling" />
      ) : stalls.length === 0 ? (
        <EmptyState hint="No clean-stage stalls; crew on track." />
      ) : (
        <div className="flex flex-col gap-3">
          <CrewAvailability crew={stalls[0].crew_availability} />
          {stalls.map((stall) => (
            <ScheduleRow key={stall.handoff_id} stall={stall} />
          ))}
        </div>
      )}
    </section>
  );
}
