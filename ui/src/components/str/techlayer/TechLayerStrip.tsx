/** The tech-layer toggle's inline reveal: per-portal, where each sponsor plugs into that
 *  portal's problem set, as four accent-bordered cells (the Portals template's tech layer).
 *  A disclosure expands the full sponsor x portal matrix for the judging deep-dive. */

import { useState } from "react";
import { StrSegment } from "../../../types";
import { TechLayerView } from "./TechLayerView";

const TECH: Record<StrSegment, { heading: string; cells: { sponsor: string; copy: string }[] }> = {
  owner: {
    heading: "Tech layer · where the stack plugs into the owner's problem",
    cells: [
      { sponsor: "NVIDIA", copy: "Reasons over your ledger" },
      { sponsor: "Stripe", copy: "Routes your monthly payout" },
      { sponsor: "Nous", copy: "The agent's judgment" },
      { sponsor: "ConductorOne", copy: "Governs every correction" },
    ],
  },
  firm: {
    heading: "Tech layer · where the stack plugs into operations",
    cells: [
      { sponsor: "NVIDIA", copy: "Scales inference across the roster" },
      { sponsor: "Stripe", copy: "Connected payouts per property" },
      { sponsor: "Nous", copy: "Models every working agent" },
      { sponsor: "ConductorOne", copy: "Scoped identity per checkout" },
    ],
  },
  agent: {
    heading: "Tech layer · where the stack plugs into the market",
    cells: [
      { sponsor: "NVIDIA", copy: "Compute metered per license" },
      { sponsor: "Stripe", copy: "Billing rails for the market" },
      { sponsor: "Nous", copy: "The licensed model substrate" },
      { sponsor: "ConductorOne", copy: "Governs every paid call" },
    ],
  },
};

export function TechLayerStrip({ portal }: { portal: StrSegment }) {
  const [showMatrix, setShowMatrix] = useState(false);
  const t = TECH[portal];

  return (
    <div className="mx-auto w-full max-w-6xl px-6 pb-2">
      <div className="border-t border-primary pt-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <span className="font-mono text-[0.62rem] uppercase tracking-[0.2em] text-primary">
            {t.heading}
          </span>
          <button
            onClick={() => setShowMatrix((v) => !v)}
            className="font-mono text-[0.6rem] uppercase tracking-[0.14em] text-muted-foreground transition-colors hover:text-foreground"
          >
            {showMatrix ? "Hide full matrix" : "Full sponsor matrix"}
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {t.cells.map((c) => (
            <div
              key={c.sponsor}
              className="flex flex-col gap-2 rounded-[var(--radius)] border border-primary bg-[hsl(var(--primary)/0.08)] px-4 py-3.5"
            >
              <span className="font-mono text-[0.66rem] uppercase tracking-[0.12em] text-primary">
                {c.sponsor}
              </span>
              <span className="font-serif text-[0.95rem] leading-snug text-foreground">
                {c.copy}
              </span>
            </div>
          ))}
        </div>

        {showMatrix && (
          <div className="mt-6">
            <TechLayerView />
          </div>
        )}
      </div>
    </div>
  );
}
