import { Rule } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

export function BareHairline() {
  return (
    <Frame>
      <span className="font-mono text-xs text-muted-foreground">Owner fee reconciliation - May 2026</span>
      <Rule />
      <span className="font-mono text-xs text-muted-foreground">Gross payout: $3,840.00</span>
    </Frame>
  );
}

export function ReasoningTrace() {
  return (
    <Frame>
      <span className="font-mono text-xs text-muted-foreground">AEO audit - Sweet Clementine - prop-001</span>
      <Rule label="reasoning trace" />
      <span className="font-mono text-xs text-muted-foreground/70">
        Occupancy delta vs. prior 90 days: +4 nights. ADR held at $192. No payout gaps detected.
      </span>
    </Frame>
  );
}

export function HashChainSection() {
  return (
    <Frame>
      <span className="font-mono text-xs text-muted-foreground">Hash-chain audit log</span>
      <Rule label="verified block" />
      <span className="font-mono text-xs text-verified">sha256: a3f7c...d91b - 2026-06-16T07:14:02Z</span>
      <Rule />
      <span className="font-mono text-xs text-muted-foreground">sha256: 88e2a...c04d - 2026-06-15T07:09:58Z</span>
    </Frame>
  );
}
