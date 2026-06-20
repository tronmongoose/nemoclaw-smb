# NemoClaw STR Agent

A three-act autonomous agent for short-term rental operations. It catches management-fee
overcharges, governs cleaner card issuance through non-human identities, and sells
dynamic pricing plus Agent Engine Optimization audits over HTTP 402. Every agent action
runs through a REQUIRE_APPROVAL gate and lands in a hash-chained audit log.
ConductorOne provides the identity control plane: the agent itself is a non-human
identity (NHI), and each sub-agent receives a least-privilege scoped identity before
any money moves. Built for the Hermes x NVIDIA x Stripe hackathon (due 2026-06-30).

---

## The three-act demo

**Act 1 - Owner catches an overcharge.** The STR owner agent ingests the monthly ledger
for property `prop-001` (Sweet Clementine). It detects that the management company
charged 22% against a 20% contract on $4,200 revenue - an $84 overcharge. The agent
holds the reconciliation payout for human approval via the REQUIRE_APPROVAL gate, then
issues an Ed25519-signed Stripe envelope and logs the corrected payment to the audit
chain once approved. In DEMO_MODE all Stripe writes are mocked but logged as if real.

**Act 2 - Management company governs card issuance and payouts.** On every guest
checkout, a least-privilege NHI is issued by ConductorOne for the `cleaner-subagent`
identity, scoped to `["card:issue:cleaning"]` with a one-hour TTL. The agent authorizes
the NHI before issuing a single-use Stripe Issuing card, runs month-end crew payouts
through Stripe Connect, and produces usage-based owner invoices through Metronome. The
C1 NHI-per-checkout path is the core governance showcase - no card can be issued
without a live authorization decision.

**Act 3 - Platform sells intelligence on HTTP 402.** The platform agent exposes a
dynamic pricing skill and an AEO (Agent Engine Optimization) audit skill behind
Stripe's Machine Payments Protocol. An AI booking agent sends a request, receives an
HTTP 402 with a payment link, pays via PaymentIntent, and gets the result. The AEO
audit analyzes a listing for structured data, response latency, and policy-compliance
signals that AI booking agents prioritize over SEO keywords. MPP settlement is
DEMO_MODE-mocked; the AEO logic and the 402 loop shape are real.

---

## ConductorOne governance

The agent is issued a non-human identity through ConductorOne at startup - not a
service account with a shared secret, but a scoped, auditable NHI with explicit
permissions. Sub-agents receive their own NHIs, narrowed to only the scopes their
task requires (e.g. `card:issue:cleaning` for the cleaner sub-agent, `ledger:read`
for the owner reconciliation path). Access inventory is managed through open-source
**Baton**, which can pull connector snapshots from SaaS tools and surface unused-access
findings without requiring a live C1 tenant.

All data used here is synthetic. The C1 client connects to a real ConductorOne API
when `C1_API_KEY` + `C1_BASE_URL` are set, but falls back gracefully to local policy
evaluation. No internal C1 roadmap features or work-tenant data are used anywhere.

---

## Quickstart

```bash
git clone https://github.com/tronmongoose/nemoclaw-smb.git
cd nemoclaw-smb
cp .env.example .env          # no keys needed for DEMO_MODE
pip install -e .
python -m demo.run_demo       # DEMO_MODE: all Stripe writes mocked but logged
```

No credentials are required to run the demo. To enable live integrations, set
`NOUS_PORTAL_API_KEY`, `NVIDIA_NIM_API_KEY`, `STRIPE_SECRET_KEY=sk_test_...`, or
`C1_API_KEY` in `.env`. Each key activates its real path; `sk_live_` keys are refused
in code.

---

## Architecture

```
Hermes (Nous Portal): orchestrator, intent parsing
        |
        v
NemoClaw harness (REQUIRE_APPROVAL gate, spend threshold)
        |
        v
ConductorOne control plane
  - NHI issuance per agent + sub-agent
  - Scope enforcement (least-privilege per action)
  - Baton OSS access inventory
        |
        v
Carryall Ed25519 signed envelope
        |
        v
Stripe primitives (DEMO_MODE-mocked in default run)
  - PaymentIntents (Act 1 reconciliation)
  - Issuing (Act 2 cleaner cards)
  - Connect + Global Payouts (Act 2 crew payouts)
  - Metronome UBP (Act 2 owner invoices)
  - MPP / HTTP-402 (Act 3 platform sells)

Model router: Nemotron 3 Ultra (heavy reasoning) <-> Hermes (orchestration)
Audit: SHA-256 hash-chained log, verified end-to-end
```

---

## Sponsor tech map

