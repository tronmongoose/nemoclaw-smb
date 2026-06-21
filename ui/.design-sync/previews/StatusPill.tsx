import { StatusPill } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Hash-chain integrity verified after payout reconciliation */
export function StatusPillChainVerified() {
  return (
    <Frame>
      <StatusPill ok={true} label="CHAIN VERIFIED" />
    </Frame>
  );
}

/** Authorization confirmed for this reconciliation run */
export function StatusPillAuthorized() {
  return (
    <Frame>
      <StatusPill ok={true} label="C1 authorized" />
    </Frame>
  );
}

/** PAN absent - no payment card number in the export payload */
export function StatusPillNoPAN() {
  return (
    <Frame>
      <StatusPill ok={true} label="NO PAN" />
    </Frame>
  );
}

/** Chain fault detected - audit requires human review */
export function StatusPillChainFault() {
  return (
    <Frame>
      <StatusPill ok={false} label="CHAIN FAULT" />
    </Frame>
  );
}

/** Mixed row showing all pills together - triage context */
export function StatusPillTriage() {
  return (
    <Frame style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 } as React.CSSProperties}>
      <StatusPill ok={true} label="CHAIN VERIFIED" />
      <StatusPill ok={true} label="NO PAN" />
      <StatusPill ok={false} label="CHAIN FAULT" />
    </Frame>
  );
}
