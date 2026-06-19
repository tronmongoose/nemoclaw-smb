# NemoClaw SMB Ops Agent — Submission

Hermes Agent Accelerated Business Hackathon (Nous Research x NVIDIA x Stripe).

## The problem

Small businesses leak money through vendor sprawl. Subscriptions creep, prices rise, seats
go unused, and nobody has time to watch every invoice. A 12-person studio does not have a
CFO. It has a founder approving charges at midnight.

## The agent

NemoClaw is an autonomous CFO/COO. It learns the business from one conversation, then:

- Watches every vendor invoice and scores it against the vendor's own history.
- Pays in-range bills automatically on HTTP 402, escalates anomalies to the CEO.
- Finds cheaper vendor alternatives and negotiates or switches.
- Deprovisions unused SaaS seats it discovers through access governance.
- Charges a 0.5% fee on what it moves. The agent pays for itself.

Nothing executes without passing a safe-execution harness, and every action is hash-chained
into an audit log that verifies end to end.

## How each sponsor technology is used

- **Hermes (Nous Research) is the primary orchestrator.** A bounded agent loop parses CEO
  intent, plans with the Hermes model on Nous Portal, dispatches skills, and finalizes. Live
  verified against `inference-api.nousresearch.com/v1` (model `nvidia/nemotron-3-super-120b-a12b`).
- **NemoClaw (NVIDIA) is the safe-execution harness.** Every skill runs guardrail to
  permission to execute to audit. Denylist plus optional NeMo Guardrails. Spend over threshold
  escalates for human approval before any money moves.
- **Nemotron 3 Ultra (NVIDIA)** is the heavy reasoner for vendor analysis, anomaly root
  cause, and negotiation drafts. Live verified through NVIDIA NIM.
- **NVIDIA agent skills.** 8 skills (onboarding, invoice-ingest, anomaly-detect,
  vendor-analyze, 402-handler, approval-gate, audit, access-governance), exportable to the
  NeMo Agent Toolkit (`agent/nat_workflow.yml`).
- **Stripe Skills for Hermes.** Payments route through the Stripe MCP server
  (`npx @stripe/mcp`, proxy to `mcp.stripe.com`). Buy on 402 (`create_payment_intent`),
  provision on switch (`create_product` + `create_price` + `create_subscription`), and collect
  the product's own fee. Test mode only. Direct SDK and mock are fallbacks.
- **ConductorOne** runs locally via open-source **Baton**. No tenant required. It surfaces
  unused-seat deprovision candidates (3 of 12 Adobe seats idle 60+ days in the demo).

## Demo script (6 scenes, ~3 minutes)

The dashboard (dark command-center on `:5173`) stays on screen throughout. `make demo`
narrates the loop in a terminal beside it.

1. **Onboarding.** "Pinwheel Studio, 12 people, design shop." The agent builds a vendor graph
   from one profile plus seed invoices. Dashboard graph populates.
2. **Anomaly caught.** Adobe renews at $340, up from a ~$277 baseline. The agent scores it
   (+23%, z-score over threshold), and ConductorOne/Baton flags 3 unused seats. It does not
   auto-pay. It escalates. The approval queue shows the $340 Adobe item.
3. **Reasoning.** Nemotron 3 Ultra ranks alternatives and drafts the procurement case
   (Affinity vs Adobe, monthly savings).
4. **Switch.** The agent provisions the replacement subscription through Stripe and records
   the realized monthly savings.
5. **Auto-pay through NemoClaw.** AWS renews in range. The agent runs it through the harness
   (guardrail to permission to execute to audit), pays via Stripe, and writes the ledger entry.
   Terminal prints the NemoClaw pipeline stages.
6. **The close.** Savings panel shows total spend, monthly and annual savings, and the
   NemoClaw fee (0.5%). The audit-chain badge reads green and verifies. The agent earned its keep.

Then, live: approve the Adobe item in the dashboard. It clears, the audit chain grows, and
re-verifies.

## What is real

Hermes orchestration, the NemoClaw harness, Nemotron reasoning, the 8 skills, and the local
ConductorOne/Baton path are real. Stripe is real in test mode the moment a `sk_test_` key is
present. 197 tests pass. The recorded demo replays a captured Hermes run for determinism
because reasoning-model output varies run to run; live orchestration is verified separately.

## Repo

`github.com/tronmongoose/nemoclaw-smb`. Architecture in `BRIEF.md`, run-day steps in
`docs/demo_runbook.md`, Stripe MCP setup in `docs/stripe_onboarding.md`.
