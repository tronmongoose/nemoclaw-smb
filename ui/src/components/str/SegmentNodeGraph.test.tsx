/** SegmentNodeGraph tests: asserts the accessible text list renders correct entity names.
 * Canvas (ForceGraph2D) is mocked -- jsdom has no canvas APIs.
 */

import { render, screen } from "@testing-library/react";
import { vi, describe, it, expect } from "vitest";
import { SegmentNodeGraph } from "./SegmentNodeGraph";

vi.mock("react-force-graph-2d", () => ({ default: () => null }));

describe("SegmentNodeGraph", () => {
  it("firm segment: renders Coastline PM and at least one property name", () => {
    render(<SegmentNodeGraph segment="firm" />);
    expect(screen.getByText("Coastline PM")).toBeInTheDocument();
    expect(screen.getByText("Sweet Clementine by the Sea")).toBeInTheDocument();
  });

  it("owner segment: renders Sweet Clementine by the Sea", () => {
    render(<SegmentNodeGraph segment="owner" />);
    expect(screen.getByText("Sweet Clementine by the Sea")).toBeInTheDocument();
  });

  it("agent segment: renders NemoClaw Agent as the platform root", () => {
    render(<SegmentNodeGraph segment="agent" />);
    expect(screen.getByText("NemoClaw Agent")).toBeInTheDocument();
  });
});
