/** The portal nav: three principals at three scales, plus the cross-cutting tech layer.
 *  Switching a portal retunes the whole page temperature (warm -> cool -> electric);
 *  the active item adopts the live portal accent so the nav signals the shift. */

import { cn } from "../../lib/utils";
import { PortalView } from "../../types";

const PORTALS: { id: PortalView; label: string; sub: string }[] = [
  { id: "owner", label: "Owner", sub: "one property, governed" },
  { id: "firm", label: "Company", sub: "many properties, agents at work" },
  { id: "agent", label: "Swarm", sub: "many firms, agents as licensed assets" },
];

const STACK: { id: PortalView; label: string; sub: string } = {
  id: "stack",
  label: "Tech Layer",
  sub: "where the stack plugs in",
};

function NavItem({
  item,
  active,
  onChange,
}: {
  item: { id: PortalView; label: string; sub: string };
  active: boolean;
  onChange: (v: PortalView) => void;
}) {
  return (
    <button
      onClick={() => onChange(item.id)}
      aria-pressed={active}
      className={cn(
        "flex flex-col items-start gap-0.5 rounded-[var(--radius)] border px-4 py-3 text-left transition-colors",
        active
          ? "border-primary bg-[hsl(var(--primary)/0.12)]"
          : "border-border bg-card/70 hover:border-primary/50",
      )}
    >
      <span
        className={cn(
          "font-serif text-base font-semibold",
          active ? "text-primary" : "text-foreground",
        )}
      >
        {item.label}
      </span>
      <span className="font-mono text-[0.66rem] uppercase tracking-[0.16em] text-muted-foreground">
        {item.sub}
      </span>
    </button>
  );
}

export function SegmentSwitch({
  view,
  onChange,
}: {
  view: PortalView;
  onChange: (v: PortalView) => void;
}) {
  return (
    <nav
      aria-label="Portals"
      className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4"
    >
      {PORTALS.map((p) => (
        <NavItem key={p.id} item={p} active={view === p.id} onChange={onChange} />
      ))}
      <NavItem item={STACK} active={view === "stack"} onChange={onChange} />
    </nav>
  );
}
