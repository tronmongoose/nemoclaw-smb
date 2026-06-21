/** agentGraph: platform-level entity graph for the STR agent segment view.
 *
 * Exports build() -> { nodes, links } representing the NemoClaw Agent platform
 * across four PM firms, with a sample of owners/properties under one firm
 * and a shared earn-pool node.
 */

import type { GraphData, GraphNode, GraphLink } from "./ownerGraph";
export type { GraphData, GraphNode, GraphLink };

export default function build(): GraphData {
  const nodes: GraphNode[] = [
    { id: "platform", label: "NemoClaw Agent", kind: "root" },
    { id: "firm-coast", label: "Coastline PM", kind: "firm" },
    { id: "firm-dune", label: "Dune Property Group", kind: "firm" },
    { id: "firm-harbor", label: "Harbor Host Co.", kind: "firm" },
    { id: "firm-tide", label: "Tidewater Stays", kind: "firm" },
    { id: "owner-coast-1", label: "Kimberly", kind: "owner" },
    { id: "owner-coast-2", label: "Marcus", kind: "owner" },
    { id: "prop-coast-1", label: "Sweet Clementine by the Sea", kind: "property" },
    { id: "prop-coast-2", label: "Surf Break Studio", kind: "property" },
    { id: "earn-pool", label: "Earn Pool", kind: "earn" },
  ];

  const links: GraphLink[] = [
    { source: "platform", target: "firm-coast" },
    { source: "platform", target: "firm-dune" },
    { source: "platform", target: "firm-harbor" },
    { source: "platform", target: "firm-tide" },
    { source: "firm-coast", target: "owner-coast-1" },
    { source: "firm-coast", target: "owner-coast-2" },
    { source: "owner-coast-1", target: "prop-coast-1" },
    { source: "owner-coast-2", target: "prop-coast-2" },
    { source: "platform", target: "earn-pool" },
  ];

  return { nodes, links };
}
