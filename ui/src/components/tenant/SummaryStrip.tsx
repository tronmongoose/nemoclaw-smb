/** One-line summary strip: tenant name, Net (semantic color), Margin %, direction vs prior period. */

import { AnalysisTotals, LongitudinalNetMonth } from "../../types";
import { formatUSD, formatPct } from "../../lib/format";

interface SummaryStripProps {
  tenant: string;
  totals: AnalysisTotals;
  netByMonth: LongitudinalNetMonth[];
  generatedAt: string;
}

function directionLabel(netByMonth: LongitudinalNetMonth[]): string | null {
  if (netByMonth.length < 13) return null;
  const recent = netByMonth.slice(-6);
  const prior = netByMonth.slice(-12, -6);
  const recentAvg = recent.reduce((s, m) => s + m.net, 0) / recent.length;
  const priorAvg = prior.reduce((s, m) => s + m.net, 0) / prior.length;
  if (priorAvg === 0) return null;
  const pct = ((recentAvg - priorAvg) / Math.abs(priorAvg)) * 100;
  const sign = pct >= 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}% vs prior 6mo`;
}

export function SummaryStrip({ tenant, totals, netByMonth, generatedAt }: SummaryStripProps) {
  const netColor = totals.net >= 0 ? "text-emerald-400" : "text-red-400";
  const marginColor = totals.margin_pct >= 0 ? "text-emerald-400" : "text-red-400";
  const direction = directionLabel(netByMonth);

  return (
    <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1 pb-5 border-b border-slate-800">
      <span className="text-base font-semibold text-slate-100 tracking-tight">{tenant}</span>
      <span className={`text-2xl font-bold tabular-nums ${netColor}`}>
        {formatUSD(totals.net)}
      </span>
      <span className={`text-sm tabular-nums ${marginColor}`}>
        {formatPct(totals.margin_pct)} margin
      </span>
      {direction && (
        <span className="text-xs text-slate-400 uppercase tracking-wide">{direction}</span>
      )}
      <span className="ml-auto text-xs text-slate-600 tabular-nums">{generatedAt}</span>
    </div>
  );
}
