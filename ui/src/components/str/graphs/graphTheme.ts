/** Per-portal graph palettes. The force-graph canvas is painted via props (not CSS), so
 *  it can't inherit the data-portal tokens; these palettes keep each graph in step with its
 *  portal temperature: Owner warm-light/orange, Company cool-dark/blue, Swarm + tech layer
 *  electric-dark/cyan. */

import type { PortalView } from "../../../types";

export interface GraphPalette {
  canvas: string;
  label: string;
  link: string;
  kinds: Record<string, string>;
  fallback: string;
}

const OWNER: GraphPalette = {
  canvas: "#f6f1e8",
  label: "#2e2419",
  link: "#d3c8b6",
  kinds: {
    root: "#c8772a",
    property: "#d98f43",
    owner: "#b39a78",
    firm: "#b39a78",
    crew: "#cbb78f",
    booking: "#cbb78f",
    fee: "#cbb78f",
    sub: "#cbb78f",
    earn: "#cbb78f",
  },
  fallback: "#cbb78f",
};

const FIRM: GraphPalette = {
  canvas: "#202c39",
  label: "#d8e2ec",
  link: "#34414f",
  kinds: {
    root: "#50a6ea",
    firm: "#50a6ea",
    property: "#74bbef",
    owner: "#8098ad",
    crew: "#8ea4b4",
    booking: "#8ea4b4",
    fee: "#8ea4b4",
    sub: "#8ea4b4",
    earn: "#8ea4b4",
  },
  fallback: "#8ea4b4",
};

const SWARM: GraphPalette = {
  canvas: "#0e111b",
  label: "#d6ecf5",
  link: "#232f44",
  kinds: {
    root: "#1fd8ee",
    property: "#3bb3d4",
    owner: "#6f9bb5",
    firm: "#5d89a6",
    crew: "#88a3b5",
    booking: "#88a3b5",
    fee: "#88a3b5",
    sub: "#88a3b5",
    earn: "#79d8c0",
  },
  fallback: "#88a3b5",
};

const STACK: GraphPalette = {
  canvas: "#12161c",
  label: "#cfe2e6",
  link: "#283039",
  kinds: {},
  fallback: "#88a3b5",
};

export function graphPalette(portal: PortalView): GraphPalette {
  if (portal === "owner") return OWNER;
  if (portal === "firm") return FIRM;
  if (portal === "agent") return SWARM;
  return STACK;
}
