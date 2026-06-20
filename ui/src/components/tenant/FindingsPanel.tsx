/** Ranked findings cards: title, confidence badge, monthly/annual impact, why. */

import { AnalysisFinding } from "../../types";
import { formatUSD } from "../../lib/format";

interface FindingsPanelProps {
  findings: AnalysisFinding[];
}

const CONFIDENCE_STYLES: Record<string, string> = {
  high: "bg-red-950 text-red-400 border-red-800",
  medium: "bg-amber-950 text-amber-400 border-amber-800",
  low: "bg-slate-800 text-slate-400 border-slate-700",
};

function FindingCard({ f }: { f: AnalysisFinding }) {
  const badgeStyle = CONFIDENCE_STYLES[f.confidence] ?? CONFIDENCE_STYLES.low;

  return (
    <div className="flex flex-col gap-1.5 bg-slate-800 border border-slate-700 rounded-lg p-4">
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-mono font-semibold text-slate-100">{f.title}</span>
        <span className={`text-xs font-mono px-2 py-0.5 rounded border shrink-0 ${badgeStyle}`}>
          {f.confidence.toUpperCase()}
        </span>
      </div>
      <div className="flex gap-4 text-xs font-mono text-slate-500">
        <span>
          Monthly: <span className="text-amber-400">{formatUSD(f.monthly_impact)}</span>
        </span>
        <span>
          Annual: <span className="text-amber-300">{formatUSD(f.annual_impact)}</span>
        </span>
      </div>
      <p className="text-xs text-slate-400 leading-relaxed">{f.why}</p>
    </div>
  );
}

export function FindingsPanel({ findings }: FindingsPanelProps) {
  if (findings.length === 0) {
    return <div className="text-slate-600 font-mono text-sm">No findings</div>;
  }

  return (
    <div className="flex flex-col gap-3">
      {findings.map((f, i) => (
        <FindingCard key={`${f.title}-${i}`} f={f} />
      ))}
    </div>
  );
}
