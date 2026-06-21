import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from "nemoclaw-smb-ui";
import { Button } from "nemoclaw-smb-ui";
import { KV, Rule, SectionLabel, StatusPill } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Payout approval confirmation dialog -- rendered open */
export function PayoutApprovalDialog() {
  return (
    <Frame>
      <SectionLabel>Dialog -- Payout Approval</SectionLabel>
      <Dialog open>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-serif">Confirm Payout</DialogTitle>
            <DialogDescription>
              Release net payout for Sweet Clementine checkout June 21.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-0">
            <KV label="Gross booking" value="$3,240.00" />
            <KV label="Platform fee" value="-$583.20" />
            <KV label="Cleaning" value="-$145.00" />
            <Rule />
            <KV label="Net payout" value="$2,511.80" accent />
          </div>
          <p className="font-mono text-xs text-muted-foreground">
            Funds clear within 2 business days. Action is logged to the hash chain.
          </p>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" size="sm">Cancel</Button>
            </DialogClose>
            <Button size="sm">Release $2,511.80</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Frame>
  );
}

/** AEO flag review dialog -- rendered open */
export function AEOFlagDialog() {
  return (
    <Frame>
      <SectionLabel>Dialog -- AEO Flag Review</SectionLabel>
      <Dialog open>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-serif">AEO Flag: Listing Quality</DialogTitle>
            <DialogDescription>
              Nemotron Ultra flagged 3 issues on Sweet Clementine during the June 21 audit.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <div className="flex items-start gap-2 font-mono text-xs">
              <span className="text-destructive">01</span>
              <span>Photo count below 25 -- add at least 8 photos to reach target range.</span>
            </div>
            <div className="flex items-start gap-2 font-mono text-xs">
              <span className="text-destructive">02</span>
              <span>Description under 400 words -- expand with amenity details and neighborhood context.</span>
            </div>
            <div className="flex items-start gap-2 font-mono text-xs">
              <span className="text-muted-foreground">03</span>
              <span className="text-muted-foreground">Title within acceptable range -- no action required.</span>
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" size="sm">Dismiss</Button>
            </DialogClose>
            <Button size="sm">Open Listing Editor</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Frame>
  );
}

/** Cleaner assignment confirmation dialog -- rendered open */
export function CleanerAssignDialog() {
  return (
    <Frame>
      <SectionLabel>Dialog -- Cleaner Assignment</SectionLabel>
      <Dialog open>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="font-serif">Assign Turnover</DialogTitle>
            <DialogDescription>
              Confirm Rosa V. for the June 21 checkout at unit 614 Clementine.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-0">
            <KV label="Cleaner" value="Rosa V." accent />
            <KV label="Window" value="11:00 AM - 3:00 PM" />
            <KV label="Rate" value="$145.00" />
            <KV label="Supplies included" value="Yes" />
          </div>
          <div>
            <StatusPill ok={true} label="Cleaner available" />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" size="sm">Cancel</Button>
            </DialogClose>
            <Button size="sm">Confirm Assignment</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Frame>
  );
}

/** Hash-chain integrity alert dialog -- rendered open */
export function HashChainAlertDialog() {
  return (
    <Frame>
      <SectionLabel>Dialog -- Audit Alert</SectionLabel>
      <Dialog open>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="font-serif text-destructive">
              Audit Chain Gap Detected
            </DialogTitle>
            <DialogDescription>
              A gap was found between entries 1,019 and 1,021. Entry 1,020 is missing from the local log.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-0">
            <KV label="Chain head (expected)" value="a3f9d1c" />
            <KV label="Chain head (actual)" value="b72e44f" />
            <KV label="Detected at" value="2026-06-21 06:32" />
          </div>
          <p className="font-mono text-xs text-muted-foreground">
            The remote ledger is unaffected. Re-sync from remote to restore local integrity.
          </p>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline" size="sm">Dismiss</Button>
            </DialogClose>
            <Button variant="destructive" size="sm">Re-sync from Remote</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Frame>
  );
}
