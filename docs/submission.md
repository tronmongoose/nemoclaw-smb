# NemoClaw STR Agent: Hackathon Submission

Hermes Agent Accelerated Business Hackathon (Nous Research x NVIDIA x Stripe).
Submission deadline: 2026-06-30.

---

## The problem

Short-term rental operators lose money at every layer of the stack. Owners get
overcharged on management fees and never notice. Management companies issue cleaner
cards manually, with shared credentials and no audit trail. Platforms price properties
on static calendars and optimize listings for human search engines that AI booking
agents do not use. The entire financial stack is manual, ungoverned, and unoptimized
for the machine-to-machine economy that is replacing human search.

---

## The agent

NemoClaw is a three-act autonomous STR operations agent. It runs through the full
economic lifecycle of a short-term rental: owner reconciliation, property management
operations, and platform-level intelligence selling. Every action is gated by
ConductorOne's identity control plane and logged in a hash-chained audit trail.
All Stripe money movement runs in DEMO_MODE (mocked but logged); the governance,
anomaly logic, and audit chain are real.

---

## How each sponsor technology is used

**Nous Research Hermes** is the primary orchestrator. A bounded agent loop parses
operator intent, plans with the Hermes model on Nous Portal, and dispatches skills
through the NemoClaw harness. Live path proven by `test_hermes_live` when
`NOUS_PORTAL_API_KEY` is set.

**NVIDIA Nemotron 3 Ultra** handles heavy reasoning: anomaly root cause, pricing
analysis, and AEO scoring logic. Routes through NVIDIA NIM. Live path proven by
`test_nemotron_live` when `NVIDIA_NIM_API_KEY` is set.

**NemoClaw (NVIDIA)** is the safe-execution harness. All spend routes through
`nemoclaw_harness.execute()`. No skill calls a payment API directly. Spend above
the REQUIRE_APPROVAL threshold (default $500) triggers a human approval gate before
any execution. Every action writes a SHA-256 hash-chained audit entry.

**Stripe** covers three distinct primitives across the three acts. Act 1 uses
PaymentIntents and the approval gate for reconciliation payouts. Act 2 uses Stripe
Issuing for single-use cleaner cards, Stripe Connect for owner accounts, and Global
Payouts for crew. Act 3 uses the Machine Payments Protocol (MPP) and HTTP-402 so AI
callers can pay for dynamic pricing and AEO audits autonomously. Metronome handles
usage-based invoicing for Act 2. All Stripe writes are DEMO_MODE-mocked; earn events
are logged as if real. `sk_live_` keys are refused in code.

**ConductorOne** provides the agent identity control plane. The top-level agent is
issued a non-human identity (NHI) at startup. Each sub-agent receives its own NHI,
scoped to only the permissions its task requires, with a TTL. The Act 2 cleaner
card path is the showcase: `issue_nhi("cleaner-subagent", scopes=["card:issue:cleaning"],
ttl_seconds=3600)` is called on every checkout event, and the NHI must be authorized
before any card is issued. Open-source Baton manages access inventory. All data is
synthetic; no live C1 work-tenant data is used anywhere.

---

## Demo script (three acts, approximately four minutes)

Run `python -m demo.run_demo` with no credentials needed. DEMO_MODE mocks all Stripe
writes but logs them to the audit chain as if real. The acts run in sequence.

**Act 1 - Owner catches an overcharge (about 90 seconds)**

The operator loads the monthly ledger for `prop-001` (Sweet Clementine). The agent
detects a 22% management fee charged against a 20% contract on $4,200 revenue - an
$84 overcharge. The agent does not auto-pay. It raises an anomaly, logs the finding,
and queues the corrected $84 reconciliation payout behind the REQUIRE_APPROVAL gate.
Once the operator approves, the agent signs an Ed25519 Stripe envelope and writes the
payment record to the audit chain. Terminal prints: ledger ingestion, anomaly score,
approval prompt, payment result, and audit hash.

