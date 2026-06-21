/** SegmentNodeGraph: force-directed entity graph, one view per StrSegment audience.
 *
 * Picks the matching graph builder (owner / firm / agent), renders a
 * ForceGraph2D canvas with a calm beachy palette, and renders an accessible
 * text list grouped by node kind beside the canvas.
 */

import { useEffect, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { StrSegment } from "../../types";
import { SectionLabel } from "./shared";
import buildOwner from "./graphs/ownerGraph";
import buildFirm from "./graphs/firmGraph";
import buildAgent from "./graphs/agentGraph";
import type { GraphData, GraphNode } from "./graphs/ownerGraph";
import { graphPalette } from "./graphs/graphTheme";

function builderFor(segment: StrSegment): () => GraphData {
  if (segment === "owner") return buildOwner;
  if (segment === "firm") return buildFirm;
  return buildAgent;
}

function labelFor(segment: StrSegment): string {
  if (segment === "owner") return "Owner entity graph";
  if (segment === "firm") return "Firm entity graph";
  return "Platform entity graph";
}

interface Props {
  segment: StrSegment;
}

export function SegmentNodeGraph({ segment }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [dims, setDims] = useState({ width: 480, height: 340 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setDims({
          width: Math.floor(entry.contentRect.width) || 480,
          height: 340,
        });
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const graphData: GraphData = builderFor(segment)();
  const pal = graphPalette(segment);

  // Group nodes by kind for the accessible text list.
  const byKind: Record<string, GraphNode[]> = {};
  for (const node of graphData.nodes) {
    const bucket = byKind[node.kind] ?? [];
    bucket.push(node);
    byKind[node.kind] = bucket;
  }

  return (
    <div className="flex flex-col gap-6">
      <SectionLabel>{labelFor(segment)}</SectionLabel>

      {/* Canvas */}
      <div
        ref={containerRef}
        className="border border-border rounded-[var(--radius)] overflow-hidden bg-card"
      >
        <ForceGraph2D
          width={dims.width}
          height={dims.height}
          graphData={graphData as unknown as Parameters<typeof ForceGraph2D>[0]["graphData"]}
          backgroundColor={pal.canvas}
          nodeLabel="label"
          nodeColor={(n) => pal.kinds[(n as GraphNode).kind] ?? pal.fallback}
          nodeRelSize={7}
          linkColor={() => pal.link}
          linkWidth={1.5}
          nodeCanvasObjectMode={() => "after"}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const n = node as GraphNode & { x: number; y: number };
            const label = n.label;
            const fontSize = Math.max(9, 12 / globalScale);
            ctx.font = `${fontSize}px monospace`;
            ctx.fillStyle = pal.label;
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillText(label, n.x, n.y + 10);
          }}
        />
      </div>

      {/* Accessible text list grouped by kind */}
      <div aria-label={`${labelFor(segment)} entities`} className="flex flex-col gap-4">
        {Object.entries(byKind).map(([kind, nodes]) => (
          <div key={kind} className="flex flex-col gap-1">
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
              {kind}
            </span>
            <ul className="flex flex-col gap-0.5">
              {nodes.map((node) => (
                <li
                  key={node.id}
                  className="font-mono text-sm text-foreground"
                >
                  {node.label}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}
