import { Separator } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Horizontal separator dividing payout summary sections. */
export function SeparatorHorizontal() {
  return (
    <Frame>
      <div style={{ display: "flex", flexDirection: "column", gap: 12, width: 320 }}>
        <div>
          <p className="font-serif text-sm text-foreground">Sweet Clementine</p>
          <p className="font-mono text-xs text-muted-foreground">614 Clementine St, Oceanside CA</p>
        </div>
        <Separator />
        <div>
          <p className="font-mono text-xs text-muted-foreground">Owner net - May 2026</p>
          <p className="font-mono text-lg text-primary">$3,241.00</p>
        </div>
        <Separator />
        <div>
          <p className="font-mono text-xs text-muted-foreground">Platform fee (Airbnb)</p>
          <p className="font-mono text-sm text-foreground">$187.50</p>
        </div>
      </div>
    </Frame>
  );
}

/** Vertical separator between inline metadata items. */
export function SeparatorVertical() {
  return (
    <Frame>
      <p className="font-mono text-xs text-muted-foreground">Hash-chain audit metadata</p>
      <div style={{ display: "flex", alignItems: "center", gap: 12, height: 20 }}>
        <span className="font-mono text-xs text-foreground">Chain valid</span>
        <Separator orientation="vertical" />
        <span className="font-mono text-xs text-foreground">47 entries</span>
        <Separator orientation="vertical" />
        <span className="font-mono text-xs text-muted-foreground">Last: 2026-06-21 06:30</span>
      </div>
    </Frame>
  );
}

/** Separator as section rule inside a cleaner fee reconciliation block. */
export function SeparatorFeeReconciliation() {
  return (
    <Frame>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, width: 300 }}>
        <p className="font-serif text-sm text-foreground">Fee reconciliation - June 2026</p>
        <Separator />
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span className="font-mono text-xs text-muted-foreground">Cleaner (Maria R.)</span>
          <span className="font-mono text-xs text-foreground">$120.00</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span className="font-mono text-xs text-muted-foreground">Supplies reimbursement</span>
          <span className="font-mono text-xs text-foreground">$18.40</span>
        </div>
        <Separator />
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span className="font-mono text-xs text-foreground">Total deducted</span>
          <span className="font-mono text-xs text-primary">$138.40</span>
        </div>
      </div>
    </Frame>
  );
}
