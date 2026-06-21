/** Per-portal editorial hero: kicker, big serif headline, dek, a CTA that scrolls to the
 *  live console, and one summary card wired to the real Act data (so the headline numbers
 *  are live, not placeholders). Layout and copy follow the Claude Design Portals template. */

import { useFetch } from "../../hooks/useFetch";
import { usePoll } from "../../hooks/usePoll";
import { useLive, liveParam } from "./LiveContext";
import {
  StrSegment,
  StrReconciliationReport,
  StrPortfolioSummary,
  StrInteractionsResponse,
} from "../../types";
import { centsToUSD } from "./shared";

const COPY: Record<StrSegment, { kicker: string; title: string; dek: string; cta: string }> = {
  owner: {
    kicker: "Portal 01 · Owner",
    title: "Your home, watched over.",
    dek: "One property. An agent reconciles every payout, catches every overcharge, and keeps the books. Owning a rental should feel like reading a receipt, not running a company.",
    cta: "Enter the owner console",
  },
  firm: {
    kicker: "Portal 02 · Company",
    title: "Every door. Every agent. In view.",
    dek: "Dozens of properties and a roster of agents working in parallel, pricing, messaging, reconciling, all visible as they work, all reporting to one operator.",
    cta: "Open the operations console",
  },
  agent: {
    kicker: "Portal 03 · Swarm",
    title: "A market of licensed agents.",
    dek: "Many companies, one substrate. Agents are licensed assets, metered, audited, and dispatched across the whole network from a single command center.",
    cta: "Enter the command center",
  },
};

function scrollToConsole() {
  document.getElementById("console")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function CardStat({ label, value, accent }: { label: string; value: string; accent?: boolean }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="font-mono text-[0.62rem] uppercase tracking-[0.14em] text-muted-foreground">
        {label}
      </span>
      <span className={`font-mono text-2xl font-semibold ${accent ? "text-primary" : "text-foreground"}`}>
        {value}
      </span>
    </div>
  );
}

function CardShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-[var(--radius)] border border-border bg-card/80 p-6 shadow-sm">
      {children}
    </div>
  );
}

function LiveDot({ label }: { label: string }) {
  return (
    <span className="flex items-center gap-2 font-mono text-[0.6rem] uppercase tracking-[0.12em] text-primary">
      <span className="h-1.5 w-1.5 rounded-full bg-primary animate-heartbeat" />
      {label}
    </span>
  );
}

function OwnerCard() {
  const { live } = useLive();
  const { data } = useFetch<StrReconciliationReport>(`/str/act1/prop-001/2026-06${liveParam(live)}`);
  const { data: feed } = usePoll<StrInteractionsResponse>("/str/interactions?segment=owner&limit=200", 4000);
  const revenue = data?.summary?.revenue_cents ?? 0;
  const fee = data?.summary?.line_items?.charged_fee_cents ?? 0;
  const over = data?.anomaly?.overcharge_cents ?? 0;
  const count = feed?.entries?.length ?? 0;

  return (
    <CardShell>
      <div className="mb-5 flex items-center justify-between gap-3">
        <div className="flex flex-col gap-0.5">
          <span className="font-serif text-lg text-foreground">Sweet Clementine by the Sea</span>
          <span className="font-mono text-[0.62rem] uppercase tracking-[0.14em] text-muted-foreground">Oceanside, CA</span>
        </div>
        <LiveDot label="Agent live" />
      </div>
      <div className="grid grid-cols-3 gap-4">
        <CardStat label="Income" value={centsToUSD(revenue)} />
        <CardStat label="Mgmt fee" value={centsToUSD(fee)} />
        <CardStat label="Net" value={centsToUSD(revenue - fee)} accent />
      </div>
      <div className="my-5 h-px bg-border" />
      <div className="flex items-center justify-between gap-3 font-mono text-xs">
        <span className="text-foreground">
          {over > 0 ? `Clawdia caught a ${centsToUSD(over)} overcharge` : "Books reconciled"}
        </span>
        <span className="text-muted-foreground">{count} events</span>
      </div>
    </CardShell>
  );
}

