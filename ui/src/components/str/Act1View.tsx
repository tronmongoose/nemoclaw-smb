/** Act I (Owner): management-fee reconciliation.
 *
 * Surfaces the full governed catch-and-correct loop on Sweet Clementine:
 *   - the ledger table (revenue, contract vs charged fee)
 *   - the $84 overcharge the agent catches, with the model+latency badge
 *   - the ConductorOne/Baton NHI and the authorize decision source
 *   - the REQUIRE_APPROVAL hold + an Approve button (re-fetches on approve)
 *   - the signed correction payment + Carryall envelope note
 *   - the audit tail (chain hash + verify state)
 *
 * Fails soft to an empty state when the API is unreachable.
 */

import { useState } from "react";
import { useFetch } from "../../hooks/useFetch";
import { apiPost } from "../../lib/api";
import { StrReconciliationReport } from "../../types";
import { useLive, liveParam } from "./LiveContext";
import { ProvenanceBadge } from "./ProvenanceBadge";
import { centsToUSD, EmptyState, SectionLabel, KV, StatusPill } from "./shared";

const PROP = "prop-001";
const MONTH = "2026-06";

export function Act1View() {
  const { live } = useLive();
  const path = `/str/act1/${PROP}/${MONTH}${liveParam(live)}`;
  const { data, loading, refetch } = useFetch<StrReconciliationReport>(path);

  if (loading) {
    return <div className="h-32 flex items-center justify-center text-slate-600 font-mono text-sm">Reconciling...</div>;
  }
  if (!data || !data.summary) {
    return <EmptyState hint="GET /str/act1/prop-001/2026-06" />;
  }

  return (
    <div className="flex flex-col gap-6">
      <LedgerTable report={data} />
      <AnomalyCatch report={data} />
      <GovernanceBlock report={data} />
      <PaymentBlock report={data} onApprove={refetch} live={live} />
      <AuditTail report={data} />
    </div>
  );
}

