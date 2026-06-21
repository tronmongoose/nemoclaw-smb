import { Tabs, TabsList, TabsTrigger, TabsContent } from "nemoclaw-smb-ui";
import { Stat, KV, Rule, SectionLabel, StatusPill, Plate } from "nemoclaw-smb-ui";
import { ProvenanceBadge } from "nemoclaw-smb-ui";
import { LiveToggle } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Three-act fee reconciliation breakdown: Owner / Management / Platform */
export function ReconciliationTabs() {
  const demoProv = { mode: "demo" as const, model: "nvidia/nemotron-ultra", latency_ms: 0, source: "cached" as const };
  return (
    <Frame>
      <div className="flex items-center justify-between w-full" style={{ minWidth: 460 }}>
        <SectionLabel>May 2026 - Sweet Clementine</SectionLabel>
        <ProvenanceBadge prov={demoProv} />
      </div>
      <Tabs defaultValue="owner" style={{ width: 460 }}>
        <TabsList>
          <TabsTrigger value="owner">Owner</TabsTrigger>
          <TabsTrigger value="management">Management</TabsTrigger>
          <TabsTrigger value="platform">Platform</TabsTrigger>
        </TabsList>

        <TabsContent value="owner">
          <div className="flex gap-8 mt-4 mb-4">
            <Stat label="Gross" value="$6,240" />
            <Stat label="Net Payout" value="$4,912" sub="after all deductions" />
          </div>
          <Rule />
          <div className="mt-3">
            <KV label="Nights booked" value="14 / 31" />
            <KV label="Avg nightly rate" value="$245" />
            <KV label="Total deductions" value="$1,328" />
            <KV label="ACH transfer date" value="2026-06-01" />
          </div>
          <div className="mt-4">
            <StatusPill ok={true} label="Payout confirmed" />
          </div>
        </TabsContent>

        <TabsContent value="management">
          <div className="flex gap-8 mt-4 mb-4">
            <Stat label="Mgmt Fee (12%)" value="$748" />
            <Stat label="Turns" value="4" sub="this month" />
          </div>
          <Rule />
          <div className="mt-3">
            <SectionLabel>Crew Costs</SectionLabel>
            <KV label="Lead cleaner - Maria V." value="$440" />
            <KV label="Cleaning assist - Rosa T." value="$165" />
            <KV label="Landscaping - Juan R." value="$80" />
            <Rule />
            <KV label="Mgmt margin" value="$63" accent />
          </div>
        </TabsContent>

        <TabsContent value="platform">
          <div className="flex gap-8 mt-4 mb-4">
            <Stat label="Airbnb Fee" value="$624" sub="10% of gross" />
            <Stat label="Nights" value="14" />
          </div>
          <Rule />
          <div className="mt-3">
            <KV label="Host service fee" value="$499" />
            <KV label="Payment processing" value="$125" />
            <KV label="Occupancy tax collected" value="$374" />
            <KV label="Tax remitted by Airbnb" value="$374" />
          </div>
          <div className="mt-4">
            <Plate>
              <span className="font-mono text-xs text-muted-foreground">Airbnb remits CA TOT directly - no owner action needed</span>
            </Plate>
          </div>
        </TabsContent>
      </Tabs>
    </Frame>
  );
}

/** LIVE/DEMO toggle context preview alongside tabs */
export function LiveDemoToggleTabs() {
  const liveProv = { mode: "live" as const, model: "nvidia/nemotron-ultra", latency_ms: 38700, source: "nemotron" as const };
  return (
    <Frame>
      <div className="flex items-center gap-3">
        <LiveToggle />
        <ProvenanceBadge prov={liveProv} />
      </div>
      <Tabs defaultValue="summary" style={{ width: 420 }}>
        <TabsList>
          <TabsTrigger value="summary">Summary</TabsTrigger>
          <TabsTrigger value="audit">Audit</TabsTrigger>
        </TabsList>

        <TabsContent value="summary">
          <div className="mt-4 flex gap-8">
            <Stat label="YTD Revenue" value="$31,440" />
            <Stat label="YTD Net" value="$24,803" />
          </div>
          <div className="mt-4">
            <KV label="Occupancy YTD" value="61%" />
            <KV label="Avg daily rate" value="$247" />
            <KV label="Bookings closed" value="28" />
          </div>
        </TabsContent>

        <TabsContent value="audit">
          <div className="mt-4">
            <SectionLabel>Chain integrity</SectionLabel>
            <div className="flex flex-col gap-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-muted-foreground">Seq range</span>
                <span className="font-mono text-xs text-foreground">1001 - 1045</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-muted-foreground">Last verified</span>
                <span className="font-mono text-xs text-foreground">2026-06-01 03:14 UTC</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-muted-foreground">Status</span>
                <StatusPill ok={true} label="Valid" />
              </div>
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </Frame>
  );
}
