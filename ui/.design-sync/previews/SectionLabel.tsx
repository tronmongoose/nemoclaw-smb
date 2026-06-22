import { SectionLabel } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

export function Ledger() {
  return (
    <Frame>
      <SectionLabel>Ledger</SectionLabel>
      <span className="font-mono text-xs text-foreground">Clementine St - June 2026</span>
      <span className="font-mono text-xs text-muted-foreground">3 payouts - 1 pending cleaner card</span>
    </Frame>
  );
}

export function AeoAudit() {
  return (
    <Frame>
      <SectionLabel>AEO audit</SectionLabel>
      <span className="font-mono text-xs text-foreground">prop-001 - last run 2026-06-16</span>
      <span className="font-mono text-xs text-muted-foreground">No anomalies flagged in rolling 90-day window</span>
    </Frame>
  );
}

export function NhiLabel() {
  return (
    <Frame>
      <SectionLabel>C1 NHI</SectionLabel>
      <span className="font-mono text-xs text-foreground">4 service identities - 0 overprivileged</span>
      <span className="font-mono text-xs text-muted-foreground">Last cert rotation: 2026-06-14</span>
    </Frame>
  );
}

export function CleanerCards() {
  return (
    <Frame>
      <SectionLabel>Cleaner cards</SectionLabel>
      <span className="font-mono text-xs text-foreground">Maria V. - checkout 6/18 - $85.00 approved</span>
      <span className="font-mono text-xs text-muted-foreground">Next turnover: 6/22 - card not yet issued</span>
    </Frame>
  );
}
