/** Act III (Platform): one licensed agent, three capability upgrades, agent marketplace. */

import { useState } from "react";
import { useFetch } from "../../hooks/useFetch";
import { apiPost } from "../../lib/api";
import { StrAeoResponse, StrGuestCommsResponse, StrMetrics, StrPriceResponse } from "../../types";
import { liveParam, useLive } from "./LiveContext";
import {
  centsToUSD,
  ElapsedCounter,
  EmptyState,
  KV,
  Plate,
  Rule,
  SectionLabel,
  Stat,
  StatusPill,
} from "./shared";
import { MppEarnCall } from "./MppEarnCall";
import { ProvenanceBadge } from "./ProvenanceBadge";
import { postAeoAudit, postGuestComms } from "./strApi";
import { CLEMENTINE_JSON_LD, DOG_ONLY_CRITICAL } from "./aeoCanonical";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

const PRICE_BODY = {
  property_id: "prop-001",
  current_rate: 200.0,
  occupancy_rate: 0.75,
  local_events: ["Comic-Con International"],
  comp_set_rates: [195.0, 215.0],
  season: "peak",
  day_of_week: "sat",
};

export function Act3View() {
  return (
    <div className="flex flex-col gap-8">
      <div>
        <h2 className="font-serif text-2xl font-semibold text-foreground mb-1">
          The Swarm
        </h2>
        <p className="font-mono text-xs text-muted-foreground max-w-prose leading-relaxed">
          One agent, licensed to every property manager. It upgrades their
          marketing, sales, and pricing, and earns per call in an agent
          marketplace. C1 governs every call, Nemotron and Hermes reason, the
          agent earns.
        </p>
      </div>

      <AeoBlock />
      <Rule />
      <GuestCommsBlock />
      <Rule />
      <PricingBlock />
      <Rule />
      <section id="section-marketplace" className="flex scroll-mt-24 flex-col gap-4">
        <SectionLabel>Agent marketplace</SectionLabel>
        <MppEarnCall />
        <MetricsBlock />
      </section>
    </div>
  );
}

