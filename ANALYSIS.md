# NemoClaw SMB — Analysis: What It Does, Value, and Intent Fidelity

This document is the honest accounting: what the project actually does when you run it, the
value it would create, and how much of the original brief survived into the build. It was
written after an independent real-vs-mock audit and a remediation pass, not from the
marketing.

## What it actually does

Run `make demo` and the agent walks the full small-business finance loop on seeded data for
a fictional 12-person design studio:

1. Learns the business from a profile and invoice history into a vendor knowledge graph.
2. Scores each invoice against that vendor's own history (real z-score math).
3. On an HTTP 402 payment-required event: checks policy, scores the anomaly, then either
   pays an in-range bill or escalates an unusual one to the CEO for approval.
4. Routes every payment through the NemoClaw harness (guardrail, approval gate, execution,
   audit) so there is one enforced chokepoint, not direct API calls.
5. Hash-chains every action into a tamper-evident audit log that verifies end to end.
6. Surfaces unused SaaS seats (ConductorOne/Baton) and ranks cheaper vendor alternatives.

Run `make dev` + the dashboard and you see the same state live: the vendor graph, the
invoice feed with the anomaly flagged, the approval queue, and a savings panel with the
agent's own 0.5% fee.

Hermes (Nous Portal) is the orchestrator: it parses a CEO intent, plans, and dispatches the
skills. That path is real and verified live. The recorded demo replays a captured run because
reasoning-model output varies run to run.

## The value thesis

A 12-person business has no CFO. It approves charges at midnight and never audits seats. This
agent is the missing finance function:

- Catches the price creep a human misses (the Adobe +23% spike).
- Pays the routine bills silently and escalates only the unusual ones.
- Finds the cheaper vendor and does the switch.
- Deprovisions seats nobody uses.
- Leaves a tamper-evident trail for every dollar moved.
- Charges 0.5% of spend under management, so it pays for itself.

The differentiator is not the payments. It is the governed path: every action gated and
audited. That is what makes an autonomous money-mover safe enough to run.

## Intent fidelity (original brief to delivered)

| Brief intent | Status | Note |
|---|---|---|
| Knowledge graph of the business | DELIVERED-REAL | in-memory graph; real GBrain MCP client wired, install user-gated |
| Hermes as primary orchestrator | DELIVERED-LIVE | real Nous Portal calls; verified with a falsifying live test |
| Nemotron heavy reasoning | DELIVERED-LIVE | real NIM calls (550B model, slow) |
| NemoClaw safe execution | DELIVERED-REAL | real harness + the single payment chokepoint; real NeMo Guardrails opt-in; subprocess sandbox (not OpenShell) |
| ConductorOne control plane | PARTIAL | real API client built to the public SDK spec; live verify needs a tenant. Access governance is live-local via Baton |
| HTTP 402 trigger loop | DELIVERED-REAL | full pipeline, both pay and escalate paths |
| Stripe Skills for Hermes | DELIVERED-LIVE (test mode) | real test-mode buy/provision/pay via SDK and Stripe MCP; verified PaymentIntent created |
| Intuit reconciliation | MOCK | in-memory ledger; needs Intuit sandbox creds |
| Vendor negotiation / switch | DELIVERED-REAL (logic) | ranking + switch cascade real; the live vendor-search step is seeded |
| Hash-chained audit | DELIVERED-REAL | SHA-256 chain, verifies end to end |
| Approval over $100 | DELIVERED-REAL | enforced in the harness |

## What this remediation pass changed

The prior state was a real local spine plus a layer of "real-when-keyed" code that no test
proved and that mostly never ran live, plus three hollow pieces. This pass:

- Built `make reality` and `tests/live/`: an honest status matrix and falsifying tests that
  fail when a live integration breaks (the gap that let the overclaiming happen).
- Removed the ConductorOne crash-landmine (setting the key used to raise) and built the real
  C1 API client behind a graceful fallback.
- Made NemoClaw the single payment chokepoint (the 402 handler no longer calls Stripe directly).
- Replaced the NeMo Guardrails presence-stub with a real LLMRails check (opt-in).
- Replaced the not-implemented OpenShell sandbox with a real subprocess isolation boundary,
  honestly labeled.
- Verified Stripe, Hermes, Nemotron, and Baton live; wired a real GBrain MCP client.

## Honest remaining gaps and what unblocks them

- **ConductorOne live:** needs a C1 tenant + API key (synthetic data only — never work data).
- **Intuit/QuickBooks:** needs Intuit developer sandbox credentials.
- **GBrain live:** needs `npm i -g github:garrytan/gbrain` (user-gated install) + bun.
- **Baton real access data:** needs a connector credential (e.g. a GitHub PAT) to produce a
  real c1z; the binary and parser are verified, the demo data is a fixture.
- **Stripe MCP path:** runs under the 3.11 venv where `mcp` is installed, not system 3.9.

Run `make reality` for the current truth. The matrix, not this document, is authoritative.
