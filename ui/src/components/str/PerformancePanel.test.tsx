/** Render-smoke for the performance panel: an under-performer renders with the Hermes why + badge. */

import { render } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { PerformancePanel } from "./PerformancePanel";
import { LiveProvider } from "./LiveContext";

vi.mock("../../lib/api", () => {
  const PROV = {
    mode: "demo",
    model: "nousresearch/hermes-4-70b[demo-cached]",
    latency_ms: 0,
    source: "hermes",
  };
  return {
    apiFetch: vi.fn().mockResolvedValue({
      count: 2,
      properties: [
        {
          property_id: "prop-003",
          property_name: "Harbor View Suite",
          revenue_cents: 195000,
          portfolio_avg_cents: 292000,
          pct_vs_avg: -0.332,
          status: "under",
          occupancy: 0.41,
          analysis: {
            verdict: "under",
            summary: "Harbor View Suite runs 33% below the portfolio average on 41% occupancy.",
            drivers: ["low occupancy"],
            reasoning_provenance: PROV,
          },
          reasoning_provenance: PROV,
        },
        {
          property_id: "prop-001",
          property_name: "Sweet Clementine by the Sea",
          revenue_cents: 420000,
          portfolio_avg_cents: 292000,
          pct_vs_avg: 0.438,
          status: "over",
          occupancy: 0.82,
          analysis: {
            verdict: "over",
            summary: "Sweet Clementine runs 44% above the portfolio average.",
            drivers: ["high occupancy"],
            reasoning_provenance: PROV,
          },
          reasoning_provenance: PROV,
        },
      ],
    }),
    apiPost: vi.fn().mockResolvedValue(null),
  };
});

function renderPanel() {
  return render(
    <LiveProvider>
      <PerformancePanel />
    </LiveProvider>,
  );
}

describe("PerformancePanel", () => {
  it("flags the under-performer with a Hermes why + provenance badge", async () => {
    const { findByText, getByText, getAllByText } = renderPanel();
    expect(await findByText(/runs 33% below the portfolio average/)).toBeInTheDocument();
    expect(getByText("UNDER")).toBeInTheDocument();
    expect(getByText("Harbor View Suite")).toBeInTheDocument();
    expect(getAllByText(/hermes/).length).toBeGreaterThan(0);
  });
});
