/** Anti-vaporware centerpiece: sponsor-technology node graph with per-pillar live verification. */

import { useEffect, useRef, useState, useCallback } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { apiFetch } from "../../lib/api";
import type { IntegrationStatusResponse, IntegrationVerify } from "../../types";
import { SectionLabel, StatusPill, ElapsedCounter, EmptyState, Plate } from "./shared";
import { Button } from "@/components/ui/button";

// Status -> fill color mapping. Light beach background: #eef4f4.
const STATUS_COLORS: Record<string, string> = {
  REAL: "#2f9e7e",           // deep sea-green
  "LIVE-OK": "#2f9e7e",      // deep sea-green
  "LIVE-CAPABLE": "#46b89a", // sea-foam
  DEMO: "#9bb0b2",           // muted slate-blue
  "LIVE-FAIL": "#e0664f",    // coral
  "NOT-CONFIGURED": "#bcc8c8", // dim
};

function statusColor(status: string): string {
  return STATUS_COLORS[status] ?? "#9bb0b2";
}

function statusOk(status: string): boolean {
  return status === "REAL" || status === "LIVE-OK" || status === "LIVE-CAPABLE";
}

interface GraphNode {
  id: string;
  label: string;
  status: string;
  kind: string;
  x?: number;
  y?: number;
}

interface VerifyState {
  pending: boolean;
  result: IntegrationVerify | null;
}

interface Props {
  width?: number;
  height?: number;
}

export function StackGraph({ width = 480, height = 380 }: Props) {
  const [data, setData] = useState<IntegrationStatusResponse | null | undefined>(undefined);
  // nodeStatuses: mutable status overrides from live-verify results
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, string>>({});
  const [verifyStates, setVerifyStates] = useState<Record<string, VerifyState>>({});
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    apiFetch<IntegrationStatusResponse>("/integrations/status").then((res) => {
      setData(res ?? null);
    });
  }, []);

  const handleVerify = useCallback(
    async (id: string) => {
      setVerifyStates((prev) => ({ ...prev, [id]: { pending: true, result: null } }));
      const result = await apiFetch<IntegrationVerify>(`/integrations/verify?pillar=${id}`);
      setVerifyStates((prev) => ({ ...prev, [id]: { pending: false, result: result ?? null } }));
      if (result) {
        setNodeStatuses((prev) => ({ ...prev, [id]: result.status }));
      }
    },
    []
  );

  if (data === undefined) return null;
  if (data === null) return <EmptyState hint="Integration status unavailable" />;

  const { agent, pillars } = data;

  // Build graph nodes and links
  const graphNodes: GraphNode[] = [
    { id: agent.id, label: agent.label, status: nodeStatuses[agent.id] ?? agent.status, kind: agent.kind },
    ...pillars.map((p) => ({
      id: p.id,
      label: p.label,
      status: nodeStatuses[p.id] ?? p.status,
      kind: p.kind,
    })),
  ];

  const graphLinks = pillars.map((p) => ({
    source: agent.id,
    target: p.id,
    kind: p.kind,
  }));

  const graphData = { nodes: graphNodes, links: graphLinks };

  return (
    <div className="flex flex-col gap-6">
      {/* Canvas */}
      <div ref={containerRef} className="overflow-hidden rounded-[var(--radius)] border border-border">
        <ForceGraph2D
          width={width}
          height={height}
          graphData={graphData}
          backgroundColor="#eef4f4"
          nodeLabel="label"
          nodeColor={(n) => statusColor((n as GraphNode).status)}
          nodeRelSize={7}
          linkColor={() => "#c2d2d2"}
          linkWidth={1.5}
          nodeCanvasObjectMode={() => "after"}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const n = node as GraphNode & { x: number; y: number };
            const label = n.label;
            const fontSize = Math.max(9, 12 / globalScale);
            ctx.font = `${fontSize}px monospace`;
            ctx.fillStyle = "#2c4a4a";
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillText(label, n.x, n.y + 10);
          }}
        />
      </div>

      {/* Accessible text list */}
      <div aria-label="Integration pillars" className="flex flex-col gap-3">
        <SectionLabel>Sponsor Stack</SectionLabel>
        {pillars.map((pillar) => {
          const currentStatus = nodeStatuses[pillar.id] ?? pillar.status;
          const vs = verifyStates[pillar.id];
          const verifyResult = vs?.result ?? null;

          return (
            <Plate key={pillar.id} className="flex flex-col gap-2">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-sm font-medium text-foreground">
                    {pillar.label}
                  </span>
                  {pillar.vendor && (
                    <span className="font-mono text-xs text-muted-foreground">{pillar.vendor}</span>
                  )}
                  <StatusPill ok={statusOk(currentStatus)} label={currentStatus} />
                </div>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleVerify(pillar.id)}
                  disabled={vs?.pending ?? false}
                  aria-label={`Verify live ${pillar.label}`}
                >
                  Verify live
                </Button>
              </div>

              {/* Detail line */}
              {pillar.detail && (
                <p className="font-mono text-xs text-muted-foreground">{pillar.detail}</p>
              )}

              {/* Verify result */}
              {vs?.pending && (
                <ElapsedCounter
                  running={true}
                  label={`Verifying ${pillar.label}`}
                />
              )}
              {verifyResult && !vs?.pending && (
                <span className="font-mono text-xs text-verified">
                  {verifyResult.status} {verifyResult.latency_ms}ms &mdash; {verifyResult.detail}
                </span>
              )}

              {/* Skills */}
              {pillar.skills && pillar.skills.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {pillar.skills.map((skill) => (
                    <span
                      key={skill}
                      className="rounded-[var(--radius)] border border-border bg-background px-1.5 py-0.5 font-mono text-[0.65rem] text-muted-foreground"
                    >
                      {skill}
                    </span>
                  ))}
                </div>
              )}
            </Plate>
          );
        })}
      </div>
    </div>
  );
}
