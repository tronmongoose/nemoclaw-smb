/** Supporting section: quiet P&L totals, expense-by-category, ranked findings list. Not boxed. */

import { AnalysisTotals, AnalysisByCategory, AnalysisFinding } from "../../types";
import { formatUSD, formatPct } from "../../lib/format";

interface SupportingSectionProps {
  totals: AnalysisTotals;
  byCategory: AnalysisByCategory[];
  findings: AnalysisFinding[];
}

function PnlTotals({ totals }: { totals: AnalysisTotals }) {
  const netColor = totals.net >= 0 ? "text-emerald-400" : "text-red-400";
  return (
    <div className="flex flex-wrap gap-8">
      <div className="flex flex-col gap-0.5">
        <span className="text-xs uppercase tracking-widest text-slate-500">Income</span>
        <span className="text-lg tabular-nums text-slate-200">{formatUSD(totals.income)}</span>
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="text-xs uppercase tracking-widest text-slate-500">Expense</span>
        <span className="text-lg tabular-nums text-slate-200">{formatUSD(totals.expense)}</span>
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="text-xs uppercase tracking-widest text-slate-500">Net</span>
        <span className={`text-lg tabular-nums ${netColor}`}>{formatUSD(totals.net)}</span>
      </div>
      <div className="flex flex-col gap-0.5">
        <span className="text-xs uppercase tracking-widest text-slate-500">Margin</span>
        <span className={`text-lg tabular-nums ${netColor}`}>{formatPct(totals.margin_pct)}</span>
      </div>
    </div>
  );
}

function CategoryList({ byCategory }: { byCategory: AnalysisByCategory[] }) {
  if (byCategory.length === 0) return null;
  const top = byCategory.slice(0, 8);
  const total = top.reduce((s, c) => s + c.amount, 0);
  return (
    <div className="flex flex-col gap-2">
      {top.map((c) => {
        const pct = total > 0 ? (c.amount / total) * 100 : 0;
        return (
          <div key={c.category} className="flex items-center gap-3">
            <span className="text-xs text-slate-400 w-36 truncate">{c.category}</span>
            <div className="flex-1 h-px bg-slate-800 relative">
              <div
                className="absolute top-0 left-0 h-full bg-amber-600 opacity-50"
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-xs tabular-nums text-slate-300 w-20 text-right">{formatUSD(c.amount)}</span>
          </div>
        );
      })}
    </div>
  );
}

function FindingRow({ f, rank }: { f: AnalysisFinding; rank: number }) {
  const confidenceLabel =
    f.confidence === "high" ? "HIGH" : f.confidence === "medium" ? "MED" : "LOW";
  return (
    <div className="flex flex-col gap-1.5 pt-4 border-t border-slate-800 first:border-t-0 first:pt-0">
      <div className="flex items-baseline gap-3">
        <span className="text-xs tabular-nums text-slate-600 w-4">{rank}.</span>
        <span className="text-sm font-semibold text-slate-100 flex-1">{f.title}</span>
        <span className="text-xs text-slate-600 uppercase tracking-wide">{confidenceLabel}</span>
      </div>
      {f.action && (
        <p className="text-xs text-amber-400 leading-relaxed ml-7">{f.action}</p>
      )}
      <div className="flex gap-4 ml-7">
        <span className="text-xs tabular-nums text-slate-500">
          {formatUSD(f.annual_impact)}/yr
        </span>
        <span className="text-xs tabular-nums text-slate-500">
          {formatUSD(f.monthly_impact)}/mo
        </span>
      </div>
      {f.why && (
        <p className="text-xs text-slate-500 leading-relaxed ml-7">{f.why}</p>
      )}
    </div>
  );
}

export function SupportingSection({ totals, byCategory, findings }: SupportingSectionProps) {
  return (
    <div className="flex flex-col gap-10 pt-8 border-t border-slate-800">
      <div className="flex flex-col gap-4">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">P&L Summary</h3>
        <PnlTotals totals={totals} />
      </div>

      {byCategory.length > 0 && (
        <div className="flex flex-col gap-4">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Expense by category</h3>
          <CategoryList byCategory={byCategory} />
        </div>
      )}

      {findings.length > 0 && (
        <div className="flex flex-col gap-0">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500 mb-4">All findings</h3>
          {findings.map((f, i) => (
            <FindingRow key={`${f.title}-${i}`} f={f} rank={i + 1} />
          ))}
        </div>
      )}
    </div>
  );
}
