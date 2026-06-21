/** STR sub-nav: Owner | Management | Platform | Audit. Editorial underline, recedes. */

import { cn } from "../../lib/utils";

export type StrTab = "stack" | "owner" | "management" | "platform" | "audit";

const TABS: Array<{ id: StrTab; label: string }> = [
  { id: "stack", label: "Stack" },
  { id: "owner", label: "Owner" },
  { id: "management", label: "Management" },
  { id: "platform", label: "Platform" },
  { id: "audit", label: "Audit" },
];

export function StrNav({ tab, onChange }: { tab: StrTab; onChange: (t: StrTab) => void }) {
  return (
    <nav className="flex items-center gap-6">
      {TABS.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          aria-current={tab === t.id}
          className={cn(
            "border-b-2 pb-1 font-mono text-xs uppercase tracking-[0.18em] transition-colors",
            tab === t.id
              ? "border-primary text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground",
          )}
        >
          {t.label}
        </button>
      ))}
    </nav>
  );
}
