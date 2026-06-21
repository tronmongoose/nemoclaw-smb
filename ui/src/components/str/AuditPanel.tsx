/** Audit: STR-scoped hash-chain entries + a polled green/red verify badge.
 *
 * Polls /str/audit every 5s. Each entry shows its sequence, event/service,
 * amount, and a truncated entry hash so the chain is legible. The verify badge
 * reflects verify_chain over the whole demo chain (true tamper-evidence).
 * Fails soft to an empty state when the API is unreachable.
 */

import { usePoll } from "../../hooks/usePoll";
import { StrAuditEntry, StrAuditResponse } from "../../types";
import { useLive } from "./LiveContext";
import { centsToUSD, EmptyState, SectionLabel, StatusPill } from "./shared";

export function AuditPanel() {
  const { live } = useLive();
  const { data } = usePoll<StrAuditResponse>(`/str/audit?limit=50&live=${live ? "true" : "false"}`, 5_000);

  const entries = data?.entries ?? [];
  const verifyOk = data?.verify?.ok ?? null;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <SectionLabel>Hash chain ({data?.count ?? 0} STR entries)</SectionLabel>
        {verifyOk === null ? (
          <span className="font-mono text-xs px-2 py-1 rounded border border-slate-700 text-slate-500">VERIFYING...</span>
        ) : (
          <StatusPill ok={verifyOk} label={verifyOk ? "CHAIN VERIFIED" : "CHAIN FAULT"} />
        )}
      </div>

      {entries.length === 0 ? (
        <EmptyState hint="GET /str/audit" />
      ) : (
        <div className="border border-slate-800 rounded overflow-hidden">
          <table className="w-full font-mono text-xs">
            <thead>
              <tr className="text-slate-500 border-b border-slate-800">
                <th className="px-3 py-2 text-left font-normal">#</th>
                <th className="px-3 py-2 text-left font-normal">Event</th>
                <th className="px-3 py-2 text-right font-normal">Amount</th>
                <th className="px-3 py-2 text-left font-normal">Entry hash</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {entries.map((e, i) => (
                <AuditRow key={`${e.entry_hash ?? i}`} entry={e} />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {data?.verify?.message && (
        <p className="font-mono text-xs text-slate-600">{data.verify.message}</p>
      )}
    </div>
  );
}

function AuditRow({ entry }: { entry: StrAuditEntry }) {
  const label = entry.event === "mpp_earn" ? `earn / ${entry.service ?? ""}` : entry.action ?? entry.event ?? "entry";
  const amount = typeof entry.amount_cents === "number" ? centsToUSD(entry.amount_cents) : "";
  const hash = entry.entry_hash ?? "";
  return (
    <tr>
      <td className="px-3 py-2 text-slate-500">{entry.seq ?? ""}</td>
      <td className="px-3 py-2 text-slate-200">{label}</td>
      <td className="px-3 py-2 text-right text-slate-300">{amount}</td>
      <td className="px-3 py-2 text-slate-500">{hash ? `${hash.slice(0, 16)}...` : ""}</td>
    </tr>
  );
}
