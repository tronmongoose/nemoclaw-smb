import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "nemoclaw-smb-ui";
import { KV, Rule, SectionLabel, Stat, StatusPill } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Single item open -- owner fee reconciliation breakdown */
export function OwnerFeeBreakdown() {
  return (
    <Frame>
      <SectionLabel>Sweet Clementine -- Fee Reconciliation</SectionLabel>
      <Accordion type="single" collapsible defaultValue="owner" className="w-80">
        <AccordionItem value="owner">
          <AccordionTrigger>Owner</AccordionTrigger>
          <AccordionContent>
            <KV label="Gross booking" value="$3,240.00" />
            <KV label="Platform fee (18%)" value="-$583.20" />
            <KV label="Cleaning pass-through" value="-$145.00" />
            <KV label="Net payout" value="$2,511.80" accent />
          </AccordionContent>
        </AccordionItem>
        <AccordionItem value="management">
          <AccordionTrigger>Management</AccordionTrigger>
          <AccordionContent>
            <KV label="PM fee (12%)" value="$388.80" />
            <KV label="Linen markup" value="$18.00" />
            <KV label="Total retained" value="$406.80" accent />
          </AccordionContent>
        </AccordionItem>
        <AccordionItem value="platform">
          <AccordionTrigger>Platform</AccordionTrigger>
          <AccordionContent>
            <KV label="Airbnb host fee" value="$97.20" />
            <KV label="Guest service fee" value="$486.00" />
            <KV label="TOT collected" value="$162.00" />
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </Frame>
  );
}

/** Cleaner cards + scheduling detail per section */
export function CleanerSchedule() {
  return (
    <Frame>
      <SectionLabel>Turnover Schedule -- June 21</SectionLabel>
      <Accordion type="single" collapsible defaultValue="cleaner-a" className="w-80">
        <AccordionItem value="cleaner-a">
          <AccordionTrigger>Rosa V. -- Unit 614</AccordionTrigger>
          <AccordionContent>
            <KV label="Checkout" value="11:00 AM" />
            <KV label="Checkin" value="3:00 PM" />
            <KV label="Window" value="4 hr" />
            <KV label="Rate" value="$145.00" accent />
            <Rule />
            <div className="pt-2">
              <StatusPill ok={true} label="Confirmed" />
            </div>
          </AccordionContent>
        </AccordionItem>
        <AccordionItem value="cleaner-b">
          <AccordionTrigger>Maria G. -- Unit 614 (deep clean)</AccordionTrigger>
          <AccordionContent>
            <KV label="Scheduled" value="July 1" />
            <KV label="Window" value="6 hr" />
            <KV label="Rate" value="$210.00" accent />
            <div className="pt-2">
              <StatusPill ok={false} label="Pending confirm" />
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </Frame>
  );
}

/** AEO audit results per category -- multi-item, one open */
export function AEOAuditAccordion() {
  return (
    <Frame>
      <SectionLabel>AEO Audit -- Sweet Clementine</SectionLabel>
      <Accordion type="single" collapsible defaultValue="listing" className="w-80">
        <AccordionItem value="listing">
          <AccordionTrigger>Listing Quality</AccordionTrigger>
          <AccordionContent>
            <KV label="Photo count" value="22 / 30 recommended" />
            <KV label="Title length" value="58 chars" />
            <KV label="Description words" value="312" />
            <KV label="AEO score" value="73 / 100" accent />
          </AccordionContent>
        </AccordionItem>
        <AccordionItem value="pricing">
          <AccordionTrigger>Pricing Health</AccordionTrigger>
          <AccordionContent>
            <KV label="ADR (30-day)" value="$228.00" accent />
            <KV label="Market ADR" value="$214.00" />
            <KV label="Occupancy" value="82%" />
            <KV label="RevPAR" value="$186.96" accent />
          </AccordionContent>
        </AccordionItem>
        <AccordionItem value="reviews">
          <AccordionTrigger>Review Signals</AccordionTrigger>
          <AccordionContent>
            <KV label="Overall rating" value="4.91" accent />
            <KV label="Cleanliness" value="4.95" />
            <KV label="Response rate" value="100%" />
            <KV label="Response time" value="within 1 hr" />
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </Frame>
  );
}

/** Hash-chain audit log sections -- single open */
export function HashChainAuditAccordion() {
  return (
    <Frame>
      <SectionLabel>Hash-Chain Audit Log</SectionLabel>
      <Accordion type="single" collapsible defaultValue="recent" className="w-96">
        <AccordionItem value="recent">
          <AccordionTrigger>Recent Entries (last 24 hr)</AccordionTrigger>
          <AccordionContent>
            <KV label="2026-06-21 07:14" value="payout-confirm #8821" />
            <KV label="2026-06-21 03:02" value="rate-update ADR $228" />
            <KV label="2026-06-20 22:45" value="cleaner-confirm Rosa V." />
            <Rule />
            <KV label="Chain head" value="a3f9d1c" accent />
            <div className="pt-2">
              <StatusPill ok={true} label="VALID" />
            </div>
          </AccordionContent>
        </AccordionItem>
        <AccordionItem value="integrity">
          <AccordionTrigger>Integrity Check</AccordionTrigger>
          <AccordionContent>
            <KV label="Entries verified" value="1,204" />
            <KV label="Last full scan" value="2026-06-21 06:30" />
            <KV label="Gaps detected" value="0" accent />
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </Frame>
  );
}
