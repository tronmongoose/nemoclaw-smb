/** KPI tiles: Income, Expense, Net, Margin % for the tenant dashboard. */

import { AnalysisTotals } from "../../types";
import { formatUSD, formatPct } from "../../lib/format";

interface KpiTilesProps {
  totals: AnalysisTotals;
}

interface TileProps {
  label: string;
  value: string;
  accent: string;
}

function Tile({ label, value, accent }: TileProps) {
  return (
    <div className="flex flex-col bg-slate-800 border border-slate-700 rounded-lg p-4">
      <span className="text-xs font-mono uppercase tracking-widest text-slate-500 mb-1">
        {label}
      </span>
      <span className={`text-xl font-mono font-bold ${accent}`}>{value}</span>
    </div>
  );
}

export function KpiTiles({ totals }: KpiTilesProps) {
  const netAccent = totals.net >= 0 ? "text-emerald-400" : "text-red-400";
  const marginAccent = totals.margin_pct >= 0 ? "text-cyan-400" : "text-red-400";

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <Tile label="Income" value={formatUSD(totals.income)} accent="text-slate-100" />
      <Tile label="Expense" value={formatUSD(totals.expense)} accent="text-amber-400" />
      <Tile label="Net" value={formatUSD(totals.net)} accent={netAccent} />
      <Tile label="Margin" value={formatPct(totals.margin_pct)} accent={marginAccent} />
    </div>
  );
}
