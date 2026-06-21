/** Act II - The Management Company: checkout, payouts, invoices, portfolio org map. */

import { useState } from "react";
import { useFetch } from "../../hooks/useFetch";
import { apiPost } from "../../lib/api";
import { liveParam, useLive } from "./LiveContext";
import {
  StrCleanerCard,
  StrInvoicesResponse,
  StrPayoutBatch,
  StrPortfolioSummary,
} from "../../types";
import {
  centsToUSD,
  EmptyState,
  KV,
  Plate,
  Rule,
  SectionLabel,
  Stat,
  StatusPill,
} from "./shared";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const PROP = "prop-001";
const MONTH = "2026-06";
const CHECKOUT_DATE = "2026-06-15";

export function Act2View() {
  return (
    <div className="flex flex-col gap-8">
      <header className="flex flex-col gap-1">
        <h2 className="font-serif text-2xl font-semibold text-foreground">
          Act II - The Management Company
        </h2>
        <p className="font-mono text-xs text-muted-foreground">
          Every checkout triggers a governed payout.
        </p>
      </header>

      <CheckoutBlock />
      <Rule />
      <PayoutsTable />
      <Rule />
      <InvoicesBlock />
      <Rule />
      <PortfolioBlock />
    </div>
  );
}

function CheckoutBlock() {
  const { live } = useLive();
  const [card, setCard] = useState<StrCleanerCard | null>(null);
  const [busy, setBusy] = useState(false);

  async function issue() {
    setBusy(true);
    const res = await apiPost<StrCleanerCard>(
      `/str/act2/checkout${liveParam(live)}`,
      { property_id: PROP, checkout_date: CHECKOUT_DATE },
    );
    setCard(res);
    setBusy(false);
  }

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <SectionLabel>Stripe Issuing for Agents: single-use cleaner card</SectionLabel>
        <Button
          variant="outline"
          size="sm"
          disabled={busy}
          onClick={() => void issue()}
          className="font-mono text-xs"
        >
          {busy ? "Issuing..." : "Trigger checkout"}
        </Button>
      </div>

      {!card ? (
        <div className="rounded-[var(--radius)] border border-border p-4 font-mono text-xs text-muted-foreground">
          A least-privilege NHI (cleaner-subagent, scope card:issue:cleaning, 1h TTL) is issued
          and Baton grant-matched before any card is created.
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <StatusPill ok={true} label="C1 authorized" />
            <span className="font-mono text-xs text-muted-foreground">
              cleaner-subagent / card:issue:cleaning / 1h TTL
            </span>
          </div>

          <Plate>
            <KV label="card token" value={card.card_token} accent />
            <KV label="cap" value={centsToUSD(card.amount_cap_cents)} />
            <KV label="MCC allow-list" value={card.mcc_list.join(", ")} />
            <KV label="expires (EOD)" value={card.expiry_utc} />
            <KV label="backend" value={card.backend} />
            <div className="mt-3 flex items-center gap-3 border-t border-border pt-3">
              <StatusPill ok={true} label="NO PAN" />
              <span className="font-mono text-xs text-muted-foreground">
                raw card number never returned, logged, or stored
              </span>
            </div>
          </Plate>
        </div>
      )}
    </section>
  );
}

