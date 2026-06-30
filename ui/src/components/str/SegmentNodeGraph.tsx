/** SegmentNodeGraph: the entity graph for a portal, an Obsidian-style force-directed
 *  node map. Node size encodes kind; each label sits in a readable chip below its node;
 *  hovering a node brightens it. Colors follow the portal palette; an accessible text list
 *  mirrors the graph for screen readers. */

import { useEffect, useMemo, useRef, useState } from "react";
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

/** Relative node weight by kind: roots largest, then owners/properties, leaves small. */
function sizeFor(kind: string): number {
  if (kind === "root" || kind === "firm") return 6;
  if (kind === "owner") return 4;
  if (kind === "property") return 3.4;
  if (kind === "crew") return 3;
  return 2;
}

/** A hex color at the given alpha, for chips and softened links. */
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
  height?: number;
}

export function SegmentNodeGraph({ segment, height = 520 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const [width, setWidth] = useState(480);
  const [hover, setHover] = useState<string | null>(null);

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

  // Organic force layout (no DAG): strong repulsion + a long link distance so the
  // cluster spreads and labels breathe, re-heated whenever the graph changes.
  useEffect(() => {
    const fg = fgRef.current;
    if (!fg) return;
    fg.d3Force("charge")?.strength(-520);
    fg.d3Force("link")?.distance(70);
    fg.d3ReheatSimulation?.();
    // Frame the graph to fill its box. onEngineStop can be missed (or fire before the
    // layout spreads), leaving a small cluster in a big empty box; re-fit on a timer too.
    const t1 = setTimeout(() => fg.zoomToFit?.(400, 28), 1000);
    const t2 = setTimeout(() => fg.zoomToFit?.(400, 28), 2300);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
    };
  }, [segment, width, height]);

  // Stable graph data: rebuilding on every render resets the force simulation, leaving
  // the nodes mid-drift (clustered, not framed). Memoize so the layout settles once.
  const graphData: GraphData = useMemo(() => builderFor(segment)(), [segment]);
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
        style={{ cursor: hover ? "pointer" : "default" }}
      >
        <ForceGraph2D
          ref={fgRef}
          width={width}
          height={height}
          graphData={graphData as unknown as Parameters<typeof ForceGraph2D>[0]["graphData"]}
          backgroundColor={pal.canvas}
          nodeRelSize={6}
          nodeVal={(n) => sizeFor((n as GraphNode).kind)}
          nodeColor={(n) => {
            const node = n as GraphNode;
            if (hover === node.id) return pal.label;
            return pal.kinds[node.kind] ?? pal.fallback;
          }}
          linkColor={() => hexA(pal.link, 0.5)}
          linkWidth={1.1}
          cooldownTicks={220}
          onEngineStop={() => fgRef.current?.zoomToFit(400, 28)}
          onNodeHover={(n) => setHover(n ? (n as GraphNode).id : null)}
          nodeCanvasObjectMode={() => "after"}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const n = node as GraphNode & { x: number; y: number };
            const label = truncate(n.label, 24);
            const fontSize = Math.max(9.5, 12 / globalScale);
            ctx.font = `${fontSize}px ui-monospace, monospace`;
            const w = ctx.measureText(label).width;
            const padX = 4;
            const h = fontSize + 4;
            const r = 6 * Math.sqrt(sizeFor(n.kind)) + 5;
            const top = n.y + r;
            ctx.fillStyle = hexA(pal.canvas, 0.82);
            ctx.beginPath();
            ctx.roundRect(n.x - w / 2 - padX, top, w + padX * 2, h, 3);
            ctx.fill();
            ctx.fillStyle = hover === n.id ? pal.label : pal.label;
            ctx.textAlign = "center";
            ctx.textBaseline = "top";
            ctx.fillText(label, n.x, top + 2);
          }}
        />
      </div>

      <div aria-label={`${labelFor(segment)} entities`} className="sr-only">
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
