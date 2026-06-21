import {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableRow,
  TableHead,
  TableCell,
  TableCaption,
} from "nemoclaw-smb-ui";
import { SectionLabel, StatusPill, Rule } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Month-end crew payout table - May 2026 */
export function CrewPayoutsTable() {
  const rows = [
    { crew: "Maria Velasquez", role: "Lead cleaner", transferId: "TRF-0519-mv", status: true, amount: "$440.00" },
    { crew: "Rosa Torres", role: "Cleaning assist", transferId: "TRF-0522-rt", status: true, amount: "$165.00" },
    { crew: "Juan Reyes", role: "Landscaping", transferId: "TRF-0531-jr", status: false, amount: "$80.00" },
    { crew: "Supplies Co.", role: "Restock vendor", transferId: "TRF-0531-sc", status: false, amount: "$116.42" },
  ];

  return (
    <Frame>
      <SectionLabel>Crew Payouts - May 2026</SectionLabel>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Crew</TableHead>
            <TableHead>Role</TableHead>
            <TableHead className="font-mono">Transfer ID</TableHead>
            <TableHead>Status</TableHead>
            <TableHead className="text-right font-mono">Amount</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.transferId}>
              <TableCell className="font-medium">{r.crew}</TableCell>
              <TableCell className="text-muted-foreground text-xs">{r.role}</TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">{r.transferId}</TableCell>
              <TableCell>
                <StatusPill ok={r.status} label={r.status ? "Paid" : "Pending"} />
              </TableCell>
              <TableCell className="text-right font-mono font-semibold text-primary">{r.amount}</TableCell>
            </TableRow>
          ))}
        </TableBody>
        <TableFooter>
          <TableRow>
            <TableCell colSpan={4} className="font-mono text-xs text-muted-foreground">Total disbursed</TableCell>
            <TableCell className="text-right font-mono font-semibold text-foreground">$801.42</TableCell>
          </TableRow>
        </TableFooter>
        <TableCaption>Payouts via ACH. Pending items clear within 2 business days.</TableCaption>
      </Table>
    </Frame>
  );
}

/** Hash-chain audit table - last 5 events */
export function AuditChainTable() {
  const rows = [
    { seq: 1041, event: "payout:owner", amount: "$4,912.00", hash: "a3f9…c14e" },
    { seq: 1042, event: "fee:management", amount: "$748.80", hash: "b7d2…09fa" },
    { seq: 1043, event: "fee:platform", amount: "$624.00", hash: "c1e5…3b77" },
    { seq: 1044, event: "payout:crew:mv", amount: "$440.00", hash: "d4a8…82cc" },
    { seq: 1045, event: "restock:supplies", amount: "$116.42", hash: "e9b1…f501" },
  ];

  return (
    <Frame>
      <div className="flex items-center justify-between w-full" style={{ minWidth: 520 }}>
        <SectionLabel>Audit Chain - May 2026 Close</SectionLabel>
        <StatusPill ok={true} label="Chain valid" />
      </div>
      <Table style={{ minWidth: 520 }}>
        <TableHeader>
          <TableRow>
            <TableHead className="font-mono w-16">Seq</TableHead>
            <TableHead>Event</TableHead>
            <TableHead className="text-right font-mono">Amount</TableHead>
            <TableHead className="font-mono">Hash</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((r) => (
            <TableRow key={r.seq}>
              <TableCell className="font-mono text-xs text-muted-foreground">{r.seq}</TableCell>
              <TableCell className="font-mono text-xs">{r.event}</TableCell>
              <TableCell className="text-right font-mono text-sm text-primary">{r.amount}</TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">{r.hash}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <Rule label="Last verified 2026-06-01 03:14 UTC" />
    </Frame>
  );
}