function AeoBlock() {
  const { live } = useLive();
  const [data, setData] = useState<StrAeoResponse | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    const res = await postAeoAudit(live);
    setData(res);
    setBusy(false);
  }

  const r = data?.result;
  const d = r?.dimension_scores;

  return (
    <section id="section-marketing" className="flex scroll-mt-24 flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <SectionLabel>Marketing readiness</SectionLabel>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <Button
            disabled={busy}
            onClick={() => void run()}
            className="font-mono text-xs"
          >
            {busy ? "Auditing..." : "Run marketing audit ($1.00)"}
          </Button>
          <ElapsedCounter running={busy} />
        </div>
      </div>

      <p className="font-mono text-xs text-muted-foreground leading-relaxed max-w-prose">
        Grades how well this listing can be found, ranked, and booked by AI
        booking agents.
      </p>

      {!r || !d ? (
        busy ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : (
          <EmptyState hint="POST /str/act3/aeo-audit (Bearer mpp_tok_demo)" />
        )
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-3">
            <Stat label="marketing readiness score" value={`${r.overall_score}/100`} />
            <div className="grid grid-cols-2 gap-x-6">
              <KV label="structure completeness" value={`${d.structure_completeness}/25`} />
              <KV label="agent parseability" value={`${d.agent_parseability}/25`} />
              <KV label="description quality" value={`${d.description_quality}/25`} />
              <KV label="conflict-free" value={`${d.conflict_free}/25`} />
            </div>
          </div>

          {data?.c1_authorized && (
            <div className="flex items-center gap-3">
              <StatusPill ok label={`agent earned ${centsToUSD(data.amount_cents)}, C1 authorized`} />
            </div>
          )}

          <Plate className="border-destructive bg-[hsl(var(--destructive)/0.06)]">
            <div className="flex flex-col gap-2 font-mono text-xs">
              <span className="self-start border border-destructive text-destructive rounded-[var(--radius)] px-2 py-1">
                {DOG_ONLY_CRITICAL.severity} {DOG_ONLY_CRITICAL.code}
              </span>
              <p className="text-foreground leading-relaxed">{DOG_ONLY_CRITICAL.message}</p>
              <p className="text-muted-foreground leading-relaxed">{DOG_ONLY_CRITICAL.plain_english}</p>
            </div>
          </Plate>

          <div>
            <SectionLabel>Optimized opening</SectionLabel>
            <Plate>
              <p className="font-mono text-xs text-foreground leading-relaxed">
                {r.optimized_opening}
              </p>
            </Plate>
          </div>

          <div>
            <SectionLabel>Proposed JSON-LD</SectionLabel>
            <Plate>
              <pre className="font-mono text-xs text-muted-foreground overflow-auto leading-relaxed max-h-64">
                {JSON.stringify(CLEMENTINE_JSON_LD, null, 2)}
              </pre>
            </Plate>
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <SectionLabel>Reasoning</SectionLabel>
              <ProvenanceBadge prov={r.reasoning_provenance} />
            </div>
            <p className="font-mono text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">
              {r.reasoning_trace}
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

function GuestCommsBlock() {
  const { live } = useLive();
  const [data, setData] = useState<StrGuestCommsResponse | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    const res = await postGuestComms(live);
    setData(res);
    setBusy(false);
  }

  const res = data?.result;

  return (
    <section id="section-sales" className="flex scroll-mt-24 flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <SectionLabel>Sales upgrade</SectionLabel>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => void run()}
            className="font-mono text-xs"
          >
            {busy ? "Drafting..." : "Draft guest reply ($1.50)"}
          </Button>
          <ElapsedCounter running={busy} label="Calling Hermes" />
        </div>
      </div>

      {!res ? (
        busy ? (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        ) : (
          <EmptyState hint="POST /str/act3/guest-comms" />
        )
      ) : (
        <div className="flex flex-col gap-3">
          <KV label="intent" value={res.intent} />

          <div>
            <SectionLabel>Drafted reply</SectionLabel>
            <Plate>
              <p className="font-serif text-sm text-foreground leading-relaxed">
                {res.message}
              </p>
            </Plate>
          </div>

          <KV label="upsell" value={res.upsell} />

          {data?.c1_authorized && (
            <StatusPill
              ok
              label={`agent earned ${centsToUSD(data.amount_cents)}, C1 authorized`}
            />
          )}

          <div className="flex items-center justify-between">
            <SectionLabel>Reasoning</SectionLabel>
            <ProvenanceBadge prov={res.reasoning_provenance} />
          </div>
        </div>
      )}
    </section>
  );
}

function PricingBlock() {
  const { live } = useLive();
  const [data, setData] = useState<StrPriceResponse | null>(null);
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    const res = await apiPost<StrPriceResponse>(`/str/act3/price${liveParam(live)}`, PRICE_BODY);
    setData(res);
    setBusy(false);
  }

  const rec = data?.recommendation;

  return (
    <section id="section-pricing" className="flex scroll-mt-24 flex-col gap-4">
      <div className="flex items-start justify-between gap-4">
        <SectionLabel>Pricing upgrade</SectionLabel>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <Button
            variant="outline"
            disabled={busy}
            onClick={() => void run()}
            className="font-mono text-xs"
          >
            {busy ? "Pricing..." : "Run pricing ($0.25)"}
          </Button>
          <ElapsedCounter running={busy} />
        </div>
      </div>

      {!rec ? (
        busy ? (
          <Skeleton className="h-28 w-full" />
        ) : (
          <EmptyState hint="POST /str/act3/price" />
        )
      ) : (
        <div className="flex flex-col gap-3">
          <Stat
            label="recommended rate"
            value={`$${rec.recommended_rate.toFixed(0)}`}
            sub={`confidence: ${rec.confidence} | valid ${rec.valid_for_hours}h`}
          />

          {data?.c1_authorized && (
            <StatusPill ok label={`agent earned ${centsToUSD(data.amount_cents)}, C1 authorized`} />
          )}

          <div>
            <div className="flex items-center justify-between mb-2">
              <SectionLabel>Reasoning</SectionLabel>
              <ProvenanceBadge prov={rec.reasoning_provenance} />
            </div>
            <p className="font-mono text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">
              {rec.reasoning}
            </p>
          </div>
        </div>
      )}
    </section>
  );
}

function MetricsBlock() {
  const { live } = useLive();
  const { data } = useFetch<StrMetrics>(`/str/act3/metrics${liveParam(live)}`);

  return (
    <section>
      <SectionLabel>Marketplace earnings</SectionLabel>
      {!data ? (
        <EmptyState hint="GET /str/act3/metrics" />
      ) : (
        <div className="flex flex-col gap-1.5">
          <KV label="calls served" value={data.calls_served} />
          <KV label="revenue earned" value={centsToUSD(data.revenue_earned_cents)} accent />
          <KV label="properties served" value={data.properties_optimized} />
        </div>
      )}
    </section>
  );
}
