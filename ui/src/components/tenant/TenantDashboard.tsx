/** Tenant decision dashboard (v2). Leads with decisions, not a data dump. */

import { TenantAnalysis } from "../../types";
import { useFetch } from "../../hooks/useFetch";
import { SummaryStrip } from "./SummaryStrip";
import { HeadlineBand } from "./HeadlineBand";
import { LongitudinalSection } from "./LongitudinalSection";
import { SupportingSection } from "./SupportingSection";

const TENANT_SLUG = (import.meta.env.VITE_TENANT as string | undefined) ?? "_sample_str";

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-64 gap-3 text-slate-600 text-sm">
      <span>No analysis data</span>
      <span className="text-xs">make tenant-analyze TENANT={TENANT_SLUG}</span>
    </div>
  );
}

export function TenantDashboard() {
  const { data, loading } = useFetch<TenantAnalysis>(`/tenant/${TENANT_SLUG}/analysis`);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-600 text-sm">
        Loading...
      </div>
    );
  }

  if (!data || !data.pnl) {
    return <EmptyState />;
  }

  const totals = data.pnl.totals ?? { income: 0, expense: 0, net: 0, margin_pct: 0 };
  const byMonth = data.pnl.by_month ?? [];
  const byCategory = data.pnl.expense_by_category ?? [];
  const headlines = data.headlines ?? [];
  const findings = data.findings ?? [];
  const longitudinal = data.longitudinal ?? { net_by_month: [], by_category_monthly: [] };

  return (
    <div className="flex flex-col gap-8 max-w-5xl mx-auto py-8 px-4">
      <SummaryStrip
        tenant={data.tenant}
        totals={totals}
        netByMonth={longitudinal.net_by_month ?? []}
        generatedAt={data.generated_at ?? ""}
      />

      {headlines.length > 0 && <HeadlineBand headlines={headlines} />}

      <LongitudinalSection longitudinal={longitudinal} byMonth={byMonth} />

      <SupportingSection totals={totals} byCategory={byCategory} findings={findings} />
    </div>
  );
}
