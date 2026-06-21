import { Skeleton } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Loading state for a payout summary card. */
export function SkeletonPayoutCard() {
  return (
    <Frame>
      <p className="font-mono text-xs text-muted-foreground">Payout card loading</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, width: 280 }}>
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-3 w-56" />
        <Skeleton className="h-3 w-48" />
      </div>
    </Frame>
  );
}

/** Loading state for a cleaner roster row. */
export function SkeletonCleanerRow() {
  return (
    <Frame>
      <p className="font-mono text-xs text-muted-foreground">Cleaner roster loading</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, width: 320 }}>
        {[1, 2, 3].map((i) => (
          <div key={i} style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <Skeleton className="h-8 w-8 rounded-full" />
            <div style={{ display: "flex", flexDirection: "column", gap: 4, flex: 1 }}>
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-2 w-40" />
            </div>
            <Skeleton className="h-5 w-16" />
          </div>
        ))}
      </div>
    </Frame>
  );
}

/** Loading state for the AEO audit table header + rows. */
export function SkeletonAuditTable() {
  return (
    <Frame>
      <p className="font-mono text-xs text-muted-foreground">AEO audit table loading</p>
      <div style={{ display: "flex", flexDirection: "column", gap: 10, width: 360 }}>
        <div style={{ display: "flex", gap: 12 }}>
          <Skeleton className="h-3 w-24" />
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-3 w-16" />
        </div>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} style={{ display: "flex", gap: 12 }}>
            <Skeleton className="h-3 w-32" />
            <Skeleton className="h-3 w-16" />
            <Skeleton className="h-3 w-20" />
          </div>
        ))}
      </div>
    </Frame>
  );
}
