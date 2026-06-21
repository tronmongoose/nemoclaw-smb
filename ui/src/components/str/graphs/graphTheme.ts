/** Per-portal graph palettes. The force-graph canvas is painted via props (not CSS),
 *  so it can't inherit the data-portal tokens; these palettes keep each graph in step
 *  with its portal temperature (warm sand / cool / dark electric / dark technical). */

import type { PortalView } from "../../../types";

export interface GraphPalette {
  canvas: string;
  label: string;
  link: string;
  kinds: Record<string, string>;
  fallback: string;
}

const OWNER: GraphPalette = {
  canvas: "#f3efe6",
  label: "#3a322a",
  link: "#d8cdb8",
  kinds: {
    root: "#2f9e7e",
    property: "#46b89a",
    owner: "#b69a6f",
    firm: "#b69a6f",
    crew: "#cdbb95",
    booking: "#cdbb95",
    fee: "#cdbb95",
    sub: "#cdbb95",
    earn: "#cdbb95",
  },
  fallback: "#cdbb95",
};

const FIRM: GraphPalette = {
  canvas: "#e9f1f4",
  label: "#27333a",
  link: "#bcd2d8",
  kinds: {
    root: "#1f93a8",
    firm: "#1f93a8",
    property: "#3aa6b5",
    owner: "#7fa6ad",
    crew: "#9bb6bd",
    booking: "#9bb6bd",
    fee: "#9bb6bd",
    sub: "#9bb6bd",
    earn: "#9bb6bd",
  },
  fallback: "#9bb6bd",
};

const SWARM: GraphPalette = {
  canvas: "#0f1620",
  label: "#cfe7ee",
  link: "#27313d",
  kinds: {
    root: "#22d3ee",
    property: "#3aa6c9",
    owner: "#6f9bb5",
    firm: "#5b8aa6",
    crew: "#88a3b5",
    booking: "#88a3b5",
    fee: "#88a3b5",
    sub: "#88a3b5",
    earn: "#7fd8c2",
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
