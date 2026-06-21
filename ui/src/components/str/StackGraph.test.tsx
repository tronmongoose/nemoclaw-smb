/** Smoke tests for StackGraph: pillar labels, Stripe skills, and Verify live control. */

import { render, screen, waitFor } from "@testing-library/react";
import { vi, describe, it, expect, beforeEach } from "vitest";
import { StackGraph } from "./StackGraph";
import type { IntegrationStatusResponse } from "../../types";

vi.mock("../../lib/api", () => ({
  apiFetch: vi.fn(),
}));

// ForceGraph2D uses canvas APIs not available in jsdom; mock the whole module.
vi.mock("react-force-graph-2d", () => ({ default: () => null }));

import { apiFetch } from "../../lib/api";
const mockApiFetch = vi.mocked(apiFetch);

const FIXTURE: IntegrationStatusResponse = {
  agent: {
    id: "agent",
    label: "NemoClaw Agent",
    kind: "core",
    status: "REAL",
    detail: "guardrail -> approval -> execute -> SHA-256 hash-chained audit",
    source: "local",
  },
  pillars: [
    {
      id: "nemotron",
      label: "NVIDIA Nemotron",
      vendor: "NVIDIA",
      kind: "reasoning",
      status: "LIVE-CAPABLE",
      detail: "Nemotron Ultra 253B available",
      skills: ["anomaly reasoning", "dynamic pricing", "AEO scoring"],
    },
    {
      id: "hermes",
      label: "Nous Hermes",
      vendor: "Nous Research",
      kind: "orchestration",
      status: "LIVE-CAPABLE",
      detail: "Hermes 3 8B available via Ollama",
      skills: ["intent parsing", "skill orchestration"],
    },
    {
      id: "stripe",
      label: "Stripe",
      vendor: "Stripe",
      kind: "payments",
      status: "DEMO",
      detail: "test-mode, mocked; no funds move",
      skills: [
        "Issuing for Agents",
        "Connect",
        "Global Payouts",
        "Metronome UBP",
        "MPP / HTTP-402",
      ],
    },
    {
      id: "conductorone",
      label: "ConductorOne",
      vendor: "ConductorOne",
      kind: "governance",
      status: "DEMO",
      detail: "Baton grant-matching via carryall-baton-backend against a .c1z",
      skills: ["scoped NHIs", "Baton entitlements", "authorize"],
    },
  ],
};

describe("StackGraph", () => {
  beforeEach(() => {
    mockApiFetch.mockResolvedValue(FIXTURE as unknown as null);
  });

  it("renders all four pillar labels", async () => {
    render(<StackGraph />);
    expect(await screen.findByText("NVIDIA Nemotron")).toBeInTheDocument();
    expect(await screen.findByText("Nous Hermes")).toBeInTheDocument();
    // Stripe and ConductorOne appear as both label and vendor span (label == vendor).
    expect((await screen.findAllByText("Stripe")).length).toBeGreaterThanOrEqual(1);
    expect((await screen.findAllByText("ConductorOne")).length).toBeGreaterThanOrEqual(1);
  });

  it("renders Stripe's five skills including Issuing for Agents and MPP / HTTP-402", async () => {
    render(<StackGraph />);
    expect(await screen.findByText("Issuing for Agents")).toBeInTheDocument();
    expect(await screen.findByText("Connect")).toBeInTheDocument();
    expect(await screen.findByText("Global Payouts")).toBeInTheDocument();
    expect(await screen.findByText("Metronome UBP")).toBeInTheDocument();
    expect(await screen.findByText("MPP / HTTP-402")).toBeInTheDocument();
  });

  it("renders a Verify live control for each pillar", async () => {
    render(<StackGraph />);
    await waitFor(() => {
      const buttons = screen.getAllByText("Verify live");
      expect(buttons.length).toBe(4);
    });
  });

  it("renders EmptyState when API returns null", async () => {
    mockApiFetch.mockResolvedValue(null);
    render(<StackGraph />);
    expect(await screen.findByText("No data")).toBeInTheDocument();
  });
});
