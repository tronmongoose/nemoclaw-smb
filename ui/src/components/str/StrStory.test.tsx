/** Render-smoke for the guided narrative: intro renders, Begin advances to Act I. */

import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect } from "vitest";
import { StrStory } from "./StrStory";
import { LiveProvider } from "./LiveContext";

vi.mock("../../lib/api", () => ({
  apiFetch: vi.fn().mockResolvedValue(null),
  apiPost: vi.fn().mockResolvedValue(null),
}));
vi.mock("./strApi", () => ({ postAeoAudit: vi.fn().mockResolvedValue(null) }));

function renderStory() {
  return render(
    <LiveProvider>
      <StrStory />
    </LiveProvider>,
  );
}

describe("StrStory", () => {
  it("opens on the intro with the property name", async () => {
    const { findByText } = renderStory();
    expect(await findByText("Sweet Clementine by the Sea")).toBeInTheDocument();
  });

  it("advances to Act I when Begin is clicked", async () => {
    const { findByText, getByText } = renderStory();
    await userEvent.click(getByText("Begin"));
    expect(await findByText("The Owner")).toBeInTheDocument();
  });
});
