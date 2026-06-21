/** Render-smoke for the STR shell: opens on Explore, Story is secondary. */

import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect } from "vitest";
import { StrView } from "./StrView";

vi.mock("../../lib/api", () => ({
  apiFetch: vi.fn().mockResolvedValue(null),
  apiPost: vi.fn().mockResolvedValue(null),
}));
vi.mock("./strApi", () => ({ postAeoAudit: vi.fn().mockResolvedValue(null) }));
vi.mock("react-force-graph-2d", () => ({ default: () => null }));

describe("StrView", () => {
  it("opens on the explorer with the act tabs by default", async () => {
    const { findByText } = render(<StrView />);
    expect(await findByText("Short-term rental operations, calm and governed.")).toBeInTheDocument();
    expect(await findByText("Owner")).toBeInTheDocument();
    expect(await findByText("Stack")).toBeInTheDocument();
  });

  it("reveals the story when Story is selected", async () => {
    const { findByText, getByText } = render(<StrView />);
    await userEvent.click(getByText("Story"));
    expect(await findByText(/One beach cottage in Oceanside/)).toBeInTheDocument();
  });

  it("shows the legacy link when onLegacy is provided", async () => {
    const onLegacy = vi.fn();
    const { findByText } = render(<StrView onLegacy={onLegacy} />);
    const link = await findByText("Legacy demos");
    await userEvent.click(link);
    expect(onLegacy).toHaveBeenCalledOnce();
  });
});
