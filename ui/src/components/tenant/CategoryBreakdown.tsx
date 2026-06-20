/** Expense-by-category breakdown using Tremor BarList. */

import { BarList } from "@tremor/react";
import { AnalysisByCategory } from "../../types";
import { formatUSD } from "../../lib/format";

interface CategoryBreakdownProps {
  byCategory: AnalysisByCategory[];
}

export function CategoryBreakdown({ byCategory }: CategoryBreakdownProps) {
  if (byCategory.length === 0) {
    return <div className="text-slate-600 font-mono text-sm">No category data</div>;
  }

  const top10 = byCategory.slice(0, 10);
  const data = top10.map((c) => ({
    name: c.category,
    value: c.amount,
  }));

  return (
    <BarList
      data={data}
      valueFormatter={(v: number) => formatUSD(v)}
      color="amber"
      className="mt-2"
    />
  );
}
