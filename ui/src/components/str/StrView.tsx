/** STR three-act container: sub-nav + global LIVE/DEMO toggle + routed act views.
 *
 * Wraps the whole tree in LiveProvider so every act threads the toggle into its
 * API calls. Each act gets its own ErrorBoundary so one act's render fault does
 * not blank the others. Mounted by App.tsx alongside Ops and Tenant.
 */

import { useState } from "react";
import { PanelCard } from "../PanelCard";
import { ErrorBoundary } from "../ErrorBoundary";
import { LiveProvider } from "./LiveContext";
import { LiveToggle } from "./LiveToggle";
import { StrNav, StrTab } from "./StrNav";
import { Act1View } from "./Act1View";
import { Act2View } from "./Act2View";
import { Act3View } from "./Act3View";
import { AuditPanel } from "./AuditPanel";

const TITLES: Record<StrTab, string> = {
  owner: "Act I: Owner Fee Reconciliation",
  management: "Act II: Property Management",
  platform: "Act III: Platform Earn Server",
  audit: "Audit Chain",
};

export function StrView() {
  const [tab, setTab] = useState<StrTab>("owner");

  return (
    <LiveProvider>
      <div className="max-w-4xl mx-auto flex flex-col gap-4 py-2">
        <div className="flex items-center justify-between">
          <StrNav tab={tab} onChange={setTab} />
          <LiveToggle />
        </div>

        <PanelCard title={TITLES[tab]}>
          <ErrorBoundary label={TITLES[tab]}>
            {tab === "owner" && <Act1View />}
            {tab === "management" && <Act2View />}
            {tab === "platform" && <Act3View />}
            {tab === "audit" && <AuditPanel />}
          </ErrorBoundary>
        </PanelCard>
      </div>
    </LiveProvider>
  );
}
