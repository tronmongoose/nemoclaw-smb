# NemoClaw SMB Ops Agent

## Project Brief for Agent Swarm — Hermes Agent Accelerated Business Hackathon

**Hackathon:** Nous Research x NVIDIA x Stripe  
**Submission deadline:** EOD Tuesday, June 30, 2026  
**Deliverable:** 1-3 min demo video + short writeup + GitHub repo  
**Prizes:** 1st place = $10k cash + NVIDIA DGX Spark + $5k Stripe Credits

-----

## Problem Statement

Small businesses (under 50 people) have no IT team, no finance ops person, and no access governance. They manually pay SaaS bills, over-provision software seats, miss anomalies, and have no negotiating leverage with vendors. The total addressable pain: every SMB is doing $5-100k/year in SaaS spend with zero automation, zero visibility, and zero policy enforcement.

**NemoClaw SMB Ops Agent** is an autonomous CFO/COO agent that governs identity, pays bills, learns the business, and negotiates on its behalf. Plug and play for any small business.

-----

## Business Model

**Primary:** Usage-based on spend under management (0.5-1% of monthly vendor spend the agent touches). Revenue scales with customer value delivered. Aligns with ConductorOne UBP.

**Secondary wedge:** Savings share on negotiated vendor deals (20% of documented savings). Easiest to sell: “we only make money when you save money.”

**GTM:** Distribute through bookkeepers and accountants (Intuit partner network), not direct to SMB owners. A bookkeeper managing 40 SMB clients becomes a reseller.

-----

## Full Architecture

### Layer 1: GBrain (Knowledge Graph / Memory)

- CEO onboards via natural language: “we’re a 12-person design studio, we pay Adobe, Figma, AWS, and Gusto monthly”
- GBrain builds a persistent business knowledge graph: vendors, spend patterns, team structure, growth trajectory, approval contacts
- Every invoice ingested updates the graph: vendor, amount, category, trend delta, anomaly flag
- GBrain feeds context to every downstream agent action — it is the reasoning substrate
- **Tech:** Garry Tan's GBrain as the knowledge graph layer; persistent across sessions

### Layer 2: Hermes Agent (Orchestration)

- CEO-facing interface: natural language in, structured actions out
- Powered by Nous Research Hermes model
- Routes tasks to the right model based on complexity (see Layer 3)
- Maintains conversation context via GBrain
- Escalates to human only when C1 policy requires it OR confidence is below threshold
- **Tech:** Nous Research Hermes via NemoClaw harness

### Layer 3: Model Routing (Open Source Intelligence)

- **Nemotron 3 Ultra (NVIDIA):** heavy reasoning tasks — contract analysis, vendor negotiation drafts, anomaly root cause investigation, multi-vendor comparison
- **Hermes 3 / smaller Hermes variant:** routine classification — invoice tagging, vendor categorization, spend bucketing, recurring vs. one-time detection
- **Devstral or equivalent:** any code/automation tasks — webhook setup, API integration scaffolding, data transformation
- Router logic: task complexity score from Hermes determines which model handles it; Nemotron only fires on high-complexity tasks to manage latency and cost
- **Tech:** ClawRouter pattern (claude-sonnet-4 swapped for Hermes; Nemotron 3 Ultra as the heavy reasoner)

### Layer 4: NemoClaw (Safe Execution Harness)

- All agent actions pass through NemoClaw before execution
- Spend actions, vendor outreach, access changes, API calls — all gated
- NemoClaw enforces REQUIRE_APPROVAL on actions above defined thresholds
- Audit log: every action hash-chained for tamper-evidence
- **Tech:** NVIDIA NemoClaw; maps directly to Carryall REQUIRE_APPROVAL pattern

### Layer 5: ConductorOne Control Plane (Identity + Policy)

- Defines who can spend what, on which vendors, up to what limits
- Access governance for SaaS provisioning: new hire triggers seat grants, offboarding triggers revocation
- Policy layer that makes this safe for an SMB with no IT team
- UBP billing: customer pays C1 based on actual usage, not a flat enterprise contract
- **Tech:** ConductorOne API; UBP entitlement model

### Layer 6: HTTP 402 Trigger Loop