| Technology | Hackathon sponsor | Role in demo | Act |
|---|---|---|---|
| **Hermes** (Nous Research) | Nous Research | Primary orchestrator; parses intent, drives skills | All |
| **Nemotron 3 Ultra** (NVIDIA NIM) | NVIDIA | Heavy reasoning for anomaly root cause, pricing analysis | 1, 3 |
| **NemoClaw harness** (NVIDIA) | NVIDIA | Safe-execution chokepoint; REQUIRE_APPROVAL gate; audit chain | All |
| **Stripe PaymentIntents** | Stripe | Reconciliation payout after anomaly approval | 1 |
| **Stripe Approval gate** | Stripe | Human-approval gate on spend over threshold | 1 |
| **Stripe Issuing for Agents** | Stripe | Single-use cleaner cards, one per checkout, C1-governed | 2 |
| **Stripe Connect** | Stripe | Owner Connect accounts for portfolio-level routing | 2 |
| **Stripe Global Payouts** | Stripe | Month-end crew payouts | 2 |
| **Metronome UBP** | Stripe ecosystem | Usage-based owner invoices per property per month | 2 |
| **Stripe MPP / HTTP-402** | Stripe | Platform agent sells pricing + AEO audits to AI callers | 3 |
| **ConductorOne** | (no sponsor tier) | Agent NHI, sub-agent scoping, Baton OSS access inventory | All |

---

## What is real vs DEMO_MODE-mocked

The no-overclaim rule is enforced: `make reality` prints a live status matrix and
`tests/live/` fails when a real integration breaks. Run it; do not trust this table
from memory.

| Component | Status | Notes |
|---|---|---|
| AEO audit logic | REAL | Structural data analysis, AI-signal scoring; no live booking agent |
| Anomaly detection | REAL | Math against contract terms; local, deterministic |
| REQUIRE_APPROVAL gate | REAL | Fires on spend over threshold; blocks execution |
| Ed25519 signed envelopes | REAL | Every Stripe call wrapped before execution |
| SHA-256 audit chain | REAL | Hash-chained log; `make audit` verifies end-to-end |
| HTTP-402 loop shape | REAL | The 402 / authorize / respond cycle is implemented |
| NemoClaw harness | REAL | Single payment chokepoint; all spend routes through it |
| ConductorOne NHI + scoping | REAL client, synthetic decisions | Connects to C1 API with key; falls back to local policy; no live work tenant |
| Baton OSS binary | REAL (binary verified) | Access data is a fixture until a connector credential produces a live c1z |
| Hermes orchestration | MOCK by default | LIVE-OK when `NOUS_PORTAL_API_KEY` set; proven by `test_hermes_live` |
| Nemotron 3 Ultra | MOCK by default | LIVE-OK when `NVIDIA_NIM_API_KEY` set; proven by `test_nemotron_live` |
| Stripe money movement | DEMO_MODE-mocked, logged | All Stripe writes mocked; logged as if real; no real funds move; `sk_live_` refused |
| MPP settlement | DEMO_MODE-mocked, logged | 402 earn events written to audit log; no real MPP settlement |
| Metronome UBP billing | DEMO_MODE-mocked | Invoice math is real; API writes are mocked |

---

## AEO explained

Agent Engine Optimization is the discipline of preparing a listing, product, or service
to be discovered, selected, and purchased by an AI booking agent rather than a human
searcher. Where SEO optimizes for keyword ranking in a search index, AEO optimizes for
structured data quality, policy-compliance signals, API response latency, and the
machine-readable trust signals that an AI agent uses to rank options and decide to pay.
An STR listing that scores well on AEO is more likely to be recommended by a travel
AI agent to a human traveler - or purchased autonomously on their behalf.

This matters now because AI agents are becoming a primary discovery and booking channel
for travel. A guest does not search for "beachside Oceanside vacation rental" and scroll
results - they ask an agent to book a qualifying property within budget, and the agent
calls APIs, reads structured metadata, and executes a PaymentIntent. Listings that are
not optimized for machine callers will be systematically underbooked as this shift
accelerates. The Act 3 platform agent in this demo is both the proof-of-concept and the
business model: an STR platform sells AEO audits and dynamic pricing via HTTP 402 to
other AI agents, capturing revenue from the machine-to-machine economy.

---

## Submission + links

- Repo: `github.com/tronmongoose/nemoclaw-smb`
- Hackathon: Hermes Agent Accelerated Business Hackathon (Nous Research x NVIDIA x Stripe)
- Submission deadline: 2026-06-30
- Demo script: `docs/submission.md`
- Run-day steps: `docs/demo_runbook.md`
- Stripe setup: `docs/stripe_onboarding.md`
- Architecture detail: `BRIEF.md`, `ANALYSIS.md`

### Tweet draft

Shipped a three-act STR agent for @NousResearch x @NVIDIAAI x @stripe.

Act 1: agent catches a management-fee overcharge, holds for human approval, pays the
corrected amount. Act 2: @ConductorOne issues a least-privilege NHI to a cleaner
sub-agent before every card is issued - zero shared secrets. Act 3: platform sells
dynamic pricing + AEO audits over HTTP-402. AI travelers will book your listing through
agents, not search. AEO is SEO for machines.

DEMO_MODE mocks Stripe. The audit chain, anomaly math, and C1 governance are real.

github.com/tronmongoose/nemoclaw-smb

---

## License

See `LICENSE`.
