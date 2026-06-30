/** Render-smoke for the stall queue: a stalled handoff renders with the Hermes nudge + badge. */

import { render } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { StallQueuePanel } from "./StallQueuePanel";
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
      count: 1,
      stalls: [
        {
          handoff_id: "prop-001:inspect",
          property_id: "prop-001",
          property_name: "Sweet Clementine by the Sea",
          stage: "inspect",
          from_actor: "cleaner",
          to_actor: "inspector",
          assigned_to: "Inspector (unassigned)",
          reason: "no inspector assigned 3h after cleaning finished",
          hours_stalled: 3.2,
          nudge: {
            stalled_actor: "inspector",
            nudge_message: "Hi Maria, please confirm an inspector for the next hour.",
            next_action: "assign_inspector_then_reopen_listing",
            reasoning_provenance: PROV,
          },
          reasoning_provenance: PROV,
        },
      ],
    }),
    apiPost: vi.fn().mockResolvedValue({ ok: true }),
  };
});

function renderPanel() {
  return render(
    <LiveProvider>
      <StallQueuePanel />
    </LiveProvider>,
  );
}

describe("StallQueuePanel", () => {
  it("renders the stalled handoff with the Hermes nudge and a provenance badge", async () => {
    const { findByText, getByText } = renderPanel();
    expect(await findByText(/please confirm an inspector/)).toBeInTheDocument();
    expect(getByText(/cleaner/)).toBeInTheDocument();
    expect(getByText(/hermes/)).toBeInTheDocument();
    expect(getByText("Nudge")).toBeInTheDocument();
  });
});
