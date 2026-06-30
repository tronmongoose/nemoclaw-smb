/** Render-smoke for the console sidebar: section navigator + status render. */

import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ConsoleSidebar } from "./ConsoleSidebar";
import { LiveProvider } from "./LiveContext";

describe("ConsoleSidebar", () => {
  it("renders the section navigator for the firm segment", () => {
    const { getByText } = render(
      <LiveProvider>
        <ConsoleSidebar segment="firm" />
      </LiveProvider>,
    );
    expect(getByText("Sections")).toBeInTheDocument();
    expect(getByText("Turnover loop")).toBeInTheDocument();
    expect(getByText("Portfolio graph")).toBeInTheDocument();
    expect(getByText("Endpoints")).toBeInTheDocument();
  });
});