- Agent monitors for 402 Payment Required responses from vendor APIs and SaaS renewals
- On 402 received:
1. GBrain lookup: is this vendor known? Is amount within expected range?
1. C1 policy check: is spend authorized for this vendor/amount/requester?
1. Anomaly check: Hermes scores the invoice against historical pattern
1. If clean: Stripe executes payment silently
1. If anomaly flagged: Nemotron reasons over it, Hermes surfaces to CEO with full context
1. If vendor flagged as poor value: agent initiates procurement loop (see Layer 8)
- **Tech:** HTTP 402 webhook listener; Stripe payment intent on approval

### Layer 7: Stripe Skills (Payment Execution)

- Executes approved payments via Stripe API
- Manages subscription seat count changes (upgrade/downgrade)
- Handles vendor onboarding for new deals negotiated by agent
- Stripe billing for NemoClaw SMB itself (the product’s own revenue collection)
- **Tech:** Stripe Skills for Hermes (hackathon integration); Stripe API for direct calls

### Layer 8: Intuit Integration (Books Layer)

- Every payment auto-categorized and reconciled into QuickBooks
- GBrain + Intuit together give CEO a live P&L view without manual entry
- Tax prep becomes a byproduct, not a project
- **Tech:** Intuit QuickBooks API; webhook on Stripe payment confirmation

### Layer 9: Vendor Negotiation / Procurement Loop

- GBrain flags: “Adobe up 23% this quarter vs. comparable studios your size”
- Nemotron drafts outreach or negotiation email
- Agent searches alternative vendors, compares pricing, presents ranked options to CEO
- CEO approves, agent executes the switch:
  - C1 updates access policy
  - Stripe cancels old subscription, provisions new one
  - Old SaaS access revoked via C1 connector
  - Intuit entry created for the transition
- **Tech:** Hermes agent + Nemotron 3 Ultra; Stripe subscription management; C1 connector API

-----

## Demo Arc (1-3 minutes)

**Scene 1 (0:00-0:20): Onboarding**
CEO talks to agent: “We’re a 12-person design studio. Here are our monthly bills.” Agent parses, GBrain builds the knowledge graph. Show the graph populating live.

**Scene 2 (0:20-0:45): Anomaly Detection**
Invoice comes in 23% higher than expected (Adobe). Agent flags it automatically. Shows CEO: “Adobe Creative Cloud renewal is $340, up from $277 last month. This is outside your normal range. Three of your seats haven’t been used in 60 days.”

**Scene 3 (0:45-1:15): Reasoning + Decision**
CEO says “find me a better option.” Nemotron reasons over alternatives. Agent returns two options: Affinity suite ($89/year flat) and a downgraded Adobe plan. Cost comparison shown cleanly.

**Scene 4 (1:15-1:45): Execution**
CEO approves Affinity switch. Show the cascade:

- C1 policy updated (Adobe de-provisioned)
- Stripe cancels Adobe subscription
- Stripe provisions Affinity
- Intuit entry created
- GBrain knowledge graph updated

**Scene 5 (1:45-2:00): 402 in the wild**
AWS renewal fires a 402. Agent handles it silently: C1 check, Stripe payment, Intuit reconcile. No CEO involvement. Show the audit log entry.

**Scene 6 (2:00-2:15): Close**
Dashboard: “This month NemoClaw saved you $1,847 in reduced SaaS spend. 3 invoices auto-paid. 1 anomaly flagged and resolved.” Show the business model line: “You owe NemoClaw $9.23.”

-----

## Repository Structure

