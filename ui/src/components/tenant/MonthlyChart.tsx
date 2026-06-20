/** Monthly trend chart: income vs expense vs net by month. Uses Tremor BarChart. */

import { BarChart } from "@tremor/react";
import { AnalysisByMonth } from "../../types";
import { formatUSD } from "../../lib/format";

interface MonthlyChartProps {
  byMonth: AnalysisByMonth[];
}

export function MonthlyChart({ byMonth }: MonthlyChartProps) {
  if (byMonth.length === 0) {
    return <div className="text-slate-600 font-mono text-sm">No monthly data</div>;
  }

  const chartData = byMonth.map((m) => ({
    month: m.month,
    Income: m.income,
    Expense: m.expense,
    Net: m.net,
  }));

  return (
    <BarChart
      data={chartData}
      index="month"
      categories={["Income", "Expense", "Net"]}
      colors={["cyan", "amber", "emerald"]}
      valueFormatter={(v: number) => formatUSD(v)}
      showLegend
      showGridLines={false}
      className="h-48 mt-2"
    />
  );
}
