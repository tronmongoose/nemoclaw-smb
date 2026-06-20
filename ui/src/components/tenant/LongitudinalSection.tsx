/** Longitudinal trends: net over time (LineChart) + top expense categories. Not boxed — hairline separated. */

import { LineChart } from "@tremor/react";
import { AnalysisLongitudinal, AnalysisByMonth } from "../../types";
import { formatUSD } from "../../lib/format";

interface LongitudinalSectionProps {
  longitudinal: AnalysisLongitudinal;
  byMonth: AnalysisByMonth[];
}

const TOP_CATEGORIES = 4;

export function LongitudinalSection({ longitudinal, byMonth }: LongitudinalSectionProps) {
  const netByMonth = longitudinal?.net_by_month ?? [];
  const byCatMonthly = longitudinal?.by_category_monthly ?? [];

  const netChartData = netByMonth.map((m) => ({ month: m.month, Net: m.net }));

  // Also show income vs expense if byMonth is present and longitudinal net is thin
  const incomeExpenseData = byMonth.map((m) => ({
    month: m.month,
    Income: m.income,
    Expense: m.expense,
  }));

  const topCats = byCatMonthly.slice(0, TOP_CATEGORIES);
  const catChartData: Record<string, number | string>[] = [];
  if (topCats.length > 0) {
    const allMonths = Array.from(
      new Set(topCats.flatMap((c) => c.series.map((s) => s.month)))
    ).sort();
    for (const month of allMonths) {
      const row: Record<string, number | string> = { month };
      for (const cat of topCats) {
        const pt = cat.series.find((s) => s.month === month);
        row[cat.category] = pt?.value ?? 0;
      }
      catChartData.push(row);
    }
  }

  const hasTrendData = netChartData.length > 0 || incomeExpenseData.length > 0;

  return (
    <div className="flex flex-col gap-10 pt-8 border-t border-slate-800">
      <div className="flex flex-col gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">Net over time</h3>
        {netChartData.length > 0 ? (
          <LineChart
            data={netChartData}
            index="month"
            categories={["Net"]}
            colors={["emerald"]}
            valueFormatter={(v: number) => formatUSD(v)}
            showLegend={false}
            showGridLines={false}
            className="h-44 mt-1"
            connectNulls
          />
        ) : incomeExpenseData.length > 0 ? (
          <LineChart
            data={incomeExpenseData}
            index="month"
            categories={["Income", "Expense"]}
            colors={["emerald", "rose"]}
            valueFormatter={(v: number) => formatUSD(v)}
            showLegend
            showGridLines={false}
            className="h-44 mt-1"
            connectNulls
          />
        ) : (
          <span className="text-sm text-slate-600">No trend data</span>
        )}
        {!hasTrendData && null}
      </div>

      {catChartData.length > 0 && topCats.length > 0 && (
        <div className="flex flex-col gap-2">
          <h3 className="text-xs font-semibold uppercase tracking-widest text-slate-500">
            Top expense categories
          </h3>
          <LineChart
            data={catChartData}
            index="month"
            categories={topCats.map((c) => c.category)}
            colors={["amber", "slate", "zinc", "stone"]}
            valueFormatter={(v: number) => formatUSD(v)}
            showLegend
            showGridLines={false}
            className="h-44 mt-1"
            connectNulls
          />
        </div>
      )}
    </div>
  );
}
