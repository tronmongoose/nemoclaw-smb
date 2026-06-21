import { Badge } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** All four variants with realistic STR status labels. */
export function BadgeVariants() {
  return (
    <Frame>
      <p className="font-serif text-sm text-muted-foreground">Status labels</p>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", alignItems: "center" }}>
        <Badge variant="destructive">CRITICAL</Badge>
        <Badge variant="secondary">DEMO</Badge>
        <Badge variant="default">LIVE</Badge>
        <Badge variant="outline">Stripe</Badge>
      </div>
    </Frame>
  );
}

/** Payout + audit badges in context. */
export function BadgePayoutContext() {
  return (
    <Frame>
      <p className="font-serif text-sm text-muted-foreground">Payout reconciliation row</p>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <span className="font-mono text-xs text-foreground">May 2026 payout</span>
        <Badge variant="default">REAL</Badge>
        <Badge variant="outline">Hash verified</Badge>
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <span className="font-mono text-xs text-foreground">Apr 2026 payout</span>
        <Badge variant="secondary">DEMO</Badge>
        <Badge variant="outline">Unverified</Badge>
      </div>
    </Frame>
  );
}

/** Cleaner card status sweep. */
export function BadgeCleanerStatus() {
  return (
    <Frame>
      <p className="font-serif text-sm text-muted-foreground">Cleaner assignment badges</p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <Badge variant="default">Confirmed</Badge>
        <Badge variant="secondary">Standby</Badge>
        <Badge variant="destructive">No-show</Badge>
        <Badge variant="outline">Pending</Badge>
      </div>
    </Frame>
  );
}