**Act 2 - Management company governs card issuance and payouts (about 90 seconds)**

A guest checkout event fires for two properties. For each checkout, ConductorOne
issues a scoped NHI to `cleaner-subagent` (`card:issue:cleaning`, one-hour TTL) and
authorizes it before any card is issued. Single-use Stripe Issuing cards are created
per cleaning job. At month end, the agent runs crew payouts through Stripe Connect,
calculates usage-based owner invoices through Metronome, and prints a portfolio
summary. Terminal prints: NHI issuance, authorization decision, card result,
payout batch, and per-owner invoice amounts.

**Act 3 - Platform sells intelligence on HTTP 402 (about 60 seconds)**

The platform agent starts its MPP server. A simulated AI booking agent sends a pricing
request. The server returns HTTP 402 with a payment link. The caller pays via
PaymentIntent (DEMO_MODE-mocked) and receives a dynamic pricing recommendation. The
same flow runs for an AEO audit: the caller receives a structured report scoring the
listing on machine-readable data quality, response latency, and policy-compliance
signals. Terminal prints: 402 challenge, payment event, pricing result, AEO score,
and platform revenue summary.

At the close, `make audit` verifies the full hash chain across all three acts.

---

## What is real vs DEMO_MODE-mocked

Run `make reality` for the live status matrix. The table below reflects the default
DEMO_MODE run; live integrations activate when the corresponding key is set.

| Component | Status |
|---|---|
| AEO audit logic and scoring | REAL |
| Anomaly detection | REAL |
| REQUIRE_APPROVAL gate | REAL |
| Ed25519 signed envelopes | REAL |
| SHA-256 audit chain | REAL |
| HTTP-402 loop shape | REAL |
| NemoClaw harness | REAL |
| ConductorOne NHI + scoping | REAL client, synthetic decisions, no live work tenant |
| Baton OSS binary | REAL (binary verified); access data is a fixture |
| Hermes orchestration | MOCK by default; LIVE-OK with `NOUS_PORTAL_API_KEY` |
| Nemotron 3 Ultra | MOCK by default; LIVE-OK with `NVIDIA_NIM_API_KEY` |
| Stripe money movement | DEMO_MODE-mocked, logged; no real funds move |
| MPP settlement | DEMO_MODE-mocked, logged |
| Metronome UBP billing | DEMO_MODE-mocked; invoice math is real |

---

## AEO: the Act 3 differentiator

Agent Engine Optimization is the practice of structuring a listing, product, or
service to be selected and purchased by an AI booking agent. Where SEO targets keyword
ranking for human eyes, AEO targets structured data quality, policy-compliance signals,
API response latency, and machine-readable trust metadata that AI agents use to rank
and book.

As AI agents become the primary discovery and booking channel for travel, listings
optimized only for human search engines will be systematically underbooked. The Act 3
platform agent is both a proof of concept and a business model: an STR platform sells
AEO audits and dynamic pricing recommendations to other AI agents over HTTP 402,
earning per call in the machine-to-machine economy.

---

## ConductorOne governance summary

The agent operates under a non-human identity issued by ConductorOne at startup, not
a shared service-account credential. Sub-agents receive time-limited, scope-narrowed
NHIs per task. The Act 2 cleaner card flow is the core showcase: one NHI per checkout,
one scope, one hour TTL, one authorization decision before any money moves. Baton
provides open-source access inventory that can pull connector snapshots without a live
C1 SaaS tenant.

This is built on ConductorOne's public GA tooling and open-source Baton. All decisions
run against synthetic data. No internal roadmap features, no live work tenant, no
ConductorOne customer data.

---

## Repo

`github.com/tronmongoose/nemoclaw-smb`

Architecture: `BRIEF.md` and `ANALYSIS.md`.
Run-day steps: `docs/demo_runbook.md`.
Stripe setup: `docs/stripe_onboarding.md`.
