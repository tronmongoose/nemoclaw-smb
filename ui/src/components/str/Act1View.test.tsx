/** Render-smoke tests for Act1View (Owner fee reconciliation).
 * Asserts: realistic report renders the $84 catch, the NHI governance, and the
 * signed payment; empty/offline falls soft; no raw object rendered as a child.
 * New: nhi_id present, full Ed25519 audit_hash rendered in mono.
 */

import { render } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { Act1View } from "./Act1View";
import { LiveProvider } from "./LiveContext";
import type { StrReconciliationReport } from "../../types";

vi.mock("../../lib/api", () => ({
  apiFetch: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiFetch } from "../../lib/api";
const mockApiFetch = vi.mocked(apiFetch);

const REPORT: StrReconciliationReport = {
  property_id: "prop-001",
  month: "2026-06",
  summary: {
    property_id: "prop-001",
    month: "2026-06",
    revenue_cents: 420000,
    contract_pct: 0.2,
    charged_pct: 0.22,
    line_items: { contracted_fee_cents: 84000, charged_fee_cents: 92400, fee_delta_cents: 8400 },
  },
  anomaly: {
    is_anomaly: true,
    expected_fee_cents: 84000,
    charged_fee_cents: 92400,
    overcharge_cents: 8400,
    reason: "Fee overcharge detected: contract 20.0% vs charged 22.0% on $4200.00 revenue.",
    model_used: "nvidia/nemotron-3-ultra-550b-a55b[demo-cached]",
    reasoning_trace: "[DEMO cached trace] Delta: $84.00. Conclusion: overcharge detected.",
    reasoning_provenance: {
      mode: "demo",
      model: "nvidia/nemotron-3-ultra-550b-a55b[demo-cached]",
      latency_ms: 0,
      source: "cached",
    },
  },
  payment: {
    payment_id: "pi_test_2147a457a92dbe27",
    amount_cents: 84000,
    status: "succeeded",
    audit_hash: "49bdd14131390566feeefd5b217f4cd313829018e85faed88cabde78e9016074",
    held_for_approval: false,
    request_id: "",
  },
  audit_ok: true,
  audit_detail: "chain ok (1352 entries)",
  nhi_id: "nhi-str-owner-agent-1781999009",
};

function renderAct1() {
  return render(
    <LiveProvider>
      <Act1View />
    </LiveProvider>,
  );
}

describe("Act1View", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders without throw on the realistic report", () => {
    mockApiFetch.mockResolvedValue(REPORT);
    expect(() => renderAct1()).not.toThrow();
  });

  it("surfaces the $84 overcharge catch after data loads", async () => {
    mockApiFetch.mockResolvedValue(REPORT);
    const { findByText, findAllByText } = renderAct1();
    expect(await findByText("Overcharge caught")).toBeInTheDocument();
    // $84 appears as the hero Stat and in the ledger table
    expect((await findAllByText("$84")).length).toBeGreaterThan(0);
  });

  it("shows the ConductorOne NHI id and decision source", async () => {
    mockApiFetch.mockResolvedValue(REPORT);
    const { findByText } = renderAct1();
    expect(await findByText("nhi-str-owner-agent-1781999009")).toBeInTheDocument();
    expect(await findByText("baton-carryall")).toBeInTheDocument();
  });

  it("shows the signed payment, full audit hash, and audit chain status", async () => {
    mockApiFetch.mockResolvedValue(REPORT);
    const { findByText } = renderAct1();
    expect(await findByText("pi_test_2147a457a92dbe27")).toBeInTheDocument();
    // Full Ed25519 receipt hash - no truncation
    expect(
      await findByText("49bdd14131390566feeefd5b217f4cd313829018e85faed88cabde78e9016074"),
    ).toBeInTheDocument();
    expect(await findByText("CHAIN OK")).toBeInTheDocument();
  });

  it("renders the REQUIRE_APPROVAL hold with an Approve button when held", async () => {
    const held: StrReconciliationReport = {
      ...REPORT,
      payment: {
        payment_id: "",
        amount_cents: 84000,
        status: "held_for_approval",
        audit_hash: "",
        held_for_approval: true,
        request_id: "req-abc",
      },
    };
    mockApiFetch.mockResolvedValue(held);
    const { findByText } = renderAct1();
    expect(await findByText(/Approve correction/)).toBeInTheDocument();
  });

  it("does not render a raw object as a child", async () => {
    mockApiFetch.mockResolvedValue(REPORT);
    const { container, findByText } = renderAct1();
    await findByText("Overcharge caught");
    expect(container.textContent).not.toContain("[object Object]");
  });

  it("surfaces the muted DEMO cached badge on a demo-mode report", async () => {
    mockApiFetch.mockResolvedValue(REPORT);
    const { findByText } = renderAct1();
    expect(await findByText(/DEMO nemotron cached/)).toBeInTheDocument();
  });

  it("surfaces the LIVE model+latency badge when the report carries live provenance", async () => {
    const liveReport: StrReconciliationReport = {
      ...REPORT,
      anomaly: {
        ...REPORT.anomaly,
        reasoning_provenance: {
          mode: "live",
          model: "nvidia/nemotron-3-ultra-550b-a55b",
          latency_ms: 41000,
          source: "nemotron",
        },
      },
    };
    mockApiFetch.mockResolvedValue(liveReport);
    const { findByText } = renderAct1();
    expect(await findByText("LIVE nemotron 41s")).toBeInTheDocument();
  });

  it("falls soft to empty state when API returns null (offline)", async () => {
    mockApiFetch.mockResolvedValue(null);
    const { findByText } = renderAct1();
    expect(await findByText("No data")).toBeInTheDocument();
  });
});
