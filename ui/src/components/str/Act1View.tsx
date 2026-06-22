/** Act I - The Owner: management-fee reconciliation for Sweet Clementine. */

import { useState } from "react";
import { useFetch } from "../../hooks/useFetch";
import { apiPost } from "../../lib/api";
import { StrReconciliationReport } from "../../types";
import { useLive, liveParam } from "./LiveContext";
import { ProvenanceBadge } from "./ProvenanceBadge";
import {
  centsToUSD,
  ElapsedCounter,
  EmptyState,
  Rule,
  SectionLabel,
  KV,
  Stat,
  StatusPill,
  Plate,
} from "./shared";
import { Skeleton } from "@/components/ui/skeleton";
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

export function Act1View() {
  const { live } = useLive();
  const path = `/str/act1/${PROP}/${MONTH}${liveParam(live)}`;
  const { data, loading, refetch } = useFetch<StrReconciliationReport>(path);

  if (loading) {
    return (
      <div className="flex flex-col gap-6 p-2">
        {live && (
          <div className="flex items-center gap-3 rounded-[var(--radius)] border border-primary bg-[hsl(var(--primary)/0.06)] px-4 py-3">
            <ElapsedCounter running label="Reconciling live, calling Nemotron Ultra" />
          </div>
        )}
        <Skeleton className="h-28 w-full" />
        <Skeleton className="h-40 w-full" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }
  if (!data || !data.summary) {
    return <EmptyState hint="GET /str/act1/prop-001/2026-06" />;
  }

  return (
    <article className="flex flex-col gap-8">
      <header className="flex flex-col gap-2">
        <h2 className="font-serif text-2xl font-semibold text-foreground">
          Act I - The Owner
        </h2>
        <p className="font-mono text-xs text-muted-foreground">
          Governed fee reconciliation for Sweet Clementine, {data.month}.
        </p>
      </header>

      <HeroStat report={data} />

      <Rule />

      <LedgerSection report={data} />

      <Rule />

      <AnomalySection report={data} />

      <Rule />

      <GovernanceSection report={data} />

      <Rule />

      <PaymentSection report={data} onApprove={refetch} live={live} />

      <Rule />

      <AuditSection report={data} />
    </article>
  );
}

function HeroStat({ report }: { report: StrReconciliationReport }) {
  const a = report.anomaly;
  const s = report.summary;
  const subLine = `charged ${(s.charged_pct * 100).toFixed(1)}% vs contract ${(s.contract_pct * 100).toFixed(1)}% on ${centsToUSD(s.revenue_cents)} revenue`;
  return (
    <section>
      <p className="font-serif text-base text-muted-foreground leading-relaxed mb-6">
        <span className="drop-cap">T</span>he reconciliation agent caught a
        management-fee overcharge this month. The amount below is owed back to
        the owner.
      </p>
      <Stat
        label="Management-fee overcharge"
        value={centsToUSD(a.overcharge_cents)}
        sub={subLine}
      />
    </section>
  );
}

function LedgerSection({ report }: { report: StrReconciliationReport }) {
  const s = report.summary;
  const li = s.line_items ?? {};
  return (
    <section>
      <SectionLabel>Ledger</SectionLabel>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="font-mono text-[0.7rem] uppercase tracking-[0.15em]">
              Line
            </TableHead>
            <TableHead className="text-right font-mono text-[0.7rem] uppercase tracking-[0.15em]">
              Amount
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow>
            <TableCell className="text-muted-foreground font-mono text-xs">
              Gross revenue
            </TableCell>
            <TableCell className="text-right font-mono text-xs text-foreground">
              {centsToUSD(s.revenue_cents)}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell className="text-muted-foreground font-mono text-xs">
              Contracted fee ({(s.contract_pct * 100).toFixed(1)}%)
            </TableCell>
            <TableCell className="text-right font-mono text-xs text-foreground">
              {centsToUSD(li.contracted_fee_cents ?? 0)}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell className="text-muted-foreground font-mono text-xs">
              Charged fee ({(s.charged_pct * 100).toFixed(1)}%)
            </TableCell>
            <TableCell className="text-right font-mono text-xs text-foreground">
              {centsToUSD(li.charged_fee_cents ?? 0)}
            </TableCell>
          </TableRow>
          <TableRow>
            <TableCell className="font-mono text-xs font-semibold text-primary">
              Fee delta
            </TableCell>
            <TableCell className="text-right font-mono text-xs font-semibold text-primary">
              {centsToUSD(li.fee_delta_cents ?? 0)}
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </section>
  );
}

function AnomalySection({ report }: { report: StrReconciliationReport }) {
  const a = report.anomaly;
  if (!a) return null;
  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <SectionLabel>Anomaly detection</SectionLabel>
        <ProvenanceBadge prov={a.reasoning_provenance} />
      </div>
      <div className="flex flex-col gap-3">
        <div className="flex items-baseline justify-between">
          <span className="font-mono text-xs font-semibold uppercase tracking-wider text-primary">
            {a.is_anomaly ? "Overcharge caught" : "No anomaly"}
          </span>
          <span className="font-mono text-xs text-muted-foreground">
            model: {a.model_used}
          </span>
        </div>
        <p className="font-serif text-sm text-foreground leading-relaxed">
          {a.reason}
        </p>
        <Rule label="reasoning trace" />
        <p className="font-mono text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">
          {a.reasoning_trace}
        </p>
      </div>
    </section>
  );
}

