/** STR sub-nav: Owner | Management | Platform | Audit. Mirrors NavToggle style. */

export type StrTab = "owner" | "management" | "platform" | "audit";

const TABS: Array<{ id: StrTab; label: string }> = [
  { id: "owner", label: "Owner" },
  { id: "management", label: "Management" },
  { id: "platform", label: "Platform" },
  { id: "audit", label: "Audit" },
];

export function StrNav({ tab, onChange }: { tab: StrTab; onChange: (t: StrTab) => void }) {
  return (
    <div className="flex items-center gap-2">
      {TABS.map((t) => (
        <button
          key={t.id}
          onClick={() => onChange(t.id)}
          className={[
            "px-3 py-1 text-xs font-mono rounded border transition-colors",
            tab === t.id
              ? "bg-cyan-900 border-cyan-700 text-cyan-300"
              : "bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200",
          ].join(" ")}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}
