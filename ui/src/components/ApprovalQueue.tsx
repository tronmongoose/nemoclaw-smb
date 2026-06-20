/** Approval queue panel: cards with approve/deny actions. */

import { useState } from "react";
import { usePoll } from "../hooks/usePoll";
import { ApprovalItem } from "../types";
import { apiPost } from "../lib/api";
import { formatUSD, formatRelativeTime } from "../lib/format";

export function ApprovalQueue() {
  const { data, refetch } = usePoll<ApprovalItem[]>("/approvals/pending", 5_000);
  const pending = data ?? [];

  if (pending.length === 0) {
    return (
      <div className="flex items-center justify-center h-20 text-slate-600 font-mono text-sm">
        No approvals pending
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {pending.map((item) => (
        <ApprovalCard key={item.id} item={item} onDecide={refetch} />
      ))}
    </div>
  );
}

function ApprovalCard({
  item,
  onDecide,
}: {
  item: ApprovalItem;
  onDecide: () => void;
}) {
  const [deciding, setDeciding] = useState(false);

  async function decide(approved: boolean) {
    setDeciding(true);
    await apiPost(`/approvals/${item.id}/decide`, {
      approved,
      decided_by: "ceo",
    });
    setDeciding(false);
    onDecide();
  }

  return (
    <div className="border border-slate-700 rounded p-3 bg-slate-800/60 text-xs font-mono">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div>
          <span className="text-slate-300 font-bold">{item.vendor}</span>
          <span className="ml-2 text-amber-400 uppercase tracking-wide">
            {item.action}
          </span>
        </div>
        <span className="text-slate-200 font-bold whitespace-nowrap">
          {formatUSD(item.amount)}
        </span>
      </div>
      <div className="text-slate-500 mb-2 leading-relaxed">
        {item.context?.anomaly_reason ?? item.context?.policy_reason ?? ""}
      </div>
      <div className="flex items-center justify-between">
        <span className="text-slate-600">
          expires {formatRelativeTime(item.expires_at)}
        </span>
        <div className="flex gap-2">
          <button
            disabled={deciding}
            onClick={() => void decide(true)}
            className="px-3 py-1 rounded bg-emerald-800 hover:bg-emerald-700 text-emerald-200 border border-emerald-700 disabled:opacity-40"
          >
            Approve
          </button>
          <button
            disabled={deciding}
            onClick={() => void decide(false)}
            className="px-3 py-1 rounded bg-red-900 hover:bg-red-800 text-red-200 border border-red-700 disabled:opacity-40"
          >
            Deny
          </button>
        </div>
      </div>
    </div>
  );
}
