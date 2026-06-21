/** firmGraph: management-firm entity graph for the STR firm segment view.
 *
 * Exports build() -> { nodes, links } representing one PM firm managing
 * three owners across five properties with a shared cleaning crew.
 */

import type { GraphData, GraphNode, GraphLink } from "./ownerGraph";
export type { GraphData, GraphNode, GraphLink };

export default function build(): GraphData {
  const nodes: GraphNode[] = [
    { id: "firm-1", label: "Coastline PM", kind: "firm" },
    { id: "owner-a", label: "Kimberly", kind: "owner" },
    { id: "owner-b", label: "Marcus", kind: "owner" },
    { id: "owner-c", label: "Diane", kind: "owner" },
    { id: "prop-a1", label: "Sweet Clementine by the Sea", kind: "property" },
    { id: "prop-a2", label: "Pelican Cottage", kind: "property" },
    { id: "prop-b1", label: "Surf Break Studio", kind: "property" },
    { id: "prop-b2", label: "Harbor View Loft", kind: "property" },
    { id: "prop-c1", label: "The Tidepool Bungalow", kind: "property" },
    { id: "crew-1", label: "Crew: Seaside Cleans", kind: "crew" },
  ];

  const links: GraphLink[] = [
    { source: "firm-1", target: "owner-a" },
    { source: "firm-1", target: "owner-b" },
    { source: "firm-1", target: "owner-c" },
    { source: "owner-a", target: "prop-a1" },
    { source: "owner-a", target: "prop-a2" },
    { source: "owner-b", target: "prop-b1" },
    { source: "owner-b", target: "prop-b2" },
    { source: "owner-c", target: "prop-c1" },
    { source: "crew-1", target: "prop-a1" },
    { source: "crew-1", target: "prop-b1" },
    { source: "crew-1", target: "prop-c1" },
  ];

  return { nodes, links };
}
