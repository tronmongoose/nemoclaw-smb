import { ProvenanceBadge } from "nemoclaw-smb-ui";

const Frame = ({ children }: { children: React.ReactNode }) => (
  <div
    className="bg-background text-foreground"
    style={{ padding: 28, display: "flex", flexDirection: "column", gap: 16, alignItems: "flex-start" }}
  >
    {children}
  </div>
);

/** Live Nemotron call - real reasoning result, 41s latency */
export function ProvenanceBadgeLive() {
  return (
    <Frame>
      <ProvenanceBadge
        prov={{
          mode: "live",
          model: "nvidia/nemotron-3-ultra-550b-a55b",
          latency_ms: 41000,
          source: "nemotron",
        }}
      />
    </Frame>
  );
}

/** Demo mode - cached result, no live inference cost */
export function ProvenanceBadgeDemo() {
  return (
    <Frame>
      <ProvenanceBadge
        prov={{
          mode: "demo",
          model: "nvidia/nemotron-3-ultra-550b-a55b[demo-cached]",
          latency_ms: 0,
          source: "cached",
        }}
      />
    </Frame>
  );
}

/** No provenance - result predates reasoning attachment or API gap */
export function ProvenanceBadgeNone() {
  return (
    <Frame>
      <ProvenanceBadge prov={undefined} />
    </Frame>
  );
}

/** Side-by-side comparison - LIVE/DEMO toggle context */
export function ProvenanceBadgeComparison() {
  return (
    <Frame style={{ flexDirection: "row", gap: 12 } as React.CSSProperties}>
      <ProvenanceBadge
        prov={{
          mode: "live",
          model: "nvidia/nemotron-3-ultra-550b-a55b",
          latency_ms: 41000,
          source: "nemotron",
        }}
      />
      <ProvenanceBadge
        prov={{
          mode: "demo",
          model: "nvidia/nemotron-3-ultra-550b-a55b[demo-cached]",
          latency_ms: 0,
          source: "cached",
        }}
      />
      <ProvenanceBadge prov={undefined} />
    </Frame>
  );
}