function GovernanceSection({ report }: { report: StrReconciliationReport }) {
  const isBaton = report.nhi_id.includes("str-owner-agent");
  const source = isBaton ? "baton-carryall" : "synthetic";
  return (
    <section>
      <SectionLabel>C1 NHI</SectionLabel>
      <Plate>
        <KV label="nhi_id" value={report.nhi_id} />
        <KV label="scopes" value="ledger:read, payment:propose" />
        <KV
          label="authorize decision"
          value={isBaton ? "ALLOW (baton-carryall)" : "ALLOW (synthetic)"}
          accent
        />
        <KV label="decision source" value={source} />
      </Plate>
    </section>
  );
}

function PaymentSection({
  report,
  onApprove,
  live,
}: {
  report: StrReconciliationReport;
  onApprove: () => void;
  live: boolean;
}) {
  const p = report.payment;
  const [deciding, setDeciding] = useState(false);

  async function approve() {
    if (!p?.request_id) return;
    setDeciding(true);
    await apiPost(`/approvals/${p.request_id}/decide`, {
      approved: true,
      decided_by: "owner",
    });
    setDeciding(false);
    onApprove();
  }

  if (!p) {
    return (
      <section>
        <SectionLabel>Correction payment</SectionLabel>
        <p className="font-mono text-xs text-muted-foreground">
          No payment proposed (no anomaly to correct).
        </p>
      </section>
    );
  }

  if (p.held_for_approval) {
    return (
      <section>
        <SectionLabel>Correction payment</SectionLabel>
        <Plate className="border-primary bg-[hsl(var(--primary)/0.06)]">
          <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-wider text-primary">
            REQUIRE_APPROVAL hold
          </p>
          <p className="mb-4 font-mono text-xs text-muted-foreground">
            Correction of {centsToUSD(p.amount_cents)} exceeds the
            auto-approve threshold. Human approval required.
          </p>
          <KV label="status" value={p.status} accent />
          <KV label="request_id" value={p.request_id} />
          <div className="mt-4">
            <Button
              disabled={deciding || !live}
              onClick={() => void approve()}
              title={
                live ? "" : "Approve runs against the real queue in LIVE mode"
              }
            >
              {deciding ? "Approving..." : "Approve correction"}
            </Button>
          </div>
        </Plate>
      </section>
    );
  }

  return (
    <section>
      <SectionLabel>Correction payment</SectionLabel>
      <Plate>
        <KV label="payment_id" value={p.payment_id} />
        <KV label="amount" value={centsToUSD(p.amount_cents)} accent />
        <KV label="status" value={p.status} />
        <Rule />
        <div className="pt-3">
          <p className="mb-1 font-mono text-[0.65rem] uppercase tracking-[0.2em] text-muted-foreground/60">
            Ed25519 receipt
          </p>
          <p className="font-mono text-xs text-muted-foreground break-all">
            {p.audit_hash}
          </p>
        </div>
      </Plate>
    </section>
  );
}

function AuditSection({ report }: { report: StrReconciliationReport }) {
  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <SectionLabel>Audit chain</SectionLabel>
        <StatusPill
          ok={report.audit_ok}
          label={report.audit_ok ? "CHAIN OK" : "CHAIN FAULT"}
        />
      </div>
      <KV label="detail" value={report.audit_detail || "n/a"} />
    </section>
  );
}
