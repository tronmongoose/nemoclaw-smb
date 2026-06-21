/** The STR experience, framed as three audience segments. Each segment shows its
 *  entity node graph, the live + historical interactions feed, and its act content,
 *  over the calm Oceanside pier background. */

import { useState } from "react";
import { ErrorBoundary } from "../ErrorBoundary";
import { StrSegment } from "../../types";
import { LiveProvider } from "./LiveContext";
import { LiveToggle } from "./LiveToggle";
import { PalmBackground } from "./PalmBackground";
import { SegmentSwitch } from "./SegmentSwitch";
import { SegmentNodeGraph } from "./SegmentNodeGraph";
import { InteractionsPanel } from "./InteractionsPanel";
import { Act1View } from "./Act1View";
import { Act2View } from "./Act2View";
import { Act3View } from "./Act3View";

const TITLE: Record<StrSegment, string> = {
  owner: "You own one or more short-term rentals.",
  firm: "You run a property-management firm.",
  agent: "You run an agent serving many property-management firms.",
};

const DEK: Record<StrSegment, string> = {
  owner: "The agent reads the monthly statement before you do, catches a management-fee overcharge, holds the correction for approval, and pays it once you say so.",
  firm: "Every guest checkout issues a single-use cleaner card under a scoped identity, then settles crew payouts and owner invoices at month end.",
  agent: "Sell dynamic pricing and AEO audits to other AI agents over HTTP-402: governed by ConductorOne, reasoned by Nemotron, earning per call.",
};

export function SegmentView({ onLegacy }: { onLegacy?: () => void }) {
  const [segment, setSegment] = useState<StrSegment>("owner");
  const Act = segment === "owner" ? Act1View : segment === "firm" ? Act2View : Act3View;

  return (
    <LiveProvider>
      <PalmBackground />
      <div className="min-h-screen">
        <header className="border-b border-border bg-[hsl(var(--background)/0.72)]">
          <div className="mx-auto flex max-w-6xl flex-wrap items-end justify-between gap-4 px-6 py-5">
            <div className="flex flex-col">
              <span className="font-mono text-[0.7rem] uppercase tracking-[0.28em] text-muted-foreground">
                Sweet Clementine by the Sea
              </span>
              <span className="font-serif text-xl font-semibold leading-tight text-foreground">
                Short-term rental operations, calm and governed.
              </span>
            </div>
            <LiveToggle />
          </div>
        </header>

        <main className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-8">
          <SegmentSwitch segment={segment} onChange={setSegment} />

          <div className="flex flex-col gap-1">
            <h2 className="font-serif text-2xl font-semibold text-foreground">{TITLE[segment]}</h2>
            <p className="max-w-prose font-mono text-xs leading-relaxed text-muted-foreground">
              {DEK[segment]}
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            <ErrorBoundary label="entity graph">
              <SegmentNodeGraph segment={segment} />
            </ErrorBoundary>
            <ErrorBoundary label="interactions">
              <InteractionsPanel segment={segment} />
            </ErrorBoundary>
          </div>

          <div className="rounded-[var(--radius)] border border-border bg-card/90 p-6">
            <ErrorBoundary label={segment}>
              <Act />
            </ErrorBoundary>
          </div>
        </main>

        {onLegacy && (
          <footer className="border-t border-border px-6 py-4">
            <div className="mx-auto flex max-w-6xl items-center justify-between">
              <span className="font-mono text-[0.65rem] text-muted-foreground/60">
                Oceanside Pier photo: Mark Neal on Unsplash
              </span>
              <button
                onClick={onLegacy}
                className="font-mono text-[0.7rem] uppercase tracking-[0.2em] text-muted-foreground/60 transition-colors hover:text-muted-foreground"
              >
                Legacy demos
              </button>
            </div>
          </footer>
        )}
      </div>
    </LiveProvider>
  );
}
