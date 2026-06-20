/** Root layout: nav toggle between ops dashboard and tenant P&L view. */

import { useState } from "react";
import { Header } from "./components/Header";
import { PanelCard } from "./components/PanelCard";
import { GraphPanel } from "./components/GraphPanel";
import { InvoiceFeed } from "./components/InvoiceFeed";
import { ApprovalQueue } from "./components/ApprovalQueue";
import { SavingsPanel } from "./components/SavingsPanel";
import { TenantDashboard } from "./components/tenant/TenantDashboard";
import { usePoll } from "./hooks/usePoll";
import { AuditResponse } from "./types";

type View = "ops" | "tenant";

function NavToggle({ view, onChange }: { view: View; onChange: (v: View) => void }) {
  const btn = (v: View, label: string) => (
    <button
      onClick={() => onChange(v)}
      className={[
        "px-3 py-1 text-xs font-mono rounded border transition-colors",
        view === v
          ? "bg-cyan-900 border-cyan-700 text-cyan-300"
          : "bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200",
      ].join(" ")}
    >
      {label}
    </button>
  );

  return (
    <div className="flex items-center gap-2">
      {btn("ops", "Ops Dashboard")}
      {btn("tenant", "Tenant P&L")}
    </div>
  );
}

export function App() {
  const [view, setView] = useState<View>("ops");
  const { data: audit } = usePoll<AuditResponse>("/audit?limit=100", 5_000);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header audit={audit} navSlot={<NavToggle view={view} onChange={setView} />} />

      <main className="flex-1 p-4">
        {view === "ops" ? (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 auto-rows-[minmax(360px,auto)]">
            <PanelCard title="Knowledge Graph" className="lg:row-span-2">
              <GraphPanel />
            </PanelCard>

            <PanelCard title="Invoice Feed" className="overflow-hidden">
              <InvoiceFeed />
            </PanelCard>

            <PanelCard title="Approval Queue">
              <ApprovalQueue />
            </PanelCard>

            <PanelCard title="Savings Intelligence" className="lg:col-span-2">
              <SavingsPanel />
            </PanelCard>
          </div>
        ) : (
          <TenantDashboard />
        )}
      </main>
    </div>
  );
}
