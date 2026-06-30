/** StallQueuePanel: the stuck handoffs the property manager chases by hand today.
 *  Each row is a blocked actor-to-actor handoff with a Hermes-drafted nudge (and a
 *  provenance badge proving it was reasoned), plus a one-click Nudge action. */

import { useState } from "react";
import { usePoll } from "../../hooks/usePoll";
import { useLive, liveParam } from "./LiveContext";
import { apiPost } from "../../lib/api";
import { StrStalledHandoff, StrStallQueueResponse } from "../../types";
import { EmptyState, KV, Plate, SectionLabel, StatusPill } from "./shared";
import { ProvenanceBadge } from "./ProvenanceBadge";
import { Button } from "@/components/ui/button";

function StallRow({ stall, onNudged }: { stall: StrStalledHandoff; onNudged: () => void }) {
  const { live } = useLive();
  const [busy, setBusy] = useState(false);

  async function nudge() {
    setBusy(true);
    await apiPost(`/str/stalls/nudge${liveParam(live)}`, { handoff_id: stall.handoff_id });
    setBusy(false);
    onNudged();
  }

  return (
    <Plate>
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="font-mono text-xs font-semibold text-foreground">
          {stall.from_actor} <span className="text-muted-foreground">&rarr;</span> {stall.to_actor}
        </span>
        <StatusPill ok={false} label={`STALLED ${stall.hours_stalled}h`} />
      </div>
      <KV label="property" value={stall.property_name} />
      <KV label="reason" value={stall.reason} />

      <div className="mt-3 border-t border-border pt-3">
        <div className="mb-2 flex items-center justify-between gap-2">
          <span className="font-mono text-[0.65rem] uppercase tracking-[0.2em] text-muted-foreground/60">
            Hermes nudge
          </span>
          <ProvenanceBadge prov={stall.reasoning_provenance} />
        </div>
        <p className="font-serif text-sm leading-relaxed text-foreground">
          {stall.nudge.nudge_message}
        </p>
        <div className="mt-3 flex items-center gap-3">
          <Button size="sm" disabled={busy} onClick={() => void nudge()} className="font-mono text-xs">
            {busy ? "Nudging..." : "Nudge"}
          </Button>
          <span className="font-mono text-[0.65rem] text-muted-foreground">
            next: {stall.nudge.next_action}
          </span>
        </div>
      </div>
    </Plate>
  );
}

export function StallQueuePanel() {
  const { live } = useLive();
  const { data, refetch } = usePoll<StrStallQueueResponse>(`/str/stalls${liveParam(live)}`, 2500);
  const stalls = data?.stalls ?? [];

  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3">
        <SectionLabel>Stalled handoffs</SectionLabel>
        {data && <StatusPill ok={stalls.length === 0} label={`${stalls.length} stuck`} />}
      </div>
      {!data ? (
        <EmptyState hint="GET /str/stalls" />
      ) : stalls.length === 0 ? (
        <EmptyState hint="No stuck handoffs; steady state." />
      ) : (
        <div className="flex flex-col gap-3">
          {stalls.map((stall) => (
            <StallRow key={stall.handoff_id} stall={stall} onNudged={refetch} />
          ))}
        </div>
      )}
    </section>
  );
}
