/** Render-smoke tests for ApprovalQueue.
 * Asserts: no throw on render, no raw object rendered as child,
 * handles null/absent context fields, handles empty pending list.
 */

import { render } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { ApprovalQueue } from "./ApprovalQueue";
import type { ApprovalItem } from "../types";

// --- mock apiFetch so tests are fully offline ---
vi.mock("../lib/api", () => ({
  apiFetch: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiFetch } from "../lib/api";
const mockApiFetch = vi.mocked(apiFetch);

// Realistic fixture: context is a full object (the exact bug that shipped)
const itemWithObjectContext: ApprovalItem = {
  id: "apr-001",
  action: "approve_payment",
  vendor: "Acme Corp",
  amount: 12500.0,
  context: {
    invoice_id: "INV-2024-001",
    threshold: 10000,
    policy_reason: "Exceeds single-payment threshold",
    anomaly_reason: "3.2 SD above 6-month baseline",
  },
  created_at: "2024-06-01T10:00:00Z",
  expires_at: "2024-06-02T10:00:00Z",
  status: "pending",
};

// Null/absent fields variant
const itemWithNullContext: ApprovalItem = {
  id: "apr-002",
  action: "approve_payment",
  vendor: "Widget LLC",
  amount: 500.0,
  context: {
    invoice_id: undefined,
    threshold: undefined,
    policy_reason: null as unknown as string,
    anomaly_reason: null as unknown as string,
  },
  created_at: "2024-06-01T11:00:00Z",
  expires_at: "2024-06-02T11:00:00Z",
  status: "pending",
};

describe("ApprovalQueue", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without throw when context is a full object (regression: object-as-child bug)", () => {
    mockApiFetch.mockResolvedValue([itemWithObjectContext]);
    // Synchronous initial render uses data=null (usePoll hasn't resolved yet).
    // The empty-state branch renders — that's fine; the regression is in the card render.
    expect(() => render(<ApprovalQueue />)).not.toThrow();
  });

  it("renders the vendor name and amount from an object-context item after data loads", async () => {
    mockApiFetch.mockResolvedValue([itemWithObjectContext]);
    const { findByText } = render(<ApprovalQueue />);
    // After usePoll resolves the mock, cards should render
    expect(await findByText("Acme Corp")).toBeInTheDocument();
    // formatUSD uses 0 fraction digits
    expect(await findByText("$12,500")).toBeInTheDocument();
  });

  it("does NOT render the raw context object as a React child", async () => {
    mockApiFetch.mockResolvedValue([itemWithObjectContext]);
    const { container, findByText } = render(<ApprovalQueue />);
    await findByText("Acme Corp");
    // [object Object] in the DOM is the canary for object-as-child
    expect(container.textContent).not.toContain("[object Object]");
  });

  it("renders without throw when context fields are null/absent", async () => {
    mockApiFetch.mockResolvedValue([itemWithNullContext]);
    const { findAllByText } = render(<ApprovalQueue />);
    // findAllByText to handle single or multiple matches safely
    const matches = await findAllByText("Widget LLC");
    expect(matches.length).toBeGreaterThan(0);
  });

  it("renders the anomaly_reason string when present", async () => {
    mockApiFetch.mockResolvedValue([itemWithObjectContext]);
    const { findByText } = render(<ApprovalQueue />);
    await findByText("3.2 SD above 6-month baseline");
  });

  it("falls back to policy_reason when anomaly_reason is absent", async () => {
    const item: ApprovalItem = {
      ...itemWithObjectContext,
      id: "apr-003",
      context: {
        ...itemWithObjectContext.context,
        anomaly_reason: undefined,
        policy_reason: "Policy cap exceeded",
      },
    };
    mockApiFetch.mockResolvedValue([item]);
    const { findByText } = render(<ApprovalQueue />);
    await findByText("Policy cap exceeded");
  });

  it("shows empty state when API returns empty array", async () => {
    mockApiFetch.mockResolvedValue([]);
    const { findByText } = render(<ApprovalQueue />);
    expect(await findByText("No approvals pending")).toBeInTheDocument();
  });

  it("shows empty state when API returns null (offline)", async () => {
    mockApiFetch.mockResolvedValue(null);
    const { findByText } = render(<ApprovalQueue />);
    expect(await findByText("No approvals pending")).toBeInTheDocument();
  });
});
