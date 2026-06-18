/** Top header: wordmark, audit-chain badge, orchestrator pill. */

import { AuditResponse } from "../types";

interface HeaderProps {
  audit: AuditResponse | null;
}

export function Header({ audit }: HeaderProps) {
  const chainOk = audit?.verify?.ok ?? null;
  const entryCount = audit?.count ?? 0;

  return (
    <header className="flex items-center justify-between px-6 py-3 border-b border-slate-800 bg-slate-900">
      <div className="flex items-center gap-4">
        <span className="text-xl font-bold tracking-tight text-cyan-400 font-mono">
          NemoClaw
        </span>
        <span className="text-slate-500 text-sm font-mono">—</span>
        <span className="text-slate-200 text-sm font-semibold tracking-wide uppercase">
          SMB Ops Agent
        </span>
      </div>

      <div className="flex items-center gap-3">
        <AuditBadge ok={chainOk} count={entryCount} />
        <OrchPill />
      </div>
    </header>
  );
}

function AuditBadge({ ok, count }: { ok: boolean | null; count: number }) {
  if (ok === null) {
    return (
      <span className="font-mono text-xs px-3 py-1 rounded border border-slate-700 text-slate-500">
        AUDIT CHAIN CHECKING…
      </span>
    );
  }
  if (ok) {
    return (
      <span className="font-mono text-xs px-3 py-1 rounded border border-emerald-700 bg-emerald-950 text-emerald-400">
        AUDIT CHAIN OK ({count} entries)
      </span>
    );
  }
  return (
    <span className="font-mono text-xs px-3 py-1 rounded border border-red-700 bg-red-950 text-red-400 animate-pulse">
      AUDIT CHAIN FAULT
    </span>
  );
}

function OrchPill() {
  return (
    <span className="font-mono text-xs px-2 py-1 rounded bg-slate-800 text-slate-400 border border-slate-700">
      Hermes orchestrator
    </span>
  );
}
