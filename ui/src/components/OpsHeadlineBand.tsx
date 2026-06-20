/** Single-signal headline band for the Ops dashboard.
 * Fetches /invoices/anomalies, /approvals/pending, /savings/summary.
 * Renders nothing on fetch failure (fail-soft). One amber accent on the
 * thing that needs attention; all other text is high-contrast neutral.
 */

import { useFetch } from "../hooks/useFetch";
import { AnomalyRecord, ApprovalItem, SavingsSummary } from "../types";
import { formatUSD } from "../lib/format";

export function OpsHeadlineBand() {
  const { data: anomalies } = useFetch<AnomalyRecord[]>("/invoices/anomalies?threshold=2.0");
  const { data: pending } = useFetch<ApprovalItem[]>("/approvals/pending");
  const { data: savings } = useFetch<SavingsSummary>("/savings/summary");

  // Fail-soft: if all three are null (API down / first paint), render nothing.
  if (anomalies === null && pending === null && savings === null) {
    return null;
  }

  const flagged = anomalies ? anomalies.filter((a) => a.is_anomaly) : [];
  const topAnomaly = flagged[0] ?? null;
  const pendingCount = pending ? pending.length : 0;
  const annualSavings = savings ? savings.annual_savings : null;

  // All clear: no anomalies, no pending, no savings data yet — render quiet state.
  if (flagged.length === 0 && pendingCount === 0 && annualSavings === null) {
    return (
      <div className="mb-4 px-4 py-3 border border-slate-800 text-slate-500 font-mono text-sm">
        All clear — no anomalies flagged, no approvals pending.
      </div>
    );
  }

  return (
    <div className="mb-4 px-4 py-3 border border-slate-700 bg-slate-900 font-mono text-sm flex flex-wrap items-baseline gap-x-6 gap-y-1">
      {topAnomaly && (
        <AnomalySegment anomaly={topAnomaly} total={flagged.length} />
      )}
      {pendingCount > 0 && (
        <span className="text-slate-200">
          <span className="text-amber-400 font-bold">{pendingCount}</span>{" "}
          {pendingCount === 1 ? "approval" : "approvals"} pending
        </span>
      )}
      {annualSavings !== null && annualSavings > 0 && (
        <span className="text-slate-200">
          {formatUSD(annualSavings)}/yr savings identified
        </span>
      )}
    </div>
  );
}

function AnomalySegment({
  anomaly,
  total,
}: {
  anomaly: AnomalyRecord;
  total: number;
}) {
  const pct = Math.round(anomaly.pct_change);
  const label =
    total === 1
      ? "1 anomaly flagged"
      : `${total} anomalies flagged`;

  return (
    <span className="text-slate-200">
      <span className="text-amber-400 font-bold">{label}</span>
      {" — "}
      {anomaly.vendor}{" "}
      <span className="text-amber-400 font-bold">+{pct}%</span>
      {" ("}
      {formatUSD(anomaly.current_amount)} vs ~{formatUSD(anomaly.baseline_mean)}
      {")"}
    </span>
  );
}
