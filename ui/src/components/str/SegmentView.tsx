/** The STR experience as three portals at three scales, plus the cross-cutting tech
 *  layer. The top nav retunes the whole page temperature on switch (warm -> cool ->
 *  electric); the transition itself communicates scale. Each portal shows its entity
 *  graph, the live + historical interactions feed, and its act content. */

import { useState } from "react";
import { ErrorBoundary } from "../ErrorBoundary";
import { PortalView, StrSegment } from "../../types";
import { LiveProvider } from "./LiveContext";
import { LiveToggle } from "./LiveToggle";
import { AtmosphereBackground } from "./AtmosphereBackground";
import { SegmentSwitch } from "./SegmentSwitch";
import { SegmentNodeGraph } from "./SegmentNodeGraph";
import { InteractionsPanel } from "./InteractionsPanel";
import { AgentsAtWorkPanel } from "./AgentsAtWorkPanel";
import { LicensedAssetsPanel } from "./LicensedAssetsPanel";
import { TechLayerView } from "./techlayer/TechLayerView";
import { StackOverlay } from "./techlayer/StackOverlay";
import { Act1View } from "./Act1View";
import { Act2View } from "./Act2View";
import { Act3View } from "./Act3View";

const TITLE: Record<StrSegment, string> = {
  owner: "You own one or more short-term rentals.",
  firm: "You run a property-management company.",
  agent: "You run an agent serving many property-management companies.",
};

const DEK: Record<StrSegment, string> = {
  owner: "The agent reads the monthly statement before you do, catches a management-fee overcharge, holds the correction for approval, and pays it once you say so.",
  firm: "Every guest checkout issues a single-use cleaner card under a scoped identity, then settles crew payouts and owner invoices at month end.",
  agent: "Sell dynamic pricing and machine-readability audits to other AI agents over HTTP-402. Agent-to-agent commerce: governed by ConductorOne, reasoned by Nemotron, earning per call.",
};

function ActFor({ segment }: { segment: StrSegment }) {
  if (segment === "owner") return <Act1View />;
  if (segment === "firm") return <Act2View />;
  return <Act3View />;
}

export function SegmentView({ onLegacy }: { onLegacy?: () => void }) {
  const [view, setView] = useState<PortalView>("owner");
  const isStack = view === "stack";
  const segment = view as StrSegment; // only read when !isStack

  return (
    <LiveProvider>
      <div
        data-portal={view}
        className="min-h-screen bg-background text-foreground transition-colors duration-700 ease-out"
      >
        <AtmosphereBackground portal={view} />

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
          <SegmentSwitch view={view} onChange={setView} />

          {isStack ? (
            <section className="flex flex-col gap-6">
              <div className="flex flex-col gap-1">
                <h2 className="font-serif text-2xl font-semibold text-foreground">
                  The stack, mapped to the work.
                </h2>
                <p className="max-w-prose font-mono text-xs leading-relaxed text-muted-foreground">
                  Where NVIDIA, Stripe, Nous, and ConductorOne plug into each portal's
                  problem set. Live calls light up as they happen.
                </p>
              </div>
              <ErrorBoundary label="tech layer">
                <TechLayerView />
              </ErrorBoundary>
            </section>
          ) : (
            <>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div className="flex flex-col gap-1">
                  <h2 className="font-serif text-2xl font-semibold text-foreground">
                    {TITLE[segment]}
                  </h2>
                  <p className="max-w-prose font-mono text-xs leading-relaxed text-muted-foreground">
                    {DEK[segment]}
                  </p>
                </div>
                <StackOverlay segment={segment} />
              </div>

              <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                <ErrorBoundary label="entity graph">
                  <SegmentNodeGraph segment={segment} />
                </ErrorBoundary>
                <ErrorBoundary label="interactions">
                  <InteractionsPanel segment={segment} />
                </ErrorBoundary>
              </div>

              {segment === "firm" && (
                <div className="rounded-[var(--radius)] border border-border bg-card/90 p-6">
                  <ErrorBoundary label="agents at work">
                    <AgentsAtWorkPanel />
                  </ErrorBoundary>
                </div>
              )}

              {segment === "agent" && (
                <div className="rounded-[var(--radius)] border border-border bg-card/90 p-6">
                  <ErrorBoundary label="licensed assets">
                    <LicensedAssetsPanel />
                  </ErrorBoundary>
                </div>
              )}

              <div className="rounded-[var(--radius)] border border-border bg-card/90 p-6">
                <ErrorBoundary label={segment}>
                  <ActFor segment={segment} />
                </ErrorBoundary>
              </div>
            </>
          )}
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
