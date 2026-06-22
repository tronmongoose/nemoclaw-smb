/** The tech layer's single source of truth: where each sponsor plugs into each
 *  portal's problem set. Honest to the code (matches the seeded interactions and the
 *  instrumented call sites). Empty portal cells mean the sponsor is genuinely not used
 *  there. `ops` are case-insensitive substrings matched against interaction op names to
 *  count live + historical calls per cell. */

import type { StrSegment } from "../../../types";

export interface SponsorCell {
  capability: string; // what the sponsor does in this portal
  problem: string; // the portal problem it addresses
  ops: string[]; // op-name substrings that count toward this cell
}

export interface SponsorRow {
  id: string; // stable row id
  sponsor: string; // matches interaction.sponsor exactly
  pillarId: string; // matches /integrations/status pillar id (for live verify)
  kind: string; // reasoning | payments | orchestration | governance
  blurb: string; // one-line role
  byPortal: Partial<Record<StrSegment, SponsorCell>>;
}

export const PORTAL_LABELS: Record<StrSegment, string> = {
  owner: "Owner",
  firm: "Company",
  agent: "Swarm",
};

export const PORTAL_ORDER: StrSegment[] = ["owner", "firm", "agent"];

export const SPONSOR_MAP: SponsorRow[] = [
  {
    id: "nvidia",
    sponsor: "NVIDIA",
    pillarId: "nemotron",
    kind: "reasoning",
    blurb: "Nemotron reasons over the hard calls",
    byPortal: {
      owner: {
        capability: "Anomaly reasoning",
        problem: "Catch the management-fee overcharge",
        ops: ["anomaly"],
      },
      agent: {
        capability: "Pricing + audit reasoning",
        problem: "Set a price and grade machine-readability",
        ops: ["dynamic pricing", "aeo", "pricing", "scoring"],
      },
    },
  },
  {
    id: "stripe",
    sponsor: "Stripe",
    pillarId: "stripe",
    kind: "payments",
    blurb: "Moves money under scoped identity",
    byPortal: {
      owner: {
        capability: "Reconciliation payout",
        problem: "Pay the correction once approved",
        ops: ["reconciliation"],
      },
      firm: {
        capability: "Issuing, Connect, Payouts, Metronome",
        problem: "Cleaner cards, crew payouts, owner invoices",
        ops: ["card issue", "payout", "owner account", "ubp", "invoice", "connect"],
      },
      agent: {
        capability: "MPP HTTP-402 earn",
        problem: "Earn per agent-to-agent call",
        ops: ["mpp earn", "earn"],
      },
    },
  },
  {
    id: "nous",
    sponsor: "Nous Research",
    pillarId: "hermes",
    kind: "orchestration",
    blurb: "Hermes routes intent to skills",
    byPortal: {
      agent: {
        capability: "Intent orchestration",
        problem: "Route each paid call to the right skill",
        ops: ["orchestration", "intent"],
      },
    },
  },
  {
    id: "conductorone",
    sponsor: "C1",
    pillarId: "conductorone",
    kind: "governance",
    blurb: "Governs every action with scoped NHIs",
    byPortal: {
      owner: {
        capability: "Authorize NHI",
        problem: "Govern the correction before it pays",
        ops: ["authorize", "nhi"],
      },
      firm: {
        capability: "Scoped NHI per checkout",
        problem: "Least-privilege cleaner identity",
        ops: ["authorize", "nhi"],
      },
      agent: {
        capability: "NHI gating + entitlements",
        problem: "Govern every paid agent-to-agent call",
        ops: ["authorize", "nhi"],
      },
    },
  },
];

/** True when an interaction op belongs to a sponsor cell (case-insensitive substring). */
export function opMatchesCell(op: string, cell: SponsorCell): boolean {
  const lower = op.toLowerCase();
  return cell.ops.some((o) => lower.includes(o));
}
