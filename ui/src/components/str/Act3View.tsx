/** Act III (Platform): the STR platform earn server.
 *
 *   - the MPP 402-then-200 earn loop (see MppEarnCall)
 *   - the AEO audit: computed score breakdown, the dog-only CRITICAL flag,
 *     the optimized opening, and the proposed JSON-LD
 *   - the dynamic pricing recommendation
 *   - platform earn metrics
 *
 * Score, breakdown, optimized opening, and pricing come live off the API. The
 * critical-flag set and JSON-LD are the documented Clementine remediation
 * artifacts (not on the serialized AEO response) and are clearly labeled.
 * Fails soft to empty states when the API is unreachable.
 */

import { useState } from "react";
import { useFetch } from "../../hooks/useFetch";
import { apiPost } from "../../lib/api";
import { StrAeoResponse, StrMetrics, StrPriceResponse } from "../../types";
import { liveParam, useLive } from "./LiveContext";
import { centsToUSD, EmptyState, KV, SectionLabel } from "./shared";
import { MppEarnCall } from "./MppEarnCall";
import { postAeoAudit } from "./strApi";
import { CLEMENTINE_JSON_LD, DOG_ONLY_CRITICAL } from "./aeoCanonical";

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
    <div className="flex flex-col gap-6">
      <MppEarnCall />
      <AeoBlock />
      <PricingBlock />
      <MetricsBlock />
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
    <section>
      <div className="flex items-center justify-between mb-3">
        <SectionLabel>AEO audit: Sweet Clementine</SectionLabel>
        <button
          disabled={busy}
          onClick={() => void run()}
          className="px-4 py-1.5 rounded bg-cyan-900 hover:bg-cyan-800 text-cyan-200 border border-cyan-700 font-mono text-xs disabled:opacity-40"
        >
          {busy ? "Auditing..." : "Run AEO audit ($1.00)"}
        </button>
      </div>

      {!r || !d ? (
        <EmptyState hint="POST /str/act3/aeo-audit (Bearer mpp_tok_demo)" />
      ) : (
        <div className="flex flex-col gap-3">
          <div className="border border-slate-800 rounded p-4">
            <div className="flex items-baseline justify-between mb-3">
              <span className="font-mono text-xs text-slate-500 uppercase tracking-widest">Score</span>
              <span className="font-mono text-2xl font-bold text-amber-300">{r.overall_score}/100</span>
            </div>
            <KV label="structure completeness" value={`${d.structure_completeness}/25`} />
            <KV label="agent parseability" value={`${d.agent_parseability}/25`} />
            <KV label="description quality" value={`${d.description_quality}/25`} />
            <KV label="conflict-free" value={`${d.conflict_free}/25`} />
          </div>

          <div className="border border-red-900 bg-red-950/20 rounded p-4 font-mono text-xs flex flex-col gap-2">
            <span className="self-start px-2 py-1 rounded border border-red-700 bg-red-950 text-red-400">
              {DOG_ONLY_CRITICAL.severity} {DOG_ONLY_CRITICAL.code}
            </span>
            <p className="text-slate-300 leading-relaxed">{DOG_ONLY_CRITICAL.message}</p>
            <p className="text-slate-500 leading-relaxed">{DOG_ONLY_CRITICAL.plain_english}</p>
          </div>

          <div className="border border-slate-800 rounded p-4">
            <SectionLabel>Optimized opening</SectionLabel>
            <p className="font-mono text-xs text-slate-300 leading-relaxed">{r.optimized_opening}</p>
          </div>

          <div className="border border-slate-800 rounded p-4 overflow-hidden">
            <SectionLabel>Proposed JSON-LD</SectionLabel>
            <pre className="font-mono text-xs text-slate-400 overflow-auto leading-relaxed">
              {JSON.stringify(CLEMENTINE_JSON_LD, null, 2)}
            </pre>
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
    <section>
      <div className="flex items-center justify-between mb-3">
        <SectionLabel>Dynamic pricing</SectionLabel>
        <button
          disabled={busy}
          onClick={() => void run()}
          className="px-4 py-1.5 rounded bg-cyan-900 hover:bg-cyan-800 text-cyan-200 border border-cyan-700 font-mono text-xs disabled:opacity-40"
        >
          {busy ? "Pricing..." : "Run pricing ($0.25)"}
        </button>
      </div>
      {!rec ? (
        <EmptyState hint="POST /str/act3/price" />
      ) : (
        <div className="border border-slate-800 rounded p-4">
          <div className="flex items-baseline justify-between mb-3">
            <span className="font-mono text-xs text-slate-500 uppercase tracking-widest">Recommended rate</span>
            <span className="font-mono text-2xl font-bold text-amber-300">${rec.recommended_rate.toFixed(0)}</span>
          </div>
          <KV label="confidence" value={rec.confidence} />
          <KV label="valid for" value={`${rec.valid_for_hours}h`} />
          <p className="font-mono text-xs text-slate-400 mt-3 pt-3 border-t border-slate-800 leading-relaxed">
            {rec.reasoning}
          </p>
        </div>
      )}
    </section>
  );
}

function MetricsBlock() {
  const { live } = useLive();
  const { data } = useFetch<StrMetrics>(`/str/act3/metrics${liveParam(live)}`);

  if (!data) {
    return (
      <section>
        <SectionLabel>Earn metrics</SectionLabel>
        <EmptyState hint="GET /str/act3/metrics" />
      </section>
    );
  }

  return (
    <section>
      <SectionLabel>Earn metrics</SectionLabel>
      <div className="border border-slate-800 rounded p-4">
        <KV label="calls served" value={data.calls_served} />
        <KV label="revenue earned" value={centsToUSD(data.revenue_earned_cents)} accent />
        <KV label="properties optimized" value={data.properties_optimized} />
      </div>
    </section>
  );
}
