/** Render-smoke tests for Act2View (Property Management).
 * Asserts: realistic payouts/invoices/portfolio render; checkout button issues
 * a card showing NO PAN; empty/offline falls soft.
 */

import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { Act2View } from "./Act2View";
import { LiveProvider } from "./LiveContext";
import type { StrCleanerCard } from "../../types";

vi.mock("../../lib/api", () => ({
  apiFetch: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiFetch, apiPost } from "../../lib/api";
const mockApiFetch = vi.mocked(apiFetch);
const mockApiPost = vi.mocked(apiPost);

const PAYOUTS = {
  month: "2026-06",
  records: [
    { crew_id: "crew-001", crew_name: "Maria S.", amount_cents: 8500, month: "2026-06", transfer_id: "tr_a", status: "paid", backend: "mock" },
    { crew_id: "crew-003", crew_name: "Falcon Maintenance", amount_cents: 15000, month: "2026-06", transfer_id: "tr_b", status: "paid", backend: "mock" },
  ],
  total_cents: 23500,
};

const INVOICES = {
  month: "2026-06",
  invoices: [
    {
      owner_id: "owner-001",
      month: "2026-06",
      invoice_id: "inv_b1bcd729bc501c6c",
      line_items: [
        { property_id: "prop-001", property_name: "Sweet Clementine by the Sea", revenue_cents: 420000, fee_pct: 0.205, fee_cents: 86100, description: "20% mgmt + 0.5% platform" },
      ],
      total_revenue_cents: 420000,
      total_fee_cents: 86100,
      backend: "mock",
    },
  ],
};

const PORTFOLIO = {
  property_count: 5,
  owner_count: 3,
  total_monthly_revenue_cents: 1460000,
  property_ids: ["prop-001", "prop-002", "prop-003", "prop-004", "prop-005"],
  owner_ids: ["owner-001", "owner-002", "owner-003"],
  properties_by_owner: {},
};

const CARD: StrCleanerCard = {
  card_token: "tok_ic_43c23b759b03becb",
  card_id: "ic_43c23b759b03becb",
  job_id: "job-prop-001-2026-06-15",
  property_id: "prop-001",
  cleaner_id: "crew-001",
  amount_cap_cents: 7500,
  mcc_list: ["7349", "5251"],
  expiry_utc: "2026-06-20T23:59:59+00:00",
  backend: "mock",
};

// Route each useFetch path to the right fixture.
function routeFetch(path: string): unknown {
  if (path.includes("/payouts/")) return PAYOUTS;
  if (path.includes("/invoices/")) return INVOICES;
  if (path.includes("/portfolio")) return PORTFOLIO;
  return null;
}

function renderAct2() {
  return render(
    <LiveProvider>
      <Act2View />
    </LiveProvider>,
  );
}

describe("Act2View", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders payouts, invoices, and portfolio from realistic fixtures", async () => {
    mockApiFetch.mockImplementation((p: string) => Promise.resolve(routeFetch(p)));
    const { findByText, findAllByText } = renderAct2();
    expect(await findByText("Maria S.")).toBeInTheDocument();
    // appears in both the invoice line item and the portfolio graph's entity list
    expect((await findAllByText("Sweet Clementine by the Sea")).length).toBeGreaterThan(0);
    // portfolio monthly revenue formatted to USD
    expect(await findByText("$14,600")).toBeInTheDocument();
  });

  it("checkout button issues a card and shows NO PAN + $75 cap", async () => {
    mockApiFetch.mockImplementation((p: string) => Promise.resolve(routeFetch(p)));
    mockApiPost.mockResolvedValue(CARD);
    const { findByText, getByText } = renderAct2();
    await userEvent.click(getByText("Trigger checkout"));
    expect(await findByText("NO PAN")).toBeInTheDocument();
    expect(await findByText("tok_ic_43c23b759b03becb")).toBeInTheDocument();
    expect(await findByText("$75")).toBeInTheDocument();
  });

  it("does not render a raw object as a child", async () => {
    mockApiFetch.mockImplementation((p: string) => Promise.resolve(routeFetch(p)));
    const { container, findByText } = renderAct2();
    await findByText("Maria S.");
    expect(container.textContent).not.toContain("[object Object]");
  });

  it("falls soft to empty states when API is offline", async () => {
    mockApiFetch.mockResolvedValue(null);
    const { findAllByText } = renderAct2();
    const empties = await findAllByText("No data");
    expect(empties.length).toBeGreaterThan(0);
  });
});
