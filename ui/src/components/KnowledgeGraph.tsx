/** Knowledge graph panel: react-force-graph-2d with node popover. */

import { useRef, useState, useCallback, useEffect } from "react";
import ForceGraph2D from "react-force-graph-2d";
import { GraphNode, GraphEdge, GraphResponse } from "../types";
import { useFetch } from "../hooks/useFetch";

interface NodeObject {
  id: string;
  label: string;
  type: string;
  category: string;
  x?: number;
  y?: number;
}

interface LinkObject {
  source: string | NodeObject;
  target: string | NodeObject;
  amount: number;
  date: string;
  category: string;
  anomaly_flag: boolean;
}

// High-contrast fills: warm off-white for labels; amber for company; muted neutrals for vendors.
// Red is reserved for anomaly edges only.
const CATEGORY_COLORS: Record<string, string> = {
  software: "#94a3b8",   // slate-400 — readable on dark background
  infrastructure: "#7dd3c0", // muted teal, not cyan
  marketing: "#fbbf24",  // amber-400 — warm accent
  payroll: "#a5b4fc",    // indigo-300 — differentiated, not purple neon
  services: "#93c5fd",   // blue-300 — readable
  self: "#f59e0b",       // amber-500 — company node accent
};

function nodeColor(node: GraphNode): string {
  // Company node gets amber; all vendors get category color or neutral warm white.
  if (node.type === "self") return "#f59e0b";
  return CATEGORY_COLORS[node.category] ?? "#cbd5e1"; // slate-300 default — high contrast
}

interface Popover {
  node: GraphNode;
  x: number;
  y: number;
  edgeCount: number;
}

interface KnowledgeGraphProps {
  width: number;
  height: number;
}

export function KnowledgeGraph({ width, height }: KnowledgeGraphProps) {
  const { data } = useFetch<GraphResponse>("/graph");
  const [popover, setPopover] = useState<Popover | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const edgeCountByNode = useCallback(
    (nodeId: string): number => {
      if (!data) return 0;
      return data.edges.filter(
        (e) => e.source === nodeId || e.target === nodeId
      ).length;
    },
    [data]
  );

  const handleNodeClick = useCallback(
    (node: NodeObject, event: MouseEvent) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (!rect) return;
      setPopover({
        node: node as unknown as GraphNode,
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
        edgeCount: edgeCountByNode(node.id),
      });
    },
    [edgeCountByNode]
  );

  useEffect(() => {
    const close = () => setPopover(null);
    window.addEventListener("click", close);
    return () => window.removeEventListener("click", close);
  }, []);

  if (!data) {
    return (
      <div className="flex items-center justify-center h-full text-slate-600 font-mono text-sm">
        Graph unavailable — API offline
      </div>
    );
  }

  const graphData = {
    nodes: data.nodes.map((n) => ({ ...n })),
    links: data.edges.map((e: GraphEdge) => ({ ...e })),
  };

  return (
    <div ref={containerRef} className="relative" style={{ width, height }}>
      <ForceGraph2D
        width={width}
        height={height}
        graphData={graphData}
        backgroundColor="#020617"
        nodeLabel="label"
        nodeColor={(n) => nodeColor(n as unknown as GraphNode)}
        nodeRelSize={6}
        linkColor={(l) =>
          // Red for anomaly; slate-500 for normal (visible but not dominant)
          (l as unknown as LinkObject).anomaly_flag ? "#ef4444" : "#64748b"
        }
        linkWidth={(l) =>
          (l as unknown as LinkObject).anomaly_flag ? 2.5 : 1
        }
        onNodeClick={(node, event) =>
          handleNodeClick(node as unknown as NodeObject, event)
        }
      />
      {popover && (
        <NodePopover
          popover={popover}
          onClose={() => setPopover(null)}
        />
      )}
    </div>
  );
}

function NodePopover({
  popover,
  onClose,
}: {
  popover: Popover;
  onClose: () => void;
}) {
  return (
    <div
      className="absolute z-10 bg-slate-800 border border-slate-700 rounded p-3 shadow-xl text-xs font-mono min-w-[160px]"
      style={{ left: popover.x + 8, top: popover.y + 8 }}
      onClick={(e) => e.stopPropagation()}
    >
      <button
        className="absolute top-1 right-2 text-slate-500 hover:text-slate-300"
        onClick={onClose}
      >
        x
      </button>
      <div className="text-slate-100 font-bold mb-1">{popover.node.label}</div>
      <div className="text-slate-400">
        category:{" "}
        <span className="text-slate-200">{popover.node.category}</span>
      </div>
      <div className="text-slate-400">
        type: <span className="text-slate-200">{popover.node.type}</span>
      </div>
      <div className="text-slate-400">
        payments: <span className="text-slate-200">{popover.edgeCount}</span>
      </div>
    </div>
  );
}

