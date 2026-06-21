import { Progress } from "nemoclaw-smb-ui";
import { SectionLabel, Stat, Rule, KV, StatusPill } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** AEO score bar -- single metric with headline stat */
export function AEOScoreBar() {
  return (
    <Frame>
      <Stat label="AEO Score" value="73" sub="Sweet Clementine -- June 2026" />
      <div className="w-72">
        <Progress value={73} className="h-3" />
      </div>
      <p className="font-mono text-xs text-muted-foreground">
        Target 85 -- 12 pts gap. Add 8 photos and expand description.
      </p>
    </Frame>
  );
}

/** Multi-bar: occupancy, review health, listing completeness */
export function OccupancyHealthBars() {
  const bars = [
    { label: "Occupancy (June)", value: 82 },
    { label: "Review Health", value: 96 },
    { label: "Listing Completeness", value: 61 },
  ] as const;

  return (
    <Frame>
      <SectionLabel>Property Health -- Sweet Clementine</SectionLabel>
      <div className="flex w-80 flex-col gap-4">
        {bars.map(({ label, value }) => (
          <div key={label} className="flex flex-col gap-1.5">
            <div className="flex items-baseline justify-between font-mono text-xs">
              <span className="text-muted-foreground">{label}</span>
              <span className="text-primary">{value}%</span>
            </div>
            <Progress value={value} />
          </div>
        ))}
      </div>
    </Frame>
  );
}

/** Payout reconciliation progress -- how much of gross has cleared */
export function PayoutReconciliationProgress() {
  return (
    <Frame>
      <SectionLabel>Payout Reconciliation -- Q2 2026</SectionLabel>
      <div className="flex w-80 flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between font-mono text-xs">
            <span className="text-muted-foreground">Cleared</span>
            <span className="text-primary">$9,228 of $11,340</span>
          </div>
          <Progress value={81} />
        </div>
        <Rule />
        <KV label="Pending" value="$2,112.00" />
        <KV label="Expected clearance" value="June 28" />
        <StatusPill ok={true} label="On track" />
      </div>
    </Frame>
  );
}

/** Hash-chain scan progress (running) */
export function HashChainScanProgress() {
  return (
    <Frame>
      <SectionLabel>Hash-Chain Integrity Scan</SectionLabel>
      <div className="flex w-80 flex-col gap-3">
        <div className="flex flex-col gap-1.5">
          <div className="flex items-baseline justify-between font-mono text-xs">
            <span className="text-muted-foreground">Entries verified</span>
            <span className="text-primary">1,024 / 1,204</span>
          </div>
          <Progress value={85} />
        </div>
        <p className="font-mono text-xs text-muted-foreground">
          Scanning audit log -- approx 14 sec remaining
        </p>
        <StatusPill ok={true} label="No gaps detected" />
      </div>
    </Frame>
  );
}

/** Cleaner rating + response bars for vendor selection */
export function CleanerRatingBars() {
  const vendors = [
    { name: "Rosa V.", rating: 97, jobs: 42 },
    { name: "Maria G.", rating: 88, jobs: 17 },
  ];

  return (
    <Frame>
      <SectionLabel>Cleaner Ratings -- Unit 614</SectionLabel>
      <div className="flex w-80 flex-col gap-5">
        {vendors.map(({ name, rating, jobs }) => (
          <div key={name} className="flex flex-col gap-1.5">
            <div className="flex items-baseline justify-between font-mono text-xs">
              <span className="text-foreground">{name}</span>
              <span className="text-primary">{rating}/100</span>
            </div>
            <Progress value={rating} />
            <span className="font-mono text-[0.65rem] text-muted-foreground">
              {jobs} completed jobs
            </span>
          </div>
        ))}
      </div>
    </Frame>
  );
}
