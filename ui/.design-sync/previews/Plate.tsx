import { Plate } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Signed payment receipt - standard Plate surface */
export function PlateSignedReceipt() {
  return (
    <Frame>
      <Plate>
        <div className="flex flex-col gap-0">
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">stay</span>
            <span className="text-foreground">Jun 14 - Jun 17 (3 nights)</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">guest</span>
            <span className="text-foreground">Ramirez, M.</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">gross</span>
            <span className="text-foreground">$1,035.00</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">platform fee</span>
            <span className="text-foreground">$207.00 (20%)</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">net payout</span>
            <span className="font-semibold text-primary">$828.00</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">hash</span>
            <span className="text-foreground break-all">a3f7c2d...b91e</span>
          </div>
        </div>
      </Plate>
    </Frame>
  );
}

/** Single-use card summary for cleaner disbursement */
export function PlateCleanerCard() {
  return (
    <Frame>
      <Plate>
        <div className="flex flex-col gap-0">
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">cleaner</span>
            <span className="text-foreground">Maria T.</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">turnover date</span>
            <span className="text-foreground">Jun 17, 2026</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">card limit</span>
            <span className="text-foreground">$120.00</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">card last4</span>
            <span className="text-foreground">••••  4872</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">status</span>
            <span className="font-semibold text-primary">issued</span>
          </div>
        </div>
      </Plate>
    </Frame>
  );
}

/** Critical flag Plate - overcharge breach requiring owner action */
export function PlateCriticalOvercharge() {
  return (
    <Frame>
      <Plate className="border-destructive">
        <div className="mb-2 font-mono text-xs font-semibold uppercase tracking-widest text-destructive">
          CRITICAL - Contract Breach
        </div>
        <div className="flex flex-col gap-0">
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">property</span>
            <span className="text-foreground">Sweet Clementine - Oceanside</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">contracted fee</span>
            <span className="text-foreground">20.0%</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">charged fee</span>
            <span className="font-semibold text-destructive">22.0%</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">overcharge</span>
            <span className="font-semibold text-destructive">$84.00 / mo</span>
          </div>
          <div className="flex justify-between py-1.5 font-mono text-xs">
            <span className="text-muted-foreground">detected</span>
            <span className="text-foreground">Jun 16, 2026</span>
          </div>
        </div>
      </Plate>
    </Frame>
  );
}
