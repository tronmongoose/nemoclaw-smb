/** Root: the STR experience is primary. Legacy Ops + Tenant demos are demoted
 *  behind a secondary surface, reachable from the STR footer. */

import { useState } from "react";
import { Header } from "./components/Header";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { PanelCard } from "./components/PanelCard";
import { GraphPanel } from "./components/GraphPanel";
import { InvoiceFeed } from "./components/InvoiceFeed";
import { ApprovalQueue } from "./components/ApprovalQueue";
import { SavingsPanel } from "./components/SavingsPanel";
import { TenantDashboard } from "./components/tenant/TenantDashboard";
import { OpsHeadlineBand } from "./components/OpsHeadlineBand";
import { StrView } from "./components/str/StrView";
import { usePoll } from "./hooks/usePoll";
import { AuditResponse } from "./types";
import { cn } from "./lib/utils";

export function App() {
  const [legacy, setLegacy] = useState(false);
  if (!legacy) return <StrView onLegacy={() => setLegacy(true)} />;
  return <LegacyApp onHome={() => setLegacy(false)} />;
}

type LegacyView = "ops" | "tenant";

function LegacyNav({
  view,
  onChange,
  onHome,
}: {
  view: LegacyView;
  onChange: (v: LegacyView) => void;
  onHome: () => void;
}) {
  const btn = (v: LegacyView, label: string) => (
    <button
      onClick={() => onChange(v)}
      className={cn(
        "rounded-[var(--radius)] border px-3 py-1 font-mono text-xs transition-colors",
        view === v
          ? "border-primary text-foreground"
          : "border-border text-muted-foreground hover:text-foreground",
      )}
    >
      {label}
    </button>
  );
  return (
    <div className="flex items-center gap-2">
      <button
        onClick={onHome}
        className="rounded-[var(--radius)] px-3 py-1 font-mono text-xs uppercase tracking-widest text-primary transition-colors hover:opacity-80"
      >
        Sweet Clementine
      </button>
      {btn("ops", "Ops")}
      {btn("tenant", "Tenant P&L")}
    </div>
  );
}

function LegacyApp({ onHome }: { onHome: () => void }) {
  const [view, setView] = useState<LegacyView>("ops");
  const { data: audit } = usePoll<AuditResponse>("/audit?limit=100", 5_000);

  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <Header audit={audit} navSlot={<LegacyNav view={view} onChange={setView} onHome={onHome} />} />

      <main className="flex-1 p-4">
        {view === "ops" && (
          <ErrorBoundary label="Ops Dashboard">
            <OpsHeadlineBand />
            <div className="grid grid-cols-1 gap-4 auto-rows-[minmax(360px,auto)] lg:grid-cols-2">
              <PanelCard title="Knowledge Graph" className="lg:row-span-2">
                <ErrorBoundary label="Knowledge Graph">
                  <GraphPanel />
                </ErrorBoundary>
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
          </ErrorBoundary>
        )}

        {view === "tenant" && (
          <ErrorBoundary label="Tenant P&L">
            <TenantDashboard />
          </ErrorBoundary>
        )}
      </main>
    </div>
  );
}
