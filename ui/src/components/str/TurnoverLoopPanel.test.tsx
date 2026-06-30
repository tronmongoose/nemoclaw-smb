/** Render-smoke for the turnover loop: the four stages render with the stalled property. */

import { render } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { TurnoverLoopPanel } from "./TurnoverLoopPanel";
import { LiveProvider } from "./LiveContext";

vi.mock("../../lib/api", () => ({
  apiFetch: vi.fn().mockResolvedValue({
    properties: [
      {
        property_id: "prop-001",
        property_name: "Sweet Clementine by the Sea",
        current_stage: "inspect",
        overall_status: "stalled",
        stages: [
          { stage: "checkout", role: "guest", status: "done", actor: "Guest party", hours_in_stage: 7 },
          { stage: "clean", role: "cleaner", status: "done", actor: "Maria S.", hours_in_stage: 3.5 },
          { stage: "inspect", role: "inspector", status: "blocked", actor: "Inspector (unassigned)", hours_in_stage: 3.2 },
          { stage: "ready", role: "booking platform", status: "waiting", actor: "Owner agent", hours_in_stage: 3.2 },
        ],
      },
    ],
  }),
  apiPost: vi.fn().mockResolvedValue(null),
}));

function renderPanel() {
  return render(
    <LiveProvider>
      <TurnoverLoopPanel propertyId="prop-001" />
    </LiveProvider>,
  );
}

describe("TurnoverLoopPanel", () => {
  it("renders the property and its four turnover stages", async () => {
    const { findByText, getByText } = renderPanel();
    expect(await findByText("Sweet Clementine by the Sea")).toBeInTheDocument();
    expect(getByText("checkout")).toBeInTheDocument();
    expect(getByText("inspect")).toBeInTheDocument();
    expect(getByText("ready")).toBeInTheDocument();
  });

  it("shows the stalled overall status", async () => {
    const { findByText } = renderPanel();
    expect(await findByText("STALLED")).toBeInTheDocument();
  });
});