```
nemoclaw-smb/
├── README.md
├── BRIEF.md                          # this document
├── agent/
│   ├── hermes_orchestrator.py        # Hermes agent main loop
│   ├── claw_router.py                # model routing (Nemotron vs Hermes-small)
│   ├── require_approval.py           # NemoClaw approval gate
│   └── audit_log.py                  # hash-chained audit (Carryall pattern)
├── gbrain/
│   ├── knowledge_graph.py            # GBrain integration
│   ├── onboarding.py                 # CEO natural language intake
│   ├── invoice_ingestion.py          # invoice parsing + graph update
│   └── anomaly_detector.py           # spend pattern analysis
├── control_plane/
│   ├── c1_client.py                  # ConductorOne API wrapper
│   ├── policy_check.py               # spend authorization logic
│   └── access_provisioner.py         # SaaS seat management via C1
├── payments/
│   ├── stripe_client.py              # Stripe Skills integration
│   ├── payment_402_handler.py        # HTTP 402 listener + executor
│   └── intuit_reconciler.py          # QuickBooks sync
├── procurement/
│   ├── vendor_analyzer.py            # Nemotron-powered vendor comparison
│   ├── negotiation_drafter.py        # outreach email generation
│   └── vendor_switcher.py            # end-to-end vendor transition
├── api/
│   ├── main.py                       # FastAPI entry point
│   ├── routes/
│   │   ├── onboarding.py
│   │   ├── invoices.py
│   │   ├── approvals.py
│   │   └── webhooks.py               # Stripe + vendor 402 webhooks
│   └── models/
│       ├── invoice.py
│       ├── vendor.py
│       └── policy.py
├── ui/
│   ├── package.json
│   └── src/
│       ├── App.jsx
│       ├── components/
│       │   ├── KnowledgeGraph.jsx    # GBrain visualization
│       │   ├── InvoiceFeed.jsx
│       │   ├── AnomalyAlert.jsx
│       │   ├── ApprovalModal.jsx
│       │   └── SavingsDashboard.jsx
│       └── hooks/
│           └── useAgentStream.js     # streaming agent responses
├── infra/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── .env.example
└── tests/
    ├── test_402_handler.py
    ├── test_anomaly_detector.py
    ├── test_policy_check.py
    └── test_vendor_switcher.py
```

-----

## Build Milestones

### Week 1 (June 16-22): Core Infrastructure

**Day 1-2: Repo scaffold + env**

- Init repo with structure above
- Wire `.env.example`: Hermes API key, NVIDIA API endpoint, C1 API key, Stripe test key, Intuit sandbox, GBrain endpoint
- Docker-compose: FastAPI backend + React frontend + Redis for state
- Stub all module interfaces so agent can call them even before they’re implemented

**Day 3-4: GBrain onboarding + invoice ingestion**

- CEO onboarding flow: natural language intake via Hermes, structured output to GBrain knowledge graph
- Invoice parser: extract vendor, amount, date, category from PDF/email/manual input
- Anomaly detector: simple statistical baseline first (mean + 2 std dev), then Nemotron-enhanced reasoning
- Mock GBrain if direct API access isn’t available yet; design the interface contract now

**Day 5-6: C1 control plane integration**

- C1 API client: policy check (is this vendor/amount approved?), access provisioning, UBP entitlement read
- REQUIRE_APPROVAL gate in NemoClaw harness
- Hash-chained audit log (port from Carryall)

**Day 7: 402 handler + Stripe basics**

- HTTP 402 webhook listener
- Stripe payment intent creation on approval
- End-to-end flow: 402 received, C1 check, Stripe pay, audit log entry
- This is the core demo loop; get it working even with mocked C1 and GBrain

-----

### Week 2 (June 23-29): Polish + Demo

**Day 8-9: Intuit reconciliation + model routing**

- QuickBooks API: auto-categorize and post payment entries
- ClawRouter: route tasks to Nemotron 3 Ultra vs. Hermes-small based on complexity score
- Vendor comparison flow: Nemotron reasoning over alternatives, ranked output

**Day 10-11: Procurement loop + negotiation**

- Vendor switch end-to-end: C1 de-provision old, Stripe cancel, Stripe provision new, C1 grant new
- Negotiation email drafter via Nemotron
- Savings calculation and attribution

**Day 12-13: UI**

- CEO dashboard: GBrain knowledge graph visualization (force-directed graph, D3 or similar)
- Invoice feed with anomaly flags
- Approval modal with full context (why flagged, recommended action, one-click approve/reject)
- Savings dashboard with NemoClaw’s own fee calculated live

**Day 14 (June 29): Demo recording + submission**

- Record 1-3 min walkthrough following the demo arc above
- Write submission copy (lead with the 402 loop and the savings share business model)
- Tweet tagging @NousResearch
- Submit to Discord channel + submission form

-----

## Deployment Considerations

### Sponsor Technology Obligations

**Nous Research / Hermes:**

