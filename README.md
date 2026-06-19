# NemoClaw SMB Ops Agent

An autonomous CFO/COO agent for small businesses. It learns the business from one
conversation, watches every vendor invoice, catches anomalies, pays bills on HTTP 402,
and negotiates switches when a vendor stops earning its price. Every action runs through
a safe-execution harness and lands in a tamper-evident audit log.

Built for the **Hermes Agent Accelerated Business Hackathon** (Nous Research x NVIDIA x Stripe).

## How the sponsor tech is used

| Sponsor tech | Role here | Where |
|---|---|---|
| **Hermes Agent** (Nous Research) | Primary orchestrator. Parses CEO intent, plans, and drives every skill. Runs on Nous Portal. | `agent/hermes_orchestrator.py`, `agent/hermes_client.py` |
| **NemoClaw** (NVIDIA) | Safe-execution harness. No skill reaches a payment API without passing guardrail to permission to execute to audit. | `agent/nemoclaw_harness.py` |
| **Nemotron 3 Ultra** (NVIDIA) | Heavy reasoner. Vendor analysis, anomaly root cause, negotiation drafts. | `agent/nvidia_client.py`, `agent/reasoning.py` |
| **NVIDIA agent skills** | 8 skills the orchestrator calls, exportable to the NeMo Agent Toolkit. | `agent/skills/`, `agent/nat_workflow.yml` |
| **Stripe Skills for Hermes** | Payment execution via the Stripe MCP server. Buy on 402, provision a subscription on switch, collect the product's own fee. | `payments/stripe_mcp.py`, `payments/stripe_client.py` |
| **ConductorOne** | Access-governance control plane, run locally via open-source Baton. Surfaces unused-seat deprovision candidates. | `control_plane/`, `agent/skills/access_governance_skill.py` |

Memory runs on an in-process knowledge graph with a GBrain MCP seam. Model calls route
through ClawRouter: routine work stays small, heavy reasoning escalates to Nemotron 3 Ultra.

## The core loop

```
HTTP 402  ->  graph lookup  ->  policy check  ->  anomaly score  ->  pay (Stripe MCP) or escalate
              (known vendor?)   (authorized?)     (in range?)        (silent)          (to CEO)
```

Spend above a threshold (default $100) requires human approval before execution. Every
action is hash-chained (SHA-256, prev_hash to entry_hash) into a tamper-evident log that
verifies end to end.

## What is real vs mocked

Honest accounting. Every integration sits behind a seam: real when keyed, mock otherwise,
so tests and the demo always run.

| Layer | Status |
|---|---|
| Hermes orchestrator (Nous Portal) | Real, live-verified. Demo replays a captured run for determinism. |
| NemoClaw safe-execution harness | Real. |
| Nemotron 3 Ultra reasoning (NVIDIA NIM) | Real, live-verified. |
| NVIDIA agent skills (8) | Real. |
| Stripe Skills for Hermes (Stripe MCP) | Real in test mode when a `sk_test_` key + Node are present. Falls back to direct SDK, then mock. |
| ConductorOne control plane | Real and local via Baton (open source). C1 SaaS client present, default mock (tenant deferred). |
| GBrain memory | In-process graph is real. External GBrain MCP is a seam with mock fallback. |
| QuickBooks / Intuit books | Mocked. |

Reasoning-model output is stochastic, so the recorded demo replays a captured Hermes run
(`fixtures/captured/hermes_run.json`) rather than a live call. Live orchestration works and
is verified separately (see the runbook).

## Quick start

```bash
make install                       # Python deps (system Python 3.9 path)
make dev                           # API on http://localhost:8000 (seeded on startup)
cd ui && npm install && npm run dev  # dashboard on http://localhost:5173
make demo                          # deterministic end-to-end run on seed data
make test                          # 197 tests
```

The dashboard reads the live API (`VITE_API_BASE`, default `http://localhost:8000`). It
fails soft to empty states when the API is down.

### Going live (optional)

Drop keys in `.env` (gitignored). Each activates its real path:

- `NOUS_PORTAL_API_KEY` — Hermes orchestration on Nous Portal (already wired and verified).
- `STRIPE_SECRET_KEY=sk_test_...` — Stripe MCP path (buy / provision / pay). Needs Node + the
  3.11 venv where `mcp` is installed (`uv run` or `.venv/bin/python`). See `docs/stripe_onboarding.md`.
- `C1_API_KEY` — ConductorOne SaaS backend. Default stays on local Baton.

## API

`GET /health`, `GET /graph`, `GET /graph/vendors`, `GET /invoices`, `GET /invoices/anomalies`,
`GET /approvals/pending`, `POST /approvals/{id}/decide`, `GET /savings/summary`,
`GET /savings/alternatives`, `GET /audit`, `POST /webhooks/402`, `POST /webhooks/stripe`.

CORS is open for the dashboard. The app seeds a coherent demo state on startup (loads
invoices, runs the Adobe anomaly 402 once, leaves one pending approval and a valid audit chain).

## Runtime note

Tests, the demo, and the API run on system **Python 3.9**. The live Stripe MCP path needs
the **Python 3.11 venv** (`.venv/`, where the `mcp` client is installed) plus Node. This
split is intentional and documented; the 3.9 path always works because the `mcp` import is
lazy and guarded.

## Status

Hackathon build. Submission due EOD Tue June 30, 2026. Architecture in `BRIEF.md`, build
log in `TASKS.md`, demo script in `docs/submission.md`, run-day steps in `docs/demo_runbook.md`.

## License

See `LICENSE`.
