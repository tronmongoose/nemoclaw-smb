/** Invoice feed panel: newest-first table; anomaly rows get a badge. */

import { useFetch } from "../hooks/useFetch";
import { Invoice, AnomalyRecord } from "../types";
import { formatUSD, formatPct } from "../lib/format";

export function InvoiceFeed() {
  const { data: invoices, loading: invLoading } = useFetch<Invoice[]>("/invoices?limit=50");
  const { data: anomalies } = useFetch<AnomalyRecord[]>("/invoices/anomalies?threshold=2.0");

  const anomalyMap = new Map<string, AnomalyRecord>();
  if (anomalies) {
    for (const a of anomalies) {
      if (a.is_anomaly) anomalyMap.set(a.vendor, a);
    }
  }

  const sorted = invoices
    ? [...invoices].sort((a, b) => b.date.localeCompare(a.date))
    : [];

  if (invLoading && !invoices) {
    return <div className="text-slate-600 font-mono text-sm">Loading…</div>;
  }

  if (!invoices || invoices.length === 0) {
    return (
      <div className="text-slate-600 font-mono text-sm">No invoices available</div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono border-separate border-spacing-0">
        <thead>
          <tr className="text-slate-500 uppercase tracking-widest">
            <th className="text-left py-1 pr-3">Date</th>
            <th className="text-left py-1 pr-3">Vendor</th>
            <th className="text-left py-1 pr-3">Description</th>
            <th className="text-left py-1 pr-3">Category</th>
            <th className="text-right py-1">Amount</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((inv) => {
            const anom = anomalyMap.get(inv.vendor);
            return (
              <tr
                key={inv.invoice_id}
                className={`border-t border-slate-800 ${anom ? "bg-red-950/30" : "hover:bg-slate-800/40"}`}
              >
                <td className="py-1.5 pr-3 text-slate-500 whitespace-nowrap">
                  {inv.date.slice(0, 10)}
                </td>
                <td className="py-1.5 pr-3 text-slate-200 whitespace-nowrap">
                  <span>{inv.vendor}</span>
                  {anom && (
                    <AnomalyBadge pct={anom.pct_change} reason={anom.reason} />
                  )}
                </td>
                <td className="py-1.5 pr-3 text-slate-400 max-w-[180px] truncate">
                  {inv.description}
                </td>
                <td className="py-1.5 pr-3 text-slate-500">{inv.category}</td>
                <td className="py-1.5 text-right text-slate-200 whitespace-nowrap">
                  {formatUSD(inv.amount)}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function AnomalyBadge({ pct, reason }: { pct: number; reason: string }) {
  return (
    <span
      className="ml-2 inline-block px-1.5 py-0.5 rounded text-[10px] bg-red-900 text-red-300 border border-red-700 cursor-help"
      title={reason}
    >
      ANOMALY {formatPct(pct)}
    </span>
  );
}
