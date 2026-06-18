/** Savings panel: Tremor metrics + NemoClaw fee callout + ranked alternatives. */

import { Metric, Text, Card, BadgeDelta } from "@tremor/react";
import { useFetch } from "../hooks/useFetch";
import { SavingsSummary, AlternativesResponse } from "../types";
import { formatUSD, formatPct } from "../lib/format";

const CURRENT_VENDOR = "Adobe Creative Cloud";

export function SavingsPanel() {
  const { data: summary } = useFetch<SavingsSummary>("/savings/summary");
  const { data: alts } = useFetch<AlternativesResponse>(
    `/savings/alternatives?current_vendor=${encodeURIComponent(CURRENT_VENDOR)}`
  );

  return (
    <div className="flex flex-col gap-4">
      <SummaryMetrics summary={summary} />
      {alts && <AlternativesList alts={alts} />}
    </div>
  );
}

function SummaryMetrics({ summary }: { summary: SavingsSummary | null }) {
  if (!summary) {
    return (
      <div className="text-slate-600 font-mono text-sm">Savings data unavailable</div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      <MetricTile
        label="Total Spend"
        value={formatUSD(summary.total_spend, summary.currency)}
        accent="text-slate-200"
      />
      <MetricTile
        label="Monthly Savings"
        value={formatUSD(summary.monthly_savings, summary.currency)}
        accent="text-emerald-400"
        delta="increase"
      />
      <MetricTile
        label="Annual Savings"
        value={formatUSD(summary.annual_savings, summary.currency)}
        accent="text-emerald-400"
        delta="increase"
      />
      <NemoclawFeeTile fee={summary.nemoclaw_fee} rate={summary.fee_rate} currency={summary.currency} />
    </div>
  );
}

function MetricTile({
  label,
  value,
  accent,
  delta,
}: {
  label: string;
  value: string;
  accent: string;
  delta?: "increase" | "decrease";
}) {
  return (
    <Card className="!bg-slate-800 !border-slate-700 p-3">
      <Text className="!text-slate-500 !text-xs font-mono uppercase tracking-widest">
        {label}
      </Text>
      <div className="flex items-center gap-2 mt-1">
        <Metric className={`!text-base !font-mono ${accent}`}>{value}</Metric>
        {delta && <BadgeDelta deltaType={delta} size="xs" />}
      </div>
    </Card>
  );
}

function NemoclawFeeTile({
  fee,
  rate,
  currency,
}: {
  fee: number;
  rate: number;
  currency: string;
}) {
  return (
    <Card className="!bg-cyan-950/60 !border-cyan-800 p-3 col-span-2">
      <Text className="!text-cyan-500 !text-xs font-mono uppercase tracking-widest">
        NemoClaw fee ({formatPct(rate * 100, 1)} — agent pays for itself)
      </Text>
      <Metric className="!text-base !font-mono !text-cyan-300 mt-1">
        {formatUSD(fee, currency)}
      </Metric>
    </Card>
  );
}

function AlternativesList({ alts }: { alts: AlternativesResponse }) {
  return (
    <div>
      <div className="text-xs font-mono text-slate-500 uppercase tracking-widest mb-2">
        Alternatives to {alts.current.vendor} ({formatUSD(alts.current.amount)}/mo)
      </div>
      <div className="flex flex-col gap-1.5">
        {alts.ranked.map((a) => (
          <div
            key={a.vendor}
            className="flex items-center justify-between text-xs font-mono bg-slate-800 rounded px-3 py-1.5 border border-slate-700"
          >
            <div className="flex items-center gap-2">
              <span className="text-slate-600">#{a.rank}</span>
              <span className="text-slate-200">{a.vendor}</span>
              <span className="text-slate-500">{formatUSD(a.amount)}/mo</span>
            </div>
            <span className="text-emerald-400">
              saves {formatUSD(a.monthly_savings)}/mo
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
