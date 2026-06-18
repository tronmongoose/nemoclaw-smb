/** Root layout: header + 4-panel command-center grid. */

import { Header } from "./components/Header";
import { PanelCard } from "./components/PanelCard";
import { GraphPanel } from "./components/GraphPanel";
import { InvoiceFeed } from "./components/InvoiceFeed";
import { ApprovalQueue } from "./components/ApprovalQueue";
import { SavingsPanel } from "./components/SavingsPanel";
import { usePoll } from "./hooks/usePoll";
import { AuditResponse } from "./types";

export function App() {
  const { data: audit } = usePoll<AuditResponse>("/audit?limit=100", 5_000);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Header audit={audit} />

      <main className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-4 p-4 auto-rows-[minmax(360px,auto)]">
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
      </main>
    </div>
  );
}