- Hermes must be the primary orchestration model, not a supporting role
- NemoClaw must be visible in the demo as the execution harness
- Nemotron 3 Ultra must handle at least one reasoning-heavy task visibly (vendor analysis, anomaly reasoning)
- GBrain should be shown learning and updating from CEO input and invoice data

**NVIDIA:**

- NemoClaw as the safe agent execution layer is the primary NVIDIA contribution
- Nemotron 3 Ultra as the reasoning model is the secondary contribution
- Both should be called out explicitly in the writeup and visible in the demo

**Stripe:**

- Stripe Skills for Hermes (not just raw Stripe API) should be the payment layer
- Show at least two Stripe actions: auto-payment on 402, subscription management on vendor switch
- The product’s own revenue collection via Stripe is a nice-touch detail for the “earn” requirement

### Infrastructure

**For demo purposes:**

- Single VPS or local Docker Compose is sufficient
- Stripe test mode throughout (no real money)
- Intuit sandbox environment
- C1 sandbox/dev environment
- GBrain: use available API or mock with a graph database (Neo4j or similar) if direct access isn’t ready

**Hard constraints:**

- No Chinese-origin models anywhere in the stack (Qwen, DeepSeek, Baidu, etc.)
- All agent actions must pass through NemoClaw before execution, no direct API calls from agent to payment layer
- REQUIRE_APPROVAL must fire on any spend action above $100 (configurable threshold)
- Audit log must be hash-chained: every action references the hash of the previous action

**Sensitive credential handling:**

- All API keys in `.env`, never hardcoded
- `.env.example` committed, `.env` gitignored
- Stripe webhook secret validated on every incoming webhook
- C1 API calls authenticated with short-lived tokens, not long-lived secrets

### Judging Criteria Mapping

|Criterion   |How we address it                                                                     |
|------------|--------------------------------------------------------------------------------------|
|Usefulness  |Real SMB pain (SaaS spend chaos), real workflow automation, measurable savings output |
|Viability   |Usage-based business model, bookkeeper GTM channel, C1 as the enterprise control plane|
|Presentation|Clean demo arc, live GBrain visualization, savings dashboard with NemoClaw’s own fee  |

-----

## Open Questions for Agent Swarm

1. **GBrain API access:** Do we have direct access to Garry Tan's GBrain (MIT, PGLite, ships as an MCP server), or do we need to implement a compatible knowledge graph interface and mock it? If mocking, mirror the GBrain MCP contract so swapping in the real thing is a one-line change.
1. **NemoClaw SDK:** Is there a published NemoClaw SDK or does integration happen via the Hermes agent framework? Check Nous Research hackathon docs in the Discord submissions channel.
1. **Stripe Skills for Hermes:** These are new hackathon integrations. Pull the latest docs from the Stripe x Nous Research integration before implementing the payment layer.
1. **C1 sandbox:** Confirm UBP entitlement API is accessible in the dev environment. If not, mock the policy check interface with a local config file.
1. **Demo recording:** Plan for screen recording on Day 14. Have a scripted walkthrough with pre-seeded data so the demo doesn’t depend on live API calls that could fail.

-----

## Submission Copy (Draft)

**Tweet:**
“We built NemoClaw SMB Ops: an autonomous CFO agent for small businesses. Hermes orchestrates. NemoClaw executes safely. C1 governs access. Stripe pays the bills. GBrain learns the business. HTTP 402 is the trigger. Demo: [link] @NousResearch #HermesHackathon”

**Writeup:**
NemoClaw SMB Ops is a plug-and-play autonomous financial operations agent for small businesses. A Hermes agent learns your business from a single CEO conversation, monitors every vendor invoice, detects anomalies using Nemotron 3 Ultra’s reasoning, enforces spend policy via ConductorOne’s control plane, and executes payments through Stripe Skills on HTTP 402 triggers. Intuit reconciles every transaction automatically. When a vendor is overcharging, the agent finds alternatives and executes the switch end-to-end: access revoked, subscription cancelled, new tool provisioned, books updated. Business model: 0.5% of spend under management, 20% of negotiated savings. Revenue is earned by the agent, spent by the agent, and governed by the agent.

-----

*Brief version: 1.0 — June 16, 2026*  
*Repo: github.com/tronmongoose/nemoclaw-smb (initialize on Day 1)*