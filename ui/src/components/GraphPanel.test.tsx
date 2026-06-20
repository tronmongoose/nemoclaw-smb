/** Render-smoke tests for GraphPanel and KnowledgeGraph.
 * ForceGraph2D is a canvas component; mock it so jsdom can render the wrapper logic.
 * Asserts: renders without throw, handles null data (offline), no object-as-child.
 */

import { render } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

// Mock ForceGraph2D before importing the component — canvas is not in jsdom.
vi.mock("react-force-graph-2d", () => ({
  default: () => <canvas data-testid="force-graph" />,
}));


vi.mock("../lib/api", () => ({
  apiFetch: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiFetch } from "../lib/api";
import { GraphPanel } from "./GraphPanel";
import { KnowledgeGraph } from "./KnowledgeGraph";
import type { GraphResponse } from "../types";

const mockApiFetch = vi.mocked(apiFetch);

const graphFixture: GraphResponse = {
  nodes: [
    { id: "self", label: "Acme Inc", type: "self", category: "self" },
    { id: "vendor-1", label: "Adobe Creative Cloud", type: "vendor", category: "software" },
    { id: "vendor-2", label: "AWS", type: "vendor", category: "infrastructure" },
  ],
  edges: [
    {
      source: "self",
      target: "vendor-1",
      amount: 599.88,
      date: "2024-06-01",
      category: "software",
      anomaly_flag: false,
    },
    {
      source: "self",
      target: "vendor-2",
      amount: 12000.0,
      date: "2024-06-01",
      category: "infrastructure",
      anomaly_flag: true,
    },
  ],
};

describe("KnowledgeGraph", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without throw with realistic graph fixture", () => {
    mockApiFetch.mockResolvedValue(graphFixture);
    expect(() => render(<KnowledgeGraph width={800} height={500} />)).not.toThrow();
  });

  it("does not render raw object as child", async () => {
    mockApiFetch.mockResolvedValue(graphFixture);
    const { container } = render(<KnowledgeGraph width={800} height={500} />);
    expect(container.textContent).not.toContain("[object Object]");
  });

  it("shows offline message when API returns null", async () => {
    mockApiFetch.mockResolvedValue(null);
    const { findByText } = render(<KnowledgeGraph width={800} height={500} />);
    expect(await findByText("Graph unavailable — API offline")).toBeInTheDocument();
  });
});

describe("GraphPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without throw", () => {
    mockApiFetch.mockResolvedValue(graphFixture);
    expect(() => render(<GraphPanel />)).not.toThrow();
  });

  it("does not render raw object as child", () => {
    mockApiFetch.mockResolvedValue(graphFixture);
    const { container } = render(<GraphPanel />);
    expect(container.textContent).not.toContain("[object Object]");
  });
});
