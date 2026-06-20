/** Render-smoke tests for OpsHeadlineBand.
 * Covers: realistic data (anomaly + pending + savings), empty/all-clear state,
 * and full null (all endpoints down) — should render nothing.
 */

import { render } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { OpsHeadlineBand } from "./OpsHeadlineBand";
import type { AnomalyRecord, ApprovalItem, SavingsSummary } from "../types";

vi.mock("../lib/api", () => ({
  apiFetch: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiFetch } from "../lib/api";
const mockApiFetch = vi.mocked(apiFetch);

const anomalyFixture: AnomalyRecord[] = [
  {
    vendor: "Adobe Creative Cloud",
    current_amount: 340,
    baseline_mean: 277,
    z_score: 2.8,
    pct_change: 22.7,
    is_anomaly: true,
    reason: "22.7% above 6-month mean",
  },
];

const pendingFixture: ApprovalItem[] = [
  {
    id: "apr-001",
    action: "approve_payment",
    vendor: "Adobe Creative Cloud",
    amount: 340,
    context: { anomaly_reason: "22.7% above baseline" },
    created_at: "2024-06-01T10:00:00Z",
    expires_at: "2024-06-02T10:00:00Z",
    status: "pending",
  },
];

const savingsFixture: SavingsSummary = {
  total_spend: 48000,
  monthly_savings: 332,
  annual_savings: 3984,
  nemoclaw_fee: 240,
  fee_rate: 0.005,
  currency: "USD",
};

describe("OpsHeadlineBand", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without throw with realistic fixture data", () => {
    mockApiFetch
      .mockResolvedValueOnce(anomalyFixture)
      .mockResolvedValueOnce(pendingFixture)
      .mockResolvedValueOnce(savingsFixture);
    expect(() => render(<OpsHeadlineBand />)).not.toThrow();
  });

  it("shows anomaly vendor and pending count after data loads", async () => {
    mockApiFetch
      .mockResolvedValueOnce(anomalyFixture)
      .mockResolvedValueOnce(pendingFixture)
      .mockResolvedValueOnce(savingsFixture);
    const { findByText, container } = render(<OpsHeadlineBand />);
    expect(await findByText(/1 anomaly flagged/)).toBeInTheDocument();
    expect(await findByText(/Adobe Creative Cloud/)).toBeInTheDocument();
    // Pending count and label span two inline elements; check combined text.
    expect(container.textContent).toMatch(/1\s+approval.*pending/);
  });

  it("shows savings figure when present", async () => {
    mockApiFetch
      .mockResolvedValueOnce(anomalyFixture)
      .mockResolvedValueOnce(pendingFixture)
      .mockResolvedValueOnce(savingsFixture);
    const { findByText } = render(<OpsHeadlineBand />);
    expect(await findByText(/\$3,984\/yr savings identified/)).toBeInTheDocument();
  });

  it("renders nothing when all endpoints return null (API down)", () => {
    mockApiFetch.mockResolvedValue(null);
    const { container } = render(<OpsHeadlineBand />);
    // Initial render: all data null -> component returns null -> empty container
    expect(container.firstChild).toBeNull();
  });

  it("shows all-clear state when anomalies empty, no pending, no savings", async () => {
    mockApiFetch
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce(null);
    const { findByText } = render(<OpsHeadlineBand />);
    expect(await findByText(/All clear/)).toBeInTheDocument();
  });

  it("does not render raw object as child", async () => {
    mockApiFetch
      .mockResolvedValueOnce(anomalyFixture)
      .mockResolvedValueOnce(pendingFixture)
      .mockResolvedValueOnce(savingsFixture);
    const { container, findByText } = render(<OpsHeadlineBand />);
    await findByText(/Adobe Creative Cloud/);
    expect(container.textContent).not.toContain("[object Object]");
  });
});
