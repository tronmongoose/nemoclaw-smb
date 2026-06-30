/** ConsoleSidebar: a sticky left rail for the console. Gives each portal structure
 *  instead of a wall of text: a section navigator that jumps to the panels, a live/demo
 *  status legend, and the API routes that used to clutter the panel bodies. */

import { StrSegment } from "../../types";
import { useLive } from "./LiveContext";
import { SectionLabel } from "./shared";
import { cn } from "../../lib/utils";

const SECTIONS: Record<StrSegment, { id: string; label: string }[]> = {
  owner: [
    { id: "section-turnover", label: "Turnover loop" },
    { id: "section-ledger", label: "Ledger" },
    { id: "section-anomaly", label: "Anomaly" },
    { id: "section-payment", label: "Correction" },
    { id: "section-audit", label: "Audit chain" },
  ],
  firm: [
    { id: "section-turnover", label: "Turnover loop" },
    { id: "section-stalls", label: "Stalled handoffs" },
    { id: "section-scheduling", label: "Cleaner scheduling" },
    { id: "section-portfolio", label: "Portfolio graph" },
    { id: "section-performance", label: "Performance" },
  ],
  agent: [
    { id: "section-marketing", label: "Marketing" },
    { id: "section-sales", label: "Sales" },
    { id: "section-pricing", label: "Pricing" },
    { id: "section-marketplace", label: "Marketplace" },
  ],
};

const API_REF: Record<StrSegment, string[]> = {
  owner: ["GET /str/act1/{prop}/{month}", "POST /approvals/{id}/decide"],
  firm: ["GET /str/turnover", "GET /str/stalls", "GET /str/performance"],
  agent: ["POST /str/act3/price", "POST /str/act3/aeo-audit", "GET /str/act3/metrics"],
};

const TEMPS: { id: StrSegment; label: string }[] = [
  { id: "owner", label: "Warm" },
  { id: "firm", label: "Cool" },
  { id: "agent", label: "Electric" },
];

function jump(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

export function ConsoleSidebar({ segment }: { segment: StrSegment }) {
  const { live } = useLive();

  return (
    <aside className="hidden w-56 shrink-0 lg:block">
      <div className="sticky top-6 flex flex-col gap-6 rounded-[var(--radius)] border border-border bg-card/60 p-4">
        <div>
          <SectionLabel>Sections</SectionLabel>
          <nav className="flex flex-col gap-0.5">
            {SECTIONS[segment].map((s) => (
              <button
                key={s.id}
                onClick={() => jump(s.id)}
                className="rounded-[var(--radius)] px-2 py-1.5 text-left font-mono text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                {s.label}
              </button>
            ))}
          </nav>
        </div>

        <div>
          <SectionLabel>Status</SectionLabel>
          <div className="flex items-center gap-2 px-2 font-mono text-xs">
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full",
                live ? "bg-primary animate-heartbeat" : "bg-muted-foreground/50",
              )}
            />
            <span className={live ? "text-primary" : "text-muted-foreground"}>
              {live ? "LIVE — real model calls" : "DEMO — cached traces"}
            </span>
          </div>
          <div className="mt-2 flex items-center gap-2 px-2 font-mono text-[0.6rem] uppercase tracking-[0.16em] text-muted-foreground">
            {TEMPS.map((t, i) => (
              <span key={t.id} className="flex items-center gap-2">
                {i > 0 && <span className="opacity-40">·</span>}
                <span className={cn(segment === t.id && "text-primary")}>{t.label}</span>
              </span>
            ))}
          </div>
        </div>

        <div>
          <SectionLabel>Endpoints</SectionLabel>
          <ul className="flex flex-col gap-1 px-2">
            {API_REF[segment].map((r) => (
              <li key={r} className="font-mono text-[0.62rem] leading-relaxed text-muted-foreground/70">
                {r}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </aside>
  );
}