function LedgerTable({ report }: { report: StrReconciliationReport }) {
  const s = report.summary;
  const li = s.line_items ?? {};
  return (
    <section>
      <SectionLabel>Ledger: Sweet Clementine ({report.month})</SectionLabel>
      <div className="border border-slate-800 rounded overflow-hidden">
        <table className="w-full font-mono text-xs">
          <tbody className="divide-y divide-slate-800">
            <Row k="Gross revenue" v={centsToUSD(s.revenue_cents)} />
            <Row k={`Contracted fee (${(s.contract_pct * 100).toFixed(1)}%)`} v={centsToUSD(li.contracted_fee_cents ?? 0)} />
            <Row k={`Charged fee (${(s.charged_pct * 100).toFixed(1)}%)`} v={centsToUSD(li.charged_fee_cents ?? 0)} />
            <Row k="Fee delta" v={centsToUSD(li.fee_delta_cents ?? 0)} accent />
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Row({ k, v, accent }: { k: string; v: string; accent?: boolean }) {
  return (
    <tr>
      <td className="px-3 py-2 text-slate-400">{k}</td>
      <td className={`px-3 py-2 text-right ${accent ? "text-amber-300 font-bold" : "text-slate-200"}`}>{v}</td>
    </tr>
  );
}

function AnomalyCatch({ report }: { report: StrReconciliationReport }) {
  const a = report.anomaly;
  if (!a) return null;
  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <SectionLabel>Anomaly</SectionLabel>
        <ProvenanceBadge prov={a.reasoning_provenance} />
      </div>
      <div className="border border-amber-900 bg-amber-950/30 rounded p-4 font-mono text-xs flex flex-col gap-2">
        <div className="flex items-baseline justify-between">
          <span className="text-amber-300 font-bold uppercase tracking-wide">
            {a.is_anomaly ? "Overcharge caught" : "No anomaly"}
          </span>
          <span className="text-amber-300 font-bold text-base">{centsToUSD(a.overcharge_cents)}</span>
        </div>
        <p className="text-slate-300 leading-relaxed">{a.reason}</p>
        <p className="text-slate-500 leading-relaxed border-t border-slate-800 pt-2 mt-1">{a.reasoning_trace}</p>
      </div>
    </section>
  );
}

function GovernanceBlock({ report }: { report: StrReconciliationReport }) {
  // The NHI id prefix carries the agent identity; governance routes through
  // OSS Baton + carryall when a .c1z is present, else a synthetic decision.
  const isBaton = report.nhi_id.includes("str-owner-agent");
  const source = isBaton ? "baton-carryall" : "synthetic";
  return (
    <section>
      <SectionLabel>ConductorOne / Baton governance</SectionLabel>
      <div className="border border-slate-800 rounded p-4">
        <KV label="NHI" value={report.nhi_id} />
        <KV label="scopes" value="ledger:read, payment:propose" />
        <KV label="authorize decision" value={source === "baton-carryall" ? "ALLOW (baton-carryall)" : "ALLOW (synthetic)"} accent />
        <KV label="decision source" value={source} />
      </div>
    </section>
  );
}

function PaymentBlock({
  report,
  onApprove,
  live,
}: {
  report: StrReconciliationReport;
  onApprove: () => void;
  live: boolean;
}) {
  const p = report.payment;
  const [deciding, setDeciding] = useState(false);

  async function approve() {
    if (!p?.request_id) return;
    setDeciding(true);
    await apiPost(`/approvals/${p.request_id}/decide`, { approved: true, decided_by: "owner" });
    setDeciding(false);
    onApprove();
  }

  if (!p) {
    return (
      <section>
        <SectionLabel>Correction payment</SectionLabel>
        <div className="border border-slate-800 rounded p-4 font-mono text-xs text-slate-500">
          No payment proposed (no anomaly to correct).
        </div>
      </section>
    );
  }

  if (p.held_for_approval) {
    return (
      <section>
        <SectionLabel>REQUIRE_APPROVAL hold</SectionLabel>
        <div className="border border-amber-900 bg-amber-950/30 rounded p-4 font-mono text-xs flex flex-col gap-3">
          <p className="text-amber-300">
            Correction of {centsToUSD(p.amount_cents)} exceeds the auto-approve threshold. Human approval required.
          </p>
          <KV label="status" value={p.status} accent />
          <KV label="request_id" value={p.request_id} />
          <button
            disabled={deciding || !live}
            onClick={() => void approve()}
            title={live ? "" : "Approve runs against the real approval queue in LIVE"}
            className="self-start px-4 py-2 rounded bg-emerald-800 hover:bg-emerald-700 text-emerald-100 border border-emerald-700 disabled:opacity-40"
          >
            {deciding ? "Approving..." : "Approve correction"}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section>
      <SectionLabel>Signed correction payment</SectionLabel>
      <div className="border border-slate-800 rounded p-4">
        <KV label="payment_id" value={p.payment_id} />
        <KV label="amount" value={centsToUSD(p.amount_cents)} accent />
        <KV label="status" value={p.status} />
        <p className="text-slate-500 font-mono text-xs mt-3 pt-3 border-t border-slate-800 leading-relaxed">
          Signed under a Carryall envelope (str_owner_refund), scoped to the str-owner-agent NHI, then written to the
          hash-chained audit log before the Stripe call.
        </p>
      </div>
    </section>
  );
}

function AuditTail({ report }: { report: StrReconciliationReport }) {
  const hash = report.payment?.audit_hash ?? "";
  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <SectionLabel>Audit tail</SectionLabel>
        <StatusPill ok={report.audit_ok} label={report.audit_ok ? "CHAIN OK" : "CHAIN FAULT"} />
      </div>
      <div className="border border-slate-800 rounded p-4 font-mono text-xs">
        <KV label="detail" value={report.audit_detail || "n/a"} />
        {hash && <KV label="entry_hash" value={`${hash.slice(0, 24)}...`} />}
      </div>
    </section>
  );
}
