/** Tenant P&L + findings dashboard. Slug resolved from VITE_TENANT env (default: _sample_str). */

import { TenantAnalysis } from "../../types";
import { useFetch } from "../../hooks/useFetch";
import { PanelCard } from "../PanelCard";
import { KpiTiles } from "./KpiTiles";
import { MonthlyChart } from "./MonthlyChart";
import { CategoryBreakdown } from "./CategoryBreakdown";
import { FindingsPanel } from "./FindingsPanel";

const TENANT_SLUG = (import.meta.env.VITE_TENANT as string | undefined) ?? "_sample_str";

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-600 font-mono">
      <span className="text-lg">No analysis data</span>
      <span className="text-sm">Run tenant-analyze first: make tenant-analyze TENANT={TENANT_SLUG}</span>
    </div>
  );
}

export function TenantDashboard() {
  const { data, loading } = useFetch<TenantAnalysis>(`/tenant/${TENANT_SLUG}/analysis`);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-600 font-mono text-sm">
        Loading...
      </div>
    );
  }

  if (!data || !data.pnl) {
    return <EmptyState />;
  }

  const generated_at = data.generated_at ?? "";
  const findings = data.findings ?? [];
  const pnl = {
    totals: data.pnl.totals ?? { income: 0, expense: 0, net: 0, margin_pct: 0 },
    by_month: data.pnl.by_month ?? [],
    expense_by_category: data.pnl.expense_by_category ?? [],
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono text-slate-500 uppercase tracking-widest">
          Tenant: <span className="text-cyan-500">{data.tenant}</span>
        </span>
        <span className="text-xs font-mono text-slate-600">
          Generated: {generated_at}
        </span>
      </div>

      <KpiTiles totals={pnl.totals} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <PanelCard title="Monthly Trend">
          <MonthlyChart byMonth={pnl.by_month} />
        </PanelCard>

        <PanelCard title="Expense by Category">
          <CategoryBreakdown byCategory={pnl.expense_by_category} />
        </PanelCard>
      </div>

      <PanelCard title={`Advisory Findings (${findings.length})`}>
        <FindingsPanel findings={findings} />
      </PanelCard>
    </div>
  );
}
