import { EmptyState } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start", width: "100%" }}
  >
    {children}
  </div>
);

export function WithHint() {
  return (
    <Frame>
      <EmptyState hint="GET /str/act1/prop-001/2026-06" />
    </Frame>
  );
}

export function Bare() {
  return (
    <Frame>
      <EmptyState />
    </Frame>
  );
}

export function PayoutsEmpty() {
  return (
    <Frame>
      <EmptyState hint="GET /str/act1/prop-001/payouts?month=2026-06" />
    </Frame>
  );
}
