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
skills. That path is MOCK by default; set `NOUS_PORTAL_API_KEY` to activate real Nous Portal
calls (verified by `test_hermes_live`). The recorded demo replays a captured Hermes run
because reasoning-model output varies run to run.

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
| Knowledge graph of the business | DELIVERED-REAL (in-memory default); LIVE when keyed | in-memory graph always runs; real GBrain MCP client activates with `GBRAIN_MCP_CMD`; install user-gated. Live test: `test_gbrain_live` |
| Hermes as primary orchestrator | MOCK by default; LIVE-OK when `NOUS_PORTAL_API_KEY` set | real Nous Portal calls verified by `test_hermes_live` when keyed |
| Nemotron heavy reasoning | MOCK by default; LIVE-OK when `NVIDIA_NIM_API_KEY` set | real NIM calls (550B model, slow); verified by `test_nemotron_live` |
| NemoClaw safe execution | DELIVERED-REAL | real harness + single payment chokepoint; NeMo Guardrails opt-in (`NEMOCLAW_GUARDRAILS=1`; denylist otherwise); subprocess sandbox opt-in (`NEMOCLAW_SANDBOX`; in-process fallback otherwise). Live tests: `test_guardrails_live`, `test_sandbox_subprocess_live` |
| ConductorOne control plane | LIVE-OK (graceful fallback); LIVE-VERIFIED needs a tenant | real API client built to the public SDK spec; falls back to local policy when unconfigured, never crashes. Access governance is live-local via Baton (binary). Live tests: `test_c1_policy_check_live`, `test_baton_live` |
| HTTP 402 trigger loop | DELIVERED-REAL | full pipeline, both pay and escalate paths |
| Stripe Skills for Hermes | MOCK by default; LIVE-OK (test mode) when `STRIPE_SECRET_KEY=sk_test_…` set | real test-mode buy/provision/pay via SDK; Stripe MCP path needs 3.11 venv + npx. `sk_live_` refused. Verified by `test_stripe_live` |
| Intuit reconciliation | MOCK | in-memory ledger; needs Intuit sandbox creds. No falsifying test — unverified |
| Vendor negotiation / switch | DELIVERED-REAL (logic) | ranking + switch cascade real; live vendor-search step is seeded |
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