function PayoutsTable() {
  const { live } = useLive();
  const { data } = useFetch<StrPayoutBatch>(`/str/act2/payouts/${MONTH}${liveParam(live)}`);
  const records = data?.records ?? [];

  return (
    <section className="flex flex-col gap-3">
      <SectionLabel>Stripe Connect + Global Payouts ({MONTH})</SectionLabel>
      {records.length === 0 ? (
        <EmptyState hint={`GET /str/act2/payouts/${MONTH}`} />
      ) : (
        <>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="font-mono text-xs">Crew</TableHead>
                <TableHead className="font-mono text-xs">Transfer</TableHead>
                <TableHead className="font-mono text-xs">Status</TableHead>
                <TableHead className="font-mono text-xs text-right">Amount</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {records.map((r) => (
                <TableRow key={r.crew_id}>
                  <TableCell className="font-mono text-xs text-foreground">
                    {r.crew_name}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {r.transfer_id}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-muted-foreground">
                    {r.status}
                  </TableCell>
                  <TableCell className="font-mono text-xs text-right text-foreground">
                    {centsToUSD(r.amount_cents)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <div className="flex justify-between px-1 font-mono text-xs">
            <span className="text-muted-foreground">Total</span>
            <span className="font-semibold text-primary">{centsToUSD(data?.total_cents ?? 0)}</span>
          </div>
        </>
      )}
    </section>
  );
}

function InvoicesBlock() {
  const { live } = useLive();
  const { data } = useFetch<StrInvoicesResponse>(`/str/act2/invoices/${MONTH}${liveParam(live)}`);
  const invoices = data?.invoices ?? [];

  return (
    <section className="flex flex-col gap-3">
      <SectionLabel>Metronome UBP: owner invoices ({MONTH})</SectionLabel>
      {invoices.length === 0 ? (
        <EmptyState hint={`GET /str/act2/invoices/${MONTH}`} />
      ) : (
        <div className="flex flex-col gap-4">
          {invoices.map((inv) => (
            <div key={inv.invoice_id} className="flex flex-col gap-1">
              <div className="flex items-baseline justify-between">
                <span className="font-mono text-xs font-medium text-foreground">
                  {inv.owner_id}
                </span>
                <span className="font-mono text-[0.65rem] text-muted-foreground/60">
                  {inv.invoice_id}
                </span>
              </div>
              {inv.line_items.map((ln) => (
                <div
                  key={ln.property_id}
                  className="flex items-baseline justify-between py-0.5 font-mono text-xs"
                >
                  <span className="text-muted-foreground">{ln.property_name}</span>
                  <span className="text-foreground">{centsToUSD(ln.fee_cents)}</span>
                </div>
              ))}
              <div className="flex items-baseline justify-between border-t border-border pt-1.5 font-mono text-xs">
                <span className="text-muted-foreground">Total fee</span>
                <span className="font-semibold text-primary">
                  {centsToUSD(inv.total_fee_cents)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

function PortfolioBlock() {
  const { live } = useLive();
  const { data } = useFetch<StrPortfolioSummary>(`/str/act2/portfolio${liveParam(live)}`);

  if (!data) {
    return (
      <section className="flex flex-col gap-3">
        <SectionLabel>Portfolio org map</SectionLabel>
        <EmptyState hint="GET /str/act2/portfolio" />
      </section>
    );
  }

  const ownerEntries = Object.entries(data.properties_by_owner);

  return (
    <section className="flex flex-col gap-4">
      <SectionLabel>Portfolio org map</SectionLabel>

      <div className="flex gap-8">
        <Stat
          label="owners / properties"
          value={`${data.owner_count} / ${data.property_count}`}
        />
        <Stat
          label="monthly revenue"
          value={centsToUSD(data.total_monthly_revenue_cents)}
        />
      </div>

      {ownerEntries.length > 0 && (
        <div className="flex flex-col gap-2">
          <Rule label="owner map" />
          {ownerEntries.map(([ownerId, props]) => (
            <div key={ownerId} className="flex items-start gap-3 font-mono text-xs">
              <span className="shrink-0 text-muted-foreground">{ownerId}</span>
              <span className="text-foreground">{(props as string[]).join(", ")}</span>
            </div>
          ))}
        </div>
      )}

      {ownerEntries.length === 0 && (
        <div className="flex flex-col gap-1">
          <KV label="property ids" value={data.property_ids.join(", ")} />
          <KV label="owner ids" value={data.owner_ids.join(", ")} />
        </div>
      )}
    </section>
  );
}
