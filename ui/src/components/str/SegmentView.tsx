/** The converged portal experience. One page per portal: an editorial hero with a live
 *  summary card on top, the real working Act below as proof. The top nav shifts the whole
 *  page temperature on switch (warm-light -> cool-dark -> electric-dark); a tech-layer
 *  toggle overlays where each sponsor plugs in. */

import { useState } from "react";
import { ErrorBoundary } from "../ErrorBoundary";
import { StrSegment } from "../../types";
import { cn } from "../../lib/utils";
import { LiveProvider } from "./LiveContext";
import { AtmosphereBackground } from "./AtmosphereBackground";
import { PortalNav } from "./PortalNav";
import { HeroSection } from "./HeroSection";
import { TechLayerStrip } from "./techlayer/TechLayerStrip";
import { SegmentNodeGraph } from "./SegmentNodeGraph";
import { ConsoleSidebar } from "./ConsoleSidebar";
import { InteractionsPanel } from "./InteractionsPanel";
import { AgentsAtWorkPanel } from "./AgentsAtWorkPanel";
import { LicensedAssetsPanel } from "./LicensedAssetsPanel";
import { Act1View } from "./Act1View";
import { Act2View } from "./Act2View";
import { Act3View } from "./Act3View";

const CONSOLE_LABEL: Record<StrSegment, string> = {
  owner: "The working agent",
  firm: "Live operations",
  agent: "Agent-to-agent commerce",
};

function ActFor({ segment }: { segment: StrSegment }) {
  if (segment === "owner") return <Act1View />;
  if (segment === "firm") return <Act2View />;
  return <Act3View />;
}

function TemperatureLegend({ view }: { view: StrSegment }) {
  const words: { id: StrSegment; label: string }[] = [
    { id: "owner", label: "Warm" },
    { id: "firm", label: "Cool" },
    { id: "agent", label: "Electric" },
  ];
  return (
    <footer className="border-t border-border">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-6 py-4 font-mono text-[0.6rem] uppercase tracking-[0.18em] text-muted-foreground">
        <span>Temperature</span>
        <div className="flex items-center gap-2">
          {words.map((w, i) => (
            <span key={w.id} className="flex items-center gap-2">
              {i > 0 && <span className="opacity-40">·</span>}
              <span className={cn("transition-colors", view === w.id ? "text-primary" : "")}>{w.label}</span>
            </span>
          ))}
        </div>
        <div
          className="hidden h-0.5 flex-1 rounded-full opacity-55 sm:block"
          style={{ background: "linear-gradient(90deg, hsl(26 74% 50%), hsl(202 80% 56%), hsl(188 95% 55%))" }}
        />
        <span>Scale ↗</span>
      </div>
    </footer>
  );
}

export function SegmentView({ onLegacy }: { onLegacy?: () => void }) {
  const [view, setView] = useState<StrSegment>("owner");
  const [tech, setTech] = useState(false);

  return (
    <LiveProvider>
      <div
        data-portal={view}
        data-tech={tech ? "on" : "off"}
        className="flex min-h-screen flex-col bg-background text-foreground transition-colors duration-700 ease-out"
      >
        <AtmosphereBackground portal={view} />
        <PortalNav view={view} onChange={setView} tech={tech} onToggleTech={() => setTech((t) => !t)} />

        <main className="flex-1">
          <HeroSection portal={view} />

          {tech && (
            <ErrorBoundary label="tech layer">
              <TechLayerStrip portal={view} />
            </ErrorBoundary>
          )}

          <section id="console" className="mx-auto w-full max-w-6xl scroll-mt-6 px-6 pb-20 pt-2">
            <div className="mb-6 flex items-center gap-3">
              <span className="font-mono text-[0.66rem] uppercase tracking-[0.2em] text-muted-foreground">
                {CONSOLE_LABEL[view]}
              </span>
              <span className="h-px flex-1 bg-border" />
            </div>

            <div className="flex gap-6">
              <ConsoleSidebar segment={view} />

              <div className="flex min-w-0 flex-1 flex-col gap-6">
                <div className="rounded-[var(--radius)] border border-border bg-card/90 p-6">
                  <ErrorBoundary label={view}>
                    <ActFor segment={view} />
                  </ErrorBoundary>
                </div>

                <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
                  <ErrorBoundary label="entity graph">
                    <SegmentNodeGraph segment={view} />
                  </ErrorBoundary>
                  <ErrorBoundary label="interactions">
                    <InteractionsPanel segment={view} />
                  </ErrorBoundary>
                </div>

                {view === "firm" && (
                  <ErrorBoundary label="agents at work">
                    <AgentsAtWorkPanel />
                  </ErrorBoundary>
                )}
                {view === "agent" && (
                  <ErrorBoundary label="licensed assets">
                    <LicensedAssetsPanel />
                  </ErrorBoundary>
                )}
              </div>
            </div>
          </section>
        </main>

        <TemperatureLegend view={view} />

        {onLegacy && (
          <div className="border-t border-border px-6 py-3">
            <div className="mx-auto flex max-w-6xl items-center justify-between">
              <span className="font-mono text-[0.6rem] text-muted-foreground/60">
                Oceanside Pier photo: Mark Neal on Unsplash
              </span>
              <button
                onClick={onLegacy}
                className="font-mono text-[0.62rem] uppercase tracking-[0.2em] text-muted-foreground/60 transition-colors hover:text-muted-foreground"
              >
                Legacy demos
              </button>
            </div>
          </div>
        )}
      </div>
    </LiveProvider>
  );
}
