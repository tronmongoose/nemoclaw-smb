/** ownerGraph: single-owner entity graph for the STR owner segment view.
 *
 * Exports build() -> { nodes, links } representing one owner's two properties
 * with per-property operational sub-nodes (booking, cleaning, fee ledger).
 */

export interface GraphNode {
  id: string;
  label: string;
  kind: string;
}

export interface GraphLink {
  source: string;
  target: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

export default function build(): GraphData {
  const nodes: GraphNode[] = [
    { id: "owner-1", label: "Kimberly, owner", kind: "owner" },
    { id: "prop-1", label: "Sweet Clementine by the Sea", kind: "property" },
    { id: "prop-2", label: "Pelican Cottage", kind: "property" },
    { id: "booking-1", label: "Booking", kind: "booking" },
    { id: "cleaning-1", label: "Cleaning", kind: "crew" },
    { id: "fee-1", label: "Fee Ledger", kind: "fee" },
    { id: "booking-2", label: "Booking", kind: "booking" },
    { id: "cleaning-2", label: "Cleaning", kind: "crew" },
    { id: "fee-2", label: "Fee Ledger", kind: "fee" },
  ];

  const links: GraphLink[] = [
    { source: "owner-1", target: "prop-1" },
    { source: "owner-1", target: "prop-2" },
    { source: "prop-1", target: "booking-1" },
    { source: "prop-1", target: "cleaning-1" },
    { source: "prop-1", target: "fee-1" },
    { source: "prop-2", target: "booking-2" },
    { source: "prop-2", target: "cleaning-2" },
    { source: "prop-2", target: "fee-2" },
  ];

  return { nodes, links };
}
