/** Render-smoke tests for tenant components: TenantDashboard, HeadlineBand,
 * LongitudinalSection, SupportingSection, SummaryStrip.
 * Asserts: no throw on render, handles null/empty data, no object-as-child.
 */

import { render } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";

// LineChart from @tremor/react uses SVG; it renders fine in jsdom but needs a stable env.
// No extra mocks needed for Tremor.

vi.mock("../../lib/api", () => ({
  apiFetch: vi.fn(),
  apiPost: vi.fn(),
}));

import { apiFetch } from "../../lib/api";
import { TenantDashboard } from "./TenantDashboard";
import { HeadlineBand } from "./HeadlineBand";
import { LongitudinalSection } from "./LongitudinalSection";
import { SupportingSection } from "./SupportingSection";
import { SummaryStrip } from "./SummaryStrip";
import type {
  TenantAnalysis,
  AnalysisHeadline,
  AnalysisLongitudinal,
  AnalysisByMonth,
  AnalysisTotals,
  AnalysisByCategory,
  AnalysisFinding,
  LongitudinalNetMonth,
} from "../../types";

const mockApiFetch = vi.mocked(apiFetch);

const totalsFixture: AnalysisTotals = {
  income: 120000,
  expense: 85000,
  net: 35000,
  margin_pct: 29.2,
};

const headlinesFixture: AnalysisHeadline[] = [
  {
    title: "Software subscription consolidation opportunity",
    action: "Consolidate 4 overlapping design tools into 1",
    annual_impact: 14400,
    monthly_impact: 1200,
    severity: "high",
    category: "software",
    series: [
      { month: "2024-01", value: 1100 },
      { month: "2024-02", value: 1150 },
      { month: "2024-03", value: 1200 },
    ],
  },
];

const byMonthFixture: AnalysisByMonth[] = [
  { month: "2024-01", income: 38000, expense: 27000, net: 11000 },
  { month: "2024-02", income: 40000, expense: 28000, net: 12000 },
  { month: "2024-03", income: 42000, expense: 30000, net: 12000 },
];

const byCategoryFixture: AnalysisByCategory[] = [
  { category: "software", amount: 24000 },
  { category: "payroll", amount: 45000 },
  { category: "infrastructure", amount: 16000 },
];

const findingsFixture: AnalysisFinding[] = [
  {
    title: "Redundant design tool subscriptions",
    category: "software",
    action: "Cancel Sketch; migrate team to Figma",
    monthly_impact: 120,
    annual_impact: 1440,
    confidence: "high",
    why: "4 active design tools for 2 designers; industry norm is 1",
  },
];

const longitudinalFixture: AnalysisLongitudinal = {
  net_by_month: byMonthFixture.map((m) => ({ month: m.month, net: m.net })),
  by_category_monthly: [
    {
      category: "software",
      series: byMonthFixture.map((m) => ({ month: m.month, value: 8000 })),
    },
  ],
};

const tenantFixture: TenantAnalysis = {
  tenant: "Acme Corp",
  generated_at: "2024-06-01T08:00:00Z",
  pnl: {
    totals: totalsFixture,
    by_month: byMonthFixture,
    expense_by_category: byCategoryFixture,
  },
  headlines: headlinesFixture,
  findings: findingsFixture,
  longitudinal: longitudinalFixture,
};

// --- SummaryStrip ---
describe("SummaryStrip", () => {
  const netByMonth: LongitudinalNetMonth[] = byMonthFixture.map((m) => ({
    month: m.month,
    net: m.net,
  }));

  it("renders without throw with realistic data", () => {
    expect(() =>
      render(
        <SummaryStrip
          tenant="Acme Corp"
          totals={totalsFixture}
          netByMonth={netByMonth}
          generatedAt="2024-06-01T08:00:00Z"
        />
      )
    ).not.toThrow();
  });

  it("renders tenant name and net", async () => {
    const { findByText } = render(
      <SummaryStrip
        tenant="Acme Corp"
        totals={totalsFixture}
        netByMonth={netByMonth}
        generatedAt="2024-06-01T08:00:00Z"
      />
    );
    expect(await findByText("Acme Corp")).toBeInTheDocument();
    // formatUSD uses 0 fraction digits
    expect(await findByText("$35,000")).toBeInTheDocument();
  });

  it("does not render raw object as child", () => {
    const { container } = render(
      <SummaryStrip
        tenant="Acme Corp"
        totals={totalsFixture}
        netByMonth={netByMonth}
        generatedAt="2024-06-01T08:00:00Z"
      />
    );
    expect(container.textContent).not.toContain("[object Object]");
  });
});

