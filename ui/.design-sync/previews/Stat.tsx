import { Stat } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Overcharge amount surfaced from fee reconciliation */
export function StatOvercharge() {
  return (
    <Frame>
      <Stat
        label="Monthly Overcharge"
        value="$84"
        sub="22% charged vs 20% contract on $4,200 gross"
      />
    </Frame>
  );
}

/** AEO audit score for Sweet Clementine */
export function StatAEOScore() {
  return (
    <Frame>
      <Stat
        label="AEO Audit Score"
        value="51/100"
        sub="Below threshold - listing optimization required"
      />
    </Frame>
  );
}

/** Recommended nightly rate from Nemotron pricing run */
export function StatRecommendedRate() {
  return (
    <Frame>
      <Stat
        label="Recommended Nightly Rate"
        value="$345"
        sub="Nemotron Ultra - peak-season Memorial Day window"
      />
    </Frame>
  );
}

/** Payout pending for current month */
export function StatPendingPayout() {
  return (
    <Frame>
      <Stat
        label="Pending Payout"
        value="$2,940"
        sub="3 stays closed - ACH initiated Jun 18"
      />
    </Frame>
  );
}
