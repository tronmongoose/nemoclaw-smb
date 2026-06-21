/** SegmentNodeGraph: the entity graph for a portal, laid out as a clean left-to-right
 *  hierarchy (DAG) so labels never collide. Node size encodes kind; each label sits in a
 *  readable chip below its node. Colors follow the portal palette; an accessible text list
 *  mirrors the graph for screen readers. */

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

/** Relative node size by kind: roots largest, properties mid, leaves small. */
function sizeFor(kind: string): number {
  if (kind === "root" || kind === "firm") return 4.2;
  if (kind === "property" || kind === "owner") return 2.4;
  return 1.5;
}

/** A hex color at the given alpha, for the label chip behind text. */
function hexA(hex: string, a: number): string {
  const m = hex.replace("#", "");
  const r = parseInt(m.slice(0, 2), 16);
  const g = parseInt(m.slice(2, 4), 16);
  const b = parseInt(m.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

interface Props {
  segment: StrSegment;
}

export function SegmentNodeGraph({ segment }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const [width, setWidth] = useState(480);
  const HEIGHT = 480;

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const e = entries[0];
      if (e) setWidth(Math.floor(e.contentRect.width) || 480);
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Spread same-level nodes so their labels have room: strong repulsion plus a longer
  // link distance, re-applied (and reheated) whenever the graph changes.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    fg.d3Force("charge")?.strength(-360);
    fg.d3Force("link")?.distance(46);
    fg.d3ReheatSimulation?.();
  }, [segment, width]);

  const graphData: GraphData = builderFor(segment)();
  const pal = graphPalette(segment);

  const byKind: Record<string, GraphNode[]> = {};
  for (const node of graphData.nodes) {
    (byKind[node.kind] ??= []).push(node);
  }

  return (
    <div className="flex flex-col gap-6">
      <SectionLabel>{labelFor(segment)}</SectionLabel>

      <div
        ref={containerRef}
        className="overflow-hidden rounded-[var(--radius)] border border-border bg-card"
      >
        <ForceGraph2D
          ref={fgRef}
          width={width}
          height={HEIGHT}
          graphData={graphData as unknown as Parameters<typeof ForceGraph2D>[0]["graphData"]}
          backgroundColor={pal.canvas}
          dagMode="lr"
          dagLevelDistance={width < 540 ? 92 : 124}
          nodeRelSize={5}
          nodeVal={(n) => sizeFor((n as GraphNode).kind)}
          nodeColor={(n) => pal.kinds[(n as GraphNode).kind] ?? pal.fallback}
          linkColor={() => pal.link}
          linkWidth={1.2}
          cooldownTicks={120}
          onEngineStop={() => fgRef.current?.zoomToFit(400, 46)}
          nodeCanvasObjectMode={() => "after"}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const n = node as GraphNode & { x: number; y: number };
            const label = truncate(n.label, 24);
            const fontSize = Math.max(9.5, 12 / globalScale);
            ctx.font = `${fontSize}px ui-monospace, monospace`;
            const w = ctx.measureText(label).width;
            const padX = 4;
            const h = fontSize + 4;
            const r = 5 * Math.sqrt(sizeFor(n.kind)) + 5;
            const top = n.y + r;
            ctx.fillStyle = hexA(pal.canvas, 0.82);
            ctx.beginPath();
            ctx.roundRect(n.x - w / 2 - padX, top, w + padX * 2, h, 3);
            ctx.fill();
            ctx.fillStyle = pal.label;
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillText(label, n.x, top + 2);
          }}
        />
      </div>

      <div aria-label={`${labelFor(segment)} entities`} className="flex flex-col gap-4">
        {Object.entries(byKind).map(([kind, nodes]) => (
          <div key={kind} className="flex flex-col gap-1">
            <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">
              {kind}
            </span>
            <ul className="flex flex-col gap-0.5">
              {nodes.map((node) => (
                <li key={node.id} className="font-mono text-sm text-foreground">
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
