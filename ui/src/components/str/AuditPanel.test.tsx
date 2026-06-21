/** Render-smoke tests for AuditPanel.
 * Asserts: realistic chain renders entries + a green verify badge; a broken
 * chain renders the red fault badge; empty/offline falls soft.
 */

import { render } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { AuditPanel } from "./AuditPanel";
import { LiveProvider } from "./LiveContext";
import type { StrAuditResponse } from "../../types";

vi.mock("../../lib/api", () => ({
  apiFetch: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiFetch } from "../../lib/api";
const mockApiFetch = vi.mocked(apiFetch);

const CHAIN: StrAuditResponse = {
  count: 2,
  entries: [
    { ts: "2026-06-20T23:44:49Z", seq: 0, event: "mpp_earn", service: "price", amount_cents: 25, token_id: "mpp_tok_demo", prev_hash: "0000", entry_hash: "cc89eb8cd5f7d59d" },
    { ts: "2026-06-20T23:44:50Z", seq: 1, event: "mpp_earn", service: "aeo-audit", amount_cents: 100, token_id: "mpp_tok_demo", prev_hash: "cc89", entry_hash: "2dd8c640f860f8dd" },
  ],
  verify: { ok: true, message: "chain ok (7 entries)" },
};

function renderPanel() {
  return render(
    <LiveProvider>
      <AuditPanel />
    </LiveProvider>,
  );
}

describe("AuditPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders chain entries and a green verify badge", async () => {
    mockApiFetch.mockResolvedValue(CHAIN);
    const { findByText, findAllByText } = renderPanel();
    expect(await findByText("CHAIN VERIFIED")).toBeInTheDocument();
    expect((await findAllByText(/earn \/ price/)).length).toBeGreaterThan(0);
  });

  it("renders the red fault badge when verify fails", async () => {
    mockApiFetch.mockResolvedValue({ ...CHAIN, verify: { ok: false, message: "tampered at line 3" } });
    const { findByText } = renderPanel();
    expect(await findByText("CHAIN FAULT")).toBeInTheDocument();
  });

  it("does not render a raw object as a child", async () => {
    mockApiFetch.mockResolvedValue(CHAIN);
    const { container, findByText } = renderPanel();
    await findByText("CHAIN VERIFIED");
    expect(container.textContent).not.toContain("[object Object]");
  });

  it("falls soft to empty state when API is offline", async () => {
    mockApiFetch.mockResolvedValue(null);
    const { findByText } = renderPanel();
    expect(await findByText("No data")).toBeInTheDocument();
  });
});
