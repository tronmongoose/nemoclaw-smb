/** Render-smoke tests for SavingsPanel.
 * Asserts: renders realistic fixture, handles null summary (offline), no object-as-child.
 */

import { render } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { SavingsPanel } from "./SavingsPanel";
import type { SavingsSummary, AlternativesResponse } from "../types";

vi.mock("../lib/api", () => ({
  apiFetch: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiFetch } from "../lib/api";
const mockApiFetch = vi.mocked(apiFetch);

const summaryFixture: SavingsSummary = {
  total_spend: 48000.0,
  monthly_savings: 1200.0,
  annual_savings: 14400.0,
  nemoclaw_fee: 1440.0,
  fee_rate: 0.1,
  currency: "USD",
};

const altsFixture: AlternativesResponse = {
  current: { vendor: "Adobe Creative Cloud", amount: 599.88 },
  ranked: [
    {
      vendor: "Canva Pro",
      amount: 119.99,
      monthly_savings: 479.89,
      annual_savings: 5758.68,
      rank: 1,
    },
    {
      vendor: "Figma",
      amount: 150.0,
      monthly_savings: 449.88,
      annual_savings: 5398.56,
      rank: 2,
    },
  ],
};

describe("SavingsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without throw with realistic fixture", () => {
    mockApiFetch
      .mockResolvedValueOnce(summaryFixture)
      .mockResolvedValueOnce(altsFixture);
    expect(() => render(<SavingsPanel />)).not.toThrow();
  });

  it("renders savings figures after data loads", async () => {
    mockApiFetch
      .mockResolvedValueOnce(summaryFixture)
      .mockResolvedValueOnce(altsFixture);
    const { findByText } = render(<SavingsPanel />);
    // formatUSD uses 0 fraction digits
    expect(await findByText("$48,000")).toBeInTheDocument();
    expect(await findByText("$14,400")).toBeInTheDocument();
  });

  it("renders alternative vendors after data loads", async () => {
    mockApiFetch
      .mockResolvedValueOnce(summaryFixture)
      .mockResolvedValueOnce(altsFixture);
    const { findByText } = render(<SavingsPanel />);
    expect(await findByText("Canva Pro")).toBeInTheDocument();
    expect(await findByText("Figma")).toBeInTheDocument();
  });

  it("does not render raw object as child", async () => {
    mockApiFetch
      .mockResolvedValueOnce(summaryFixture)
      .mockResolvedValueOnce(altsFixture);
    const { container, findByText } = render(<SavingsPanel />);
    await findByText("$48,000");
    expect(container.textContent).not.toContain("[object Object]");
  });

  it("shows unavailable state when summary is null (offline)", async () => {
    mockApiFetch.mockResolvedValue(null);
    const { findByText } = render(<SavingsPanel />);
    expect(await findByText("Savings data unavailable")).toBeInTheDocument();
  });
});
