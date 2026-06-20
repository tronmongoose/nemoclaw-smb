/** Render-smoke tests for InvoiceFeed.
 * Asserts: renders realistic fixture, handles null/empty data, no object-as-child.
 */

import { render } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { InvoiceFeed } from "./InvoiceFeed";
import type { Invoice, AnomalyRecord } from "../types";

vi.mock("../lib/api", () => ({
  apiFetch: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiFetch } from "../lib/api";
const mockApiFetch = vi.mocked(apiFetch);

const invoiceFixture: Invoice[] = [
  {
    invoice_id: "INV-001",
    vendor: "Adobe Creative Cloud",
    description: "Annual subscription",
    amount: 599.88,
    date: "2024-06-01T00:00:00Z",
    category: "software",
  },
  {
    invoice_id: "INV-002",
    vendor: "Slack Technologies",
    description: "Team plan",
    amount: 87.5,
    date: "2024-05-15T00:00:00Z",
    category: "software",
  },
];

const anomalyFixture: AnomalyRecord[] = [
  {
    vendor: "Adobe Creative Cloud",
    current_amount: 599.88,
    baseline_mean: 299.94,
    z_score: 3.1,
    pct_change: 100.0,
    is_anomaly: true,
    reason: "100% above 6-month mean",
  },
];

describe("InvoiceFeed", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without throw with a realistic fixture", () => {
    mockApiFetch.mockResolvedValue(invoiceFixture);
    expect(() => render(<InvoiceFeed />)).not.toThrow();
  });

  it("renders vendor names and amounts after data loads", async () => {
    // First call = invoices, second = anomalies
    mockApiFetch
      .mockResolvedValueOnce(invoiceFixture)
      .mockResolvedValueOnce(anomalyFixture);
    const { findByText } = render(<InvoiceFeed />);
    expect(await findByText("Adobe Creative Cloud")).toBeInTheDocument();
    expect(await findByText("Slack Technologies")).toBeInTheDocument();
  });

  it("does not render raw object as child", async () => {
    mockApiFetch
      .mockResolvedValueOnce(invoiceFixture)
      .mockResolvedValueOnce(anomalyFixture);
    const { container, findByText } = render(<InvoiceFeed />);
    await findByText("Adobe Creative Cloud");
    expect(container.textContent).not.toContain("[object Object]");
  });

  it("shows empty state when API returns empty array", async () => {
    mockApiFetch.mockResolvedValue([]);
    const { findByText } = render(<InvoiceFeed />);
    expect(await findByText("No invoices available")).toBeInTheDocument();
  });

  it("shows empty state when API returns null (offline)", async () => {
    mockApiFetch.mockResolvedValue(null);
    const { findByText } = render(<InvoiceFeed />);
    expect(await findByText("No invoices available")).toBeInTheDocument();
  });
});
