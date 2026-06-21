/** Render-smoke tests for Act3View (Platform earn server).
 * Asserts: AEO audit renders the computed score, the dog-only CRITICAL flag,
 * the optimized opening, and JSON-LD; pricing + metrics render; empty/offline
 * falls soft.
 */

import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { Act3View } from "./Act3View";
import { LiveProvider } from "./LiveContext";
import type { StrAeoResponse, StrMetrics, StrPriceResponse } from "../../types";

vi.mock("../../lib/api", () => ({
  apiFetch: vi.fn(),
  apiPost: vi.fn(),
}));

vi.mock("./strApi", () => ({
  postAeoAudit: vi.fn(),
}));

import { apiFetch, apiPost } from "../../lib/api";
import { postAeoAudit } from "./strApi";
const mockApiFetch = vi.mocked(apiFetch);
const mockApiPost = vi.mocked(apiPost);
const mockPostAeo = vi.mocked(postAeoAudit);

const AEO: StrAeoResponse = {
  service: "aeo-audit",
  amount_cents: 100,
  result: {
    overall_score: 48,
    dimension_scores: { structure_completeness: 8, agent_parseability: 12, description_quality: 15, conflict_free: 13 },
    optimized_opening:
      "2BR/1BA beach cottage, Oceanside CA. 6 guests max. Pet-friendly (dogs only, max 2, $30/night/pet).",
    reasoning_trace: "Score 48/100.",
  },
  earn_event: { chain_hash: "cd22b3", seq: 6, timestamp: "2026-06-20T23:47:36+00:00" },
  c1_authorized: true,
};

const PRICE: StrPriceResponse = {
  service: "price",
  property_id: "prop-001",
  amount_cents: 25,
  recommendation: {
    recommended_rate: 345.09,
    confidence: "high",
    reasoning: "Base $200. Season=peak. Recommended $345.",
    suggested_title_tweak: "Book now",
    valid_for_hours: 12,
  },
  earn_event: { chain_hash: "0d4fa8", seq: 5, timestamp: "2026-06-20T23:47:31+00:00" },
  c1_authorized: true,
};

const METRICS: StrMetrics = {
  calls_served: 2,
  revenue_earned_cents: 125,
  revenue_earned_dollars: 1.25,
  properties_optimized: 1,
  property_ids: ["prop-001"],
};

function renderAct3() {
  return render(
    <LiveProvider>
      <Act3View />
    </LiveProvider>,
  );
}

describe("Act3View", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders without throw and shows metrics from the realistic fixture", async () => {
    mockApiFetch.mockResolvedValue(METRICS);
    const { findByText } = renderAct3();
    // metrics revenue formatted to USD
    expect(await findByText("$1")).toBeInTheDocument();
  });

  it("AEO audit shows computed score, dog-only CRITICAL flag, opening, and JSON-LD", async () => {
    mockApiFetch.mockResolvedValue(METRICS);
    mockPostAeo.mockResolvedValue(AEO);
    const { findByText, getByText } = renderAct3();
    await userEvent.click(getByText(/Run AEO audit/));
    expect(await findByText("48/100")).toBeInTheDocument();
    expect(await findByText(/CRITICAL pet_species_conflict/)).toBeInTheDocument();
    expect(await findByText(/dogs only/)).toBeInTheDocument();
    // JSON-LD pre block carries the schema.org type
    expect(await findByText(/LodgingBusiness/)).toBeInTheDocument();
  });

  it("pricing button renders the recommended rate", async () => {
    mockApiFetch.mockResolvedValue(METRICS);
    mockApiPost.mockResolvedValue(PRICE);
    const { findByText, getByText } = renderAct3();
    await userEvent.click(getByText(/Run pricing/));
    expect(await findByText("$345")).toBeInTheDocument();
  });

  it("does not render a raw object as a child", async () => {
    mockApiFetch.mockResolvedValue(METRICS);
    const { container, findByText } = renderAct3();
    await findByText("$1");
    expect(container.textContent).not.toContain("[object Object]");
  });

  it("falls soft to empty states when API is offline", async () => {
    mockApiFetch.mockResolvedValue(null);
    mockApiPost.mockResolvedValue(null);
    mockPostAeo.mockResolvedValue(null);
    const { findAllByText } = renderAct3();
    const empties = await findAllByText("No data");
    expect(empties.length).toBeGreaterThan(0);
  });
});
