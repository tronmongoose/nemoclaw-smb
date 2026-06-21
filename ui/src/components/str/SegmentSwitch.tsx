/** The three audience segments: who is using the agent, at what scale. */

import { cn } from "../../lib/utils";
import { StrSegment } from "../../types";

const SEGMENTS: { id: StrSegment; label: string; sub: string }[] = [
  { id: "owner", label: "Owner", sub: "one or more rentals" },
  { id: "firm", label: "Management firm", sub: "many owners and crews" },
  { id: "agent", label: "Agent platform", sub: "many firms, earn per call" },
];

export function SegmentSwitch({
  segment,
  onChange,
}: {
  segment: StrSegment;
  onChange: (s: StrSegment) => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {SEGMENTS.map((s) => (
        <button
          key={s.id}
          onClick={() => onChange(s.id)}
          aria-pressed={segment === s.id}
          className={cn(
            "flex flex-col items-start gap-0.5 rounded-[var(--radius)] border p-4 text-left transition-colors",
            segment === s.id
              ? "border-primary bg-[hsl(var(--primary)/0.1)]"
              : "border-border bg-card/80 hover:border-primary/50",
          )}
        >
          <span className="font-serif text-base font-semibold text-foreground">{s.label}</span>
          <span className="font-mono text-[0.7rem] uppercase tracking-[0.18em] text-muted-foreground">
            {s.sub}
          </span>
        </button>
      ))}
    </div>
  );
}