function CompanyCard() {
  const { live } = useLive();
  const { data } = useFetch<StrPortfolioSummary>(`/str/act2/portfolio${liveParam(live)}`);
  const { data: feed } = usePoll<StrInteractionsResponse>("/str/interactions?segment=firm&limit=200", 4000);
  const recent = (feed?.entries ?? []).slice(-3).reverse();

  return (
    <CardShell>
      <div className="mb-5 grid grid-cols-3 gap-4">
        <CardStat label="Properties" value={`${data?.property_count ?? 0}`} />
        <CardStat label="Owners" value={`${data?.owner_count ?? 0}`} accent />
        <CardStat label="Monthly" value={centsToUSD(data?.total_monthly_revenue_cents ?? 0)} />
      </div>
      <div className="flex flex-col">
        {recent.length === 0 && (
          <span className="font-mono text-xs text-muted-foreground">Awaiting agent activity</span>
        )}
        {recent.map((e, i) => (
          <div key={e.entry_hash ?? i} className="flex items-center justify-between gap-3 border-t border-border py-2.5">
            <span className="font-mono text-xs text-foreground">{e.op}</span>
            <span className="font-mono text-[0.6rem] uppercase tracking-[0.1em] text-primary">{e.sponsor}</span>
          </div>
        ))}
      </div>
    </CardShell>
  );
}

function SwarmCard() {
  const { data: feed } = usePoll<StrInteractionsResponse>("/str/interactions?segment=agent&limit=200", 4000);
  const entries = feed?.entries ?? [];
  const earned = entries.reduce((s, e) => s + Number(e.metadata?.amount_cents ?? 0), 0);
  const last = entries.length > 0 ? entries[entries.length - 1] : null;

  return (
    <CardShell>
      <div className="mb-5 grid grid-cols-3 gap-4">
        <CardStat label="Calls served" value={`${entries.length}`} />
        <CardStat label="Earned" value={centsToUSD(earned)} accent />
        <CardStat label="Licensed" value="3" />
      </div>
      <div className="h-px bg-border" />
      <div className="mt-4 truncate font-mono text-[0.7rem] text-muted-foreground">
        {last ? `↳ ${last.op} · metered · audited ✓` : "↳ awaiting agent-to-agent calls"}
      </div>
    </CardShell>
  );
}

function SummaryCard({ portal }: { portal: StrSegment }) {
  if (portal === "owner") return <OwnerCard />;
  if (portal === "firm") return <CompanyCard />;
  return <SwarmCard />;
}

export function HeroSection({ portal }: { portal: StrSegment }) {
  const c = COPY[portal];
  return (
    <section className="mx-auto grid w-full max-w-6xl items-center gap-10 px-6 py-14 lg:grid-cols-[1.04fr_1fr] lg:gap-16 lg:py-20">
      <div>
        <div className="mb-5 font-mono text-[0.72rem] uppercase tracking-[0.24em] text-primary">
          {c.kicker}
        </div>
        <h1
          className="font-serif text-foreground"
          style={{ fontSize: "clamp(2.5rem, 5.4vw, 4.6rem)", fontWeight: 440, lineHeight: 0.98, letterSpacing: "-0.022em", textWrap: "balance" }}
        >
          {c.title}
        </h1>
        <p className="mt-6 max-w-[46ch] text-[1.05rem] leading-relaxed text-muted-foreground">
          {c.dek}
        </p>
        <button
          onClick={scrollToConsole}
          className="mt-8 inline-flex items-center gap-2 rounded-[var(--radius)] bg-primary px-5 py-3 font-mono text-xs font-semibold uppercase tracking-[0.04em] text-primary-foreground transition-opacity hover:opacity-90"
        >
          {c.cta} <span aria-hidden>↓</span>
        </button>
      </div>
      <SummaryCard portal={portal} />
    </section>
  );
}
