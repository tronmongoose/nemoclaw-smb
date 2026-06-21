/** Act II (Management): property-management orchestration.
 *
 *   - a Checkout button -> issues a single-use cleaner card under a scoped NHI;
 *     renders token, $75 cap, MCC allow-list, same-day expiry, and "NO PAN"
 *   - the month-end crew payouts table
 *   - per-owner UBP invoices (line items + totals)
 *   - the portfolio summary across the managed properties
 *
 * Fails soft to empty states when the API is unreachable.
 */

import { useState } from "react";
import { useFetch } from "../../hooks/useFetch";
import { apiPost } from "../../lib/api";
import { liveParam, useLive } from "./LiveContext";
import {
  StrCleanerCard,
  StrInvoicesResponse,
  StrPayoutBatch,
  StrPortfolioSummary,
} from "../../types";
import { centsToUSD, EmptyState, KV, SectionLabel } from "./shared";

const PROP = "prop-001";
const MONTH = "2026-06";
const CHECKOUT_DATE = "2026-06-15";

export function Act2View() {
  return (
    <div className="flex flex-col gap-6">
      <CheckoutBlock />
      <PayoutsTable />
      <InvoicesBlock />
      <PortfolioBlock />
    </div>
  );
}

function CheckoutBlock() {
  const { live } = useLive();
  const [card, setCard] = useState<StrCleanerCard | null>(null);
  const [busy, setBusy] = useState(false);

  async function issue() {
    setBusy(true);
    const res = await apiPost<StrCleanerCard>(`/str/act2/checkout${liveParam(live)}`, {
      property_id: PROP,
      checkout_date: CHECKOUT_DATE,
    });
    setCard(res);
    setBusy(false);
  }

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <SectionLabel>Guest checkout: issue cleaner card</SectionLabel>
        <button
          disabled={busy}
          onClick={() => void issue()}
          className="px-4 py-1.5 rounded bg-cyan-900 hover:bg-cyan-800 text-cyan-200 border border-cyan-700 font-mono text-xs disabled:opacity-40"
        >
          {busy ? "Issuing..." : "Trigger checkout"}
        </button>
      </div>
      {!card ? (
        <div className="border border-slate-800 rounded p-4 font-mono text-xs text-slate-500">
          A least-privilege NHI (cleaner-subagent, scope card:issue:cleaning) is issued and authorized before any card.
        </div>
      ) : (
        <div className="border border-slate-800 rounded p-4">
          <KV label="scoped NHI" value="cleaner-subagent / card:issue:cleaning" />
          <KV label="card token" value={card.card_token} accent />
          <KV label="single-use cap" value={centsToUSD(card.amount_cap_cents)} />
          <KV label="MCC allow-list" value={card.mcc_list.join(", ")} />
          <KV label="expires (EOD)" value={card.expiry_utc} />
          <div className="mt-3 pt-3 border-t border-slate-800 flex items-center gap-2 font-mono text-xs">
            <span className="px-2 py-1 rounded border border-emerald-700 bg-emerald-950 text-emerald-400">NO PAN</span>
            <span className="text-slate-500">raw card number never returned, logged, or stored</span>
          </div>
        </div>
      )}
    </section>
  );
}

function PayoutsTable() {
  const { live } = useLive();
  const { data } = useFetch<StrPayoutBatch>(`/str/act2/payouts/${MONTH}${liveParam(live)}`);
  const records = data?.records ?? [];

  return (
    <section>
      <SectionLabel>Month-end crew payouts ({MONTH})</SectionLabel>
      {records.length === 0 ? (
        <EmptyState hint={`GET /str/act2/payouts/${MONTH}`} />
      ) : (
        <div className="border border-slate-800 rounded overflow-hidden">
          <table className="w-full font-mono text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-slate-800">
                <th className="px-3 py-2 text-left font-normal">Crew</th>
                <th className="px-3 py-2 text-left font-normal">Transfer</th>
                <th className="px-3 py-2 text-right font-normal">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {records.map((r) => (
                <tr key={r.crew_id}>
                  <td className="px-3 py-2 text-slate-200">{r.crew_name}</td>
                  <td className="px-3 py-2 text-slate-500">{r.transfer_id}</td>
                  <td className="px-3 py-2 text-right text-slate-200">{centsToUSD(r.amount_cents)}</td>
                </tr>
              ))}
              <tr className="bg-slate-900/60">
                <td className="px-3 py-2 text-slate-400" colSpan={2}>
                  Total
                </td>
                <td className="px-3 py-2 text-right text-amber-300 font-bold">{centsToUSD(data?.total_cents ?? 0)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function InvoicesBlock() {
  const { live } = useLive();
  const { data } = useFetch<StrInvoicesResponse>(`/str/act2/invoices/${MONTH}${liveParam(live)}`);
  const invoices = data?.invoices ?? [];

  return (
    <section>
      <SectionLabel>Owner UBP invoices ({MONTH})</SectionLabel>
      {invoices.length === 0 ? (
        <EmptyState hint={`GET /str/act2/invoices/${MONTH}`} />
      ) : (
        <div className="flex flex-col gap-3">
          {invoices.map((inv) => (
            <div key={inv.invoice_id} className="border border-slate-800 rounded p-4">
              <div className="flex items-baseline justify-between mb-2 font-mono text-xs">
                <span className="text-slate-300 font-bold">{inv.owner_id}</span>
                <span className="text-slate-500">{inv.invoice_id}</span>
              </div>
              {inv.line_items.map((ln) => (
                <div key={ln.property_id} className="flex items-baseline justify-between py-1 font-mono text-xs">
                  <span className="text-slate-400">{ln.property_name}</span>
                  <span className="text-slate-200">{centsToUSD(ln.fee_cents)}</span>
                </div>
              ))}
              <div className="flex items-baseline justify-between pt-2 mt-1 border-t border-slate-800 font-mono text-xs">
                <span className="text-slate-500">Total fee</span>
                <span className="text-amber-300 font-bold">{centsToUSD(inv.total_fee_cents)}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function PortfolioBlock() {
  const { live } = useLive();
  const { data } = useFetch<StrPortfolioSummary>(`/str/act2/portfolio${liveParam(live)}`);

  if (!data) {
    return (
      <section>
        <SectionLabel>Portfolio</SectionLabel>
        <EmptyState hint="GET /str/act2/portfolio" />
      </section>
    );
  }

  return (
    <section>
      <SectionLabel>Portfolio</SectionLabel>
      <div className="border border-slate-800 rounded p-4">
        <KV label="properties" value={data.property_count} />
        <KV label="owners" value={data.owner_count} />
        <KV label="monthly revenue" value={centsToUSD(data.total_monthly_revenue_cents)} accent />
        <KV label="property ids" value={data.property_ids.join(", ")} />
      </div>
    </section>
  );
}
