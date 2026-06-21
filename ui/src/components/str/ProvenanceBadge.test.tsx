/** Tests for the LIVE/DEMO reasoning badge.
 * Asserts: LIVE badge surfaces a short model id + latency; DEMO badge is muted
 * and says "cached"; null provenance fails soft.
 */

import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ProvenanceBadge } from "./ProvenanceBadge";
import type { ReasoningProvenance } from "../../types";

const LIVE: ReasoningProvenance = {
  mode: "live",
  model: "nvidia/nemotron-3-ultra-550b-a55b",
  latency_ms: 41000,
  source: "nemotron",
};

const DEMO: ReasoningProvenance = {
  mode: "demo",
  model: "nvidia/nemotron-3-ultra-550b-a55b[demo-cached]",
  latency_ms: 0,
  source: "cached",
};

describe("ProvenanceBadge", () => {
  it("LIVE badge shows model id and latency (e.g. LIVE nemotron 41s)", () => {
    const { getByText } = render(<ProvenanceBadge prov={LIVE} />);
    expect(getByText("LIVE nemotron 41s")).toBeInTheDocument();
  });

  it("LIVE badge renders sub-second latency in ms", () => {
    const { getByText } = render(<ProvenanceBadge prov={{ ...LIVE, latency_ms: 420 }} />);
    expect(getByText("LIVE nemotron 420ms")).toBeInTheDocument();
  });

  it("DEMO badge is muted and labeled cached", () => {
    const { getByText } = render(<ProvenanceBadge prov={DEMO} />);
    expect(getByText(/DEMO/)).toBeInTheDocument();
    expect(getByText(/cached/)).toBeInTheDocument();
  });

  it("fails soft when provenance is absent", () => {
    const { getByText } = render(<ProvenanceBadge prov={null} />);
    expect(getByText("no reasoning")).toBeInTheDocument();
  });
});
