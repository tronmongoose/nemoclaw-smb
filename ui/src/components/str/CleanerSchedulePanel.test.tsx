/** Render-smoke for the cleaner schedule: a clean stall renders the Hermes reassign + Assign button. */

import { render } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { CleanerSchedulePanel } from "./CleanerSchedulePanel";
import { LiveProvider } from "./LiveContext";

vi.mock("../../lib/api", () => {
  const PROV = {
    mode: "demo",
    model: "nousresearch/hermes-4-70b[demo-cached]",
    latency_ms: 0,
    source: "hermes",
  };
  const MARIA = { id: "crew-001", name: "Maria S.", free_from: "2026-06-15T13:00:00+00:00", available: true };
  const JAMES = { id: "crew-002", name: "James T.", free_from: "2026-06-15T20:00:00+00:00", available: false };
  return {
    apiFetch: vi.fn().mockResolvedValue({
      count: 1,
      stalls: [
        {
          handoff_id: "prop-004:clean",
          property_id: "prop-004",
          property_name: "Sunset Ridge Cabin",
          stage: "clean",
          assigned_to: "James T.",
          hours_stalled: 5.0,
          reason: "cleaner not started 5h after checkout",
          assigned_cleaner: JAMES,
          suggested_cleaner: MARIA,
          crew_availability: [MARIA, JAMES],
          schedule: {
            suggested_cleaner: "Maria S.",
            scheduled_start: "today, 2:30pm (next free 90-min window)",
            reason: "Sunset Ridge Cabin cleaning has sat 5h with James T., who is booked. Reassign to Maria S.",
            card_action: "pre-authorize $75 single-use card (MCC cleaning, end-of-day expiry)",
            reasoning_provenance: PROV,
          },
          reasoning_provenance: PROV,
        },
      ],
    }),
    apiPost: vi.fn().mockResolvedValue({ ok: true, card_token: "tok_ic_demo", cleaner: "Maria S." }),
  };
});

function renderPanel() {
  return render(
    <LiveProvider>
      <CleanerSchedulePanel />
    </LiveProvider>,
  );
}

describe("CleanerSchedulePanel", () => {
  it("renders the Hermes reassign suggestion with an Assign action", async () => {
    const { findByText, getByText } = renderPanel();
    expect(await findByText(/Reassign to Maria S\./)).toBeInTheDocument();
    expect(getByText("Assign + issue card")).toBeInTheDocument();
    expect(getByText(/hermes/)).toBeInTheDocument();
  });
});
