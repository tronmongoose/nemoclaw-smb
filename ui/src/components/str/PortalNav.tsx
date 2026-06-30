/** The portal top bar: wordmark, numbered tabs that shift the page temperature on
 *  switch (the active tab carries the portal accent + an underline bar), the DEMO/LIVE
 *  toggle, and a tech-layer toggle that overlays where each sponsor plugs in. */

import { cn } from "../../lib/utils";
import { StrSegment } from "../../types";
import { LiveToggle } from "./LiveToggle";

const TABS: { id: StrSegment; label: string }[] = [
  { id: "owner", label: "Owner" },
  { id: "firm", label: "Company" },
  { id: "agent", label: "Swarm" },
];

function Tab({
  tab,
  active,
  onChange,
}: {
  tab: { id: StrSegment; label: string };
  active: boolean;
  onChange: (s: StrSegment) => void;
}) {
  return (
    <button
      onClick={() => onChange(tab.id)}
      aria-pressed={active}
      className="flex flex-col items-center gap-2 bg-transparent px-0 py-1 transition-colors"
    >
      <span
        className={cn(
          "font-mono text-[0.72rem] uppercase tracking-[0.16em] transition-colors",
          active ? "text-foreground" : "text-muted-foreground hover:text-foreground",
        )}
      >
        {tab.label}
      </span>
      <span
        className={cn(
          "h-0.5 w-full rounded-full transition-colors",
          active ? "bg-primary" : "bg-transparent",
        )}
      />
    </button>
  );
}

export function PortalNav({
  view,
  onChange,
  tech,
  onToggleTech,
}: {
  view: StrSegment;
  onChange: (s: StrSegment) => void;
  tech: boolean;
  onToggleTech: () => void;
}) {
  return (
    <header className="border-b border-border">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-5">
        <div className="flex min-w-[180px] items-baseline gap-3">
          <span className="font-serif text-xl font-semibold tracking-tight text-foreground">
            NemoClaw
          </span>
          <span className="font-mono text-[0.62rem] uppercase tracking-[0.22em] text-muted-foreground">
            STR substrate
          </span>
        </div>

        <nav aria-label="Portals" className="flex items-end gap-8 sm:gap-12">
          {TABS.map((t) => (
            <Tab key={t.id} tab={t} active={view === t.id} onChange={onChange} />
          ))}
        </nav>

        <div className="flex min-w-[180px] items-center justify-end gap-3">
          <LiveToggle />
          <button
            onClick={onToggleTech}
            aria-pressed={tech}
            className={cn(
              "flex items-center gap-2 rounded-[var(--radius)] border border-primary px-3 py-1.5 font-mono text-[0.62rem] uppercase tracking-[0.14em] transition-colors",
              tech ? "bg-primary text-primary-foreground" : "bg-transparent text-muted-foreground hover:text-foreground",
            )}
          >
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full transition-colors",
                tech ? "bg-primary-foreground" : "bg-muted-foreground",
              )}
            />
            Tech layer
          </button>
        </div>
      </div>
    </header>
  );
}
