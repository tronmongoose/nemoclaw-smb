/** The badge that proves a reasoning result is real.
 *
 * LIVE  => amber, with the heartbeat dot, shows model id + measured latency
 *          (e.g. "LIVE nemotron 41s").
 * DEMO  => muted, shows "DEMO cached".
 *
 * Reads the ReasoningProvenance attached to every model-backed STR result, so
 * the source of truth is the API response, not the UI toggle alone.
 */

import { ReasoningProvenance } from "../../types";

function shortModel(model: string): string {
  // "nvidia/nemotron-3-ultra-550b-a55b[demo-cached]" -> "nemotron"
  const tail = model.split("/").pop() ?? model;
  const base = tail.split("[")[0];
  if (base.includes("nemotron")) return "nemotron";
  if (base.includes("hermes")) return "hermes";
  return base.split("-")[0] || base;
}

function formatLatency(ms: number): string {
  if (ms <= 0) return "0ms";
  if (ms < 1000) return `${Math.round(ms)}ms`;
  return `${(ms / 1000).toFixed(0)}s`;
}

export function ProvenanceBadge({ prov }: { prov?: ReasoningProvenance | null }) {
  if (!prov) {
    return (
      <span className="rounded-[var(--radius)] border border-border px-2 py-1 font-mono text-xs text-muted-foreground">
        no reasoning
      </span>
    );
  }

  const model = shortModel(prov.model);

  if (prov.mode === "live") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-[var(--radius)] border border-primary bg-[hsl(var(--primary)/0.12)] px-2 py-1 font-mono text-xs text-primary">
        <span className="h-1.5 w-1.5 rounded-full bg-primary animate-heartbeat" />
        LIVE {model} {formatLatency(prov.latency_ms)}
      </span>
    );
  }

  return (
    <span className="rounded-[var(--radius)] border border-border px-2 py-1 font-mono text-xs text-muted-foreground">
      DEMO {model.replace("[demo-cached]", "")} cached
    </span>
  );
}
