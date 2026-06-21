import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "nemoclaw-smb-ui";
import { Stat, KV, Rule, SectionLabel, StatusPill, Plate } from "nemoclaw-smb-ui";
import { ProvenanceBadge } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Owner reconciliation summary card - May 2026 close */
export function OwnerReconciliationCard() {
  const prov = { mode: "demo" as const, model: "nvidia/nemotron-ultra", latency_ms: 0, source: "cached" as const };
  return (
    <Frame>
      <Card style={{ width: 380 }}>
        <CardHeader>
          <div className="flex items-start justify-between gap-2">
            <div>
              <CardTitle className="font-serif text-lg">Sweet Clementine</CardTitle>
              <CardDescription className="font-mono text-xs mt-1">614 Clementine St, Oceanside CA - May 2026</CardDescription>
            </div>
            <StatusPill ok={true} label="Reconciled" />
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex gap-8 mb-4">
            <Stat label="Gross Revenue" value="$6,240" />
            <Stat label="Net to Owner" value="$4,912" sub="after mgmt + fees" />
          </div>
          <Rule />
          <div className="mt-3">
            <SectionLabel>Fee Breakdown</SectionLabel>
            <KV label="Platform (Airbnb)" value="$624" />
            <KV label="Management (12%)" value="$748" />
            <KV label="Cleaning (4 turns)" value="$440" />
            <KV label="Supplies restocked" value="$116" />
            <Rule />
            <KV label="Owner payout" value="$4,912" accent />
          </div>
        </CardContent>
        <CardFooter className="justify-between">
          <span className="font-mono text-xs text-muted-foreground">Closed 2026-05-31</span>
          <ProvenanceBadge prov={prov} />
        </CardFooter>
      </Card>
    </Frame>
  );
}

/** Single-use card: one reservation summary */
export function ReservationSummaryCard() {
  return (
    <Frame>
      <Card style={{ width: 340 }}>
        <CardHeader>
          <CardTitle className="font-serif text-base">Res #CLM-2026-0519</CardTitle>
          <CardDescription className="font-mono text-xs mt-1">May 19-24 - 5 nights - 4 guests</CardDescription>
        </CardHeader>
        <CardContent>
          <Plate>
            <KV label="Nightly rate" value="$245" />
            <KV label="Cleaning fee" value="$110" />
            <KV label="Airbnb service" value="$82" />
            <KV label="Guest total" value="$1,307" accent />
          </Plate>
          <div className="mt-4 flex items-center gap-2">
            <StatusPill ok={true} label="Paid out" />
            <span className="font-mono text-xs text-muted-foreground">ACH 2026-05-26</span>
          </div>
        </CardContent>
      </Card>
    </Frame>
  );
}

/** AEO audit card - action items surface here */
export function AeoAuditCard() {
  const prov = { mode: "live" as const, model: "nvidia/nemotron-ultra", latency_ms: 41200, source: "nemotron" as const };
  return (
    <Frame>
      <Card style={{ width: 400 }}>
        <CardHeader>
          <CardTitle className="font-serif text-base">AEO Audit - June 2026</CardTitle>
          <CardDescription className="font-mono text-xs mt-1">Answer Engine Optimization - listing health</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-6 mb-4">
            <Stat label="Score" value="84" sub="/ 100" />
            <Stat label="Flags" value="3" sub="action needed" />
          </div>
          <Rule label="Findings" />
          <div className="mt-3 flex flex-col gap-2">
            <Plate>
              <span className="font-mono text-xs text-destructive">Missing: check-in photo guide (affects search rank)</span>
            </Plate>
            <Plate>
              <span className="font-mono text-xs text-destructive">Title below 50 chars - expand for keyword coverage</span>
            </Plate>
            <Plate>
              <span className="font-mono text-xs text-muted-foreground">Amenity list matches 91% of comparables in ZIP 92054</span>
            </Plate>
          </div>
        </CardContent>
        <CardFooter className="justify-end">
          <ProvenanceBadge prov={prov} />
        </CardFooter>
      </Card>
    </Frame>
  );
}

/** Compact card variant: cleaner dispatch summary */
export function CleanerDispatchCard() {
  return (
    <Frame style={{ flexDirection: "row", flexWrap: "wrap" }}>
      {[
        { name: "Maria V.", date: "Jun 22", type: "Full turn", status: true, amount: "$110" },
        { name: "Rosa T.", date: "Jun 28", type: "Quick reset", status: false, amount: "$65" },
      ].map((c) => (
        <Card key={c.name} style={{ width: 220 }}>
          <CardHeader className="pb-2">
            <CardTitle className="font-serif text-sm">{c.name}</CardTitle>
            <CardDescription className="font-mono text-xs">{c.date} - {c.type}</CardDescription>
          </CardHeader>
          <CardContent className="pt-0">
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm font-semibold text-primary">{c.amount}</span>
              <StatusPill ok={c.status} label={c.status ? "Confirmed" : "Pending"} />
            </div>
          </CardContent>
        </Card>
      ))}
    </Frame>
  );
}