// --- HeadlineBand ---
describe("HeadlineBand", () => {
  it("renders without throw with realistic headlines", () => {
    expect(() => render(<HeadlineBand headlines={headlinesFixture} />)).not.toThrow();
  });

  it("renders headline titles and amounts", async () => {
    const { findByText } = render(<HeadlineBand headlines={headlinesFixture} />);
    expect(
      await findByText("Software subscription consolidation opportunity")
    ).toBeInTheDocument();
    // formatUSD uses 0 fraction digits
    expect(await findByText("$14,400")).toBeInTheDocument();
  });

  it("renders nothing when headlines is empty", () => {
    const { container } = render(<HeadlineBand headlines={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("does not render raw object as child", async () => {
    const { container, findByText } = render(<HeadlineBand headlines={headlinesFixture} />);
    await findByText("$14,400");
    expect(container.textContent).not.toContain("[object Object]");
  });
});

// --- LongitudinalSection ---
describe("LongitudinalSection", () => {
  it("renders without throw with realistic data", () => {
    expect(() =>
      render(
        <LongitudinalSection
          longitudinal={longitudinalFixture}
          byMonth={byMonthFixture}
        />
      )
    ).not.toThrow();
  });

  it("renders without throw when longitudinal is empty", () => {
    const empty: AnalysisLongitudinal = { net_by_month: [], by_category_monthly: [] };
    expect(() =>
      render(<LongitudinalSection longitudinal={empty} byMonth={[]} />)
    ).not.toThrow();
  });

  it("does not render raw object as child", () => {
    const { container } = render(
      <LongitudinalSection longitudinal={longitudinalFixture} byMonth={byMonthFixture} />
    );
    expect(container.textContent).not.toContain("[object Object]");
  });
});

// --- SupportingSection ---
describe("SupportingSection", () => {
  it("renders without throw with realistic data", () => {
    expect(() =>
      render(
        <SupportingSection
          totals={totalsFixture}
          byCategory={byCategoryFixture}
          findings={findingsFixture}
        />
      )
    ).not.toThrow();
  });

  it("renders income/expense/net totals", async () => {
    const { findByText } = render(
      <SupportingSection
        totals={totalsFixture}
        byCategory={byCategoryFixture}
        findings={findingsFixture}
      />
    );
    // formatUSD uses 0 fraction digits
    expect(await findByText("$120,000")).toBeInTheDocument();
    expect(await findByText("$85,000")).toBeInTheDocument();
  });

  it("renders finding titles", async () => {
    const { findByText } = render(
      <SupportingSection
        totals={totalsFixture}
        byCategory={byCategoryFixture}
        findings={findingsFixture}
      />
    );
    expect(
      await findByText("Redundant design tool subscriptions")
    ).toBeInTheDocument();
  });

  it("renders without throw when byCategory and findings are empty", () => {
    expect(() =>
      render(
        <SupportingSection totals={totalsFixture} byCategory={[]} findings={[]} />
      )
    ).not.toThrow();
  });

  it("does not render raw object as child", async () => {
    const { container, findByText } = render(
      <SupportingSection
        totals={totalsFixture}
        byCategory={byCategoryFixture}
        findings={findingsFixture}
      />
    );
    await findByText("$120,000");
    expect(container.textContent).not.toContain("[object Object]");
  });
});

// --- TenantDashboard (integration: fetches, renders all sub-components) ---
describe("TenantDashboard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders without throw with full fixture", () => {
    mockApiFetch.mockResolvedValue(tenantFixture);
    expect(() => render(<TenantDashboard />)).not.toThrow();
  });

  it("shows tenant name after data loads", async () => {
    mockApiFetch.mockResolvedValue(tenantFixture);
    const { findByText } = render(<TenantDashboard />);
    expect(await findByText("Acme Corp")).toBeInTheDocument();
  });

  it("shows empty state when API returns null", async () => {
    mockApiFetch.mockResolvedValue(null);
    const { findByText } = render(<TenantDashboard />);
    expect(await findByText("No analysis data")).toBeInTheDocument();
  });

  it("does not render raw object as child", async () => {
    mockApiFetch.mockResolvedValue(tenantFixture);
    const { container, findByText } = render(<TenantDashboard />);
    // Wait for the full render to settle (P&L Summary is in SupportingSection, rendered after data loads)
    await findByText("P&L Summary");
    expect(container.textContent).not.toContain("[object Object]");
  });
});
