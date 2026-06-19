# CLAUDE.md — NemoClaw SMB Ops Agent

Guidance for agents working in this repo. Read this before editing or making claims about
what the project does.

## What this is

An autonomous CFO/COO agent for small businesses, built for the Hermes Agent Accelerated
Business Hackathon (Nous Research x NVIDIA x Stripe). It learns a business from a profile,
watches vendor invoices, scores anomalies, pays in-range bills on HTTP 402, escalates the
rest, and can switch vendors. Every action is hash-chained into a tamper-evident audit log,
and spend over a threshold needs human approval.

Repo root is `~/projects/nemoclaw-smb`. It is NOT `~/projects/bjornswarm` — if `make dev`
or `make demo` reports "No rule to make target", you are in the wrong directory.

## The one rule that matters here: no overclaiming

This project was once described as "all real / live-verified" when most sponsor integrations
were mock-by-default code that no test exercised live. Do not repeat that.

- A claim that an integration is "live", or that "every action" does X, must be backed by a
  test in `tests/live/` that actually hits the real path and FAILS if it breaks. No falsifying
  test → downgrade the claim to honest specifics.
- `make reality` is the source of truth. Run it; quote it; do not assert status from memory.
- The offline suite proves local logic and mock shape. It does NOT prove any live integration.

## Reality matrix (run `make reality` to refresh — counts here drift)

| Layer | Status | Notes |
|---|---|---|
| Audit hash chain | REAL | SHA-256 prev_hash→entry_hash, `verify_chain` from genesis. `agent/audit_log.py` |
| Anomaly detection | REAL | z-score math, `gbrain/anomaly_detector.py` |
| Policy / approval / TTL | REAL | local YAML policy + deterministic approval gate |
| Knowledge graph | REAL | in-memory, `gbrain/knowledge_graph.py` |
| NemoClaw harness | REAL | guardrail → approval → execute → audit; the single payment chokepoint |
| Hermes (Nous Portal) | LIVE-OK | real call when `NOUS_PORTAL_API_KEY` set; `tests/live` proves it |
| Nemotron (NVIDIA NIM) | LIVE-OK | real call when `NVIDIA_NIM_API_KEY` set (550B model is slow, ~30–120s) |
| Stripe (SDK + MCP) | LIVE-OK (test mode) | real test-mode calls when `STRIPE_SECRET_KEY=sk_test_…`; `sk_live_` refused. SDK + Stripe MCP backends; mock fallback |
| NeMo Guardrails | REAL (opt-in) | real `LLMRails` check when `NEMOCLAW_GUARDRAILS=1`; built-in denylist otherwise |
| Sandbox | SUBPROCESS | real subprocess isolation for JSON-serializable skills when `NEMOCLAW_SANDBOX` set; in-process fallback for rich objects. OpenShell is NOT installed/used |
| Baton (binary) | LIVE-OK | `baton` 0.4.5 installed; access-grant DATA still uses a fixture until a connector cred (e.g. a GitHub PAT) produces a real c1z |
| ConductorOne API | BUILD-TO-SPEC | real client to the public C1 API; live verify needs a tenant. Graceful fallback to local policy, never crashes on key |
| GBrain MCP | WIRED, LIVE-DEFERRED | real client behind `GBRAIN_MCP_CMD`; needs `npm i -g github:garrytan/gbrain` (user-gated) + bun. In-memory graph is the default and the source of truth |
| Intuit / QuickBooks | MOCK | in-memory ledger; needs Intuit sandbox creds to go live |

## Architecture

- `agent/hermes_orchestrator.py` + `hermes_client.py` — Hermes is the primary orchestrator
  (Nous Portal). Bounded loop; dispatches skills through the harness.
- `agent/nemoclaw_harness.py` — safe-execution chokepoint. All spend now routes here
  (`payments/payment_402_handler.py` calls `execute()`, not Stripe directly).
- `agent/skills/` — 9 skills (onboarding, invoice_ingest, anomaly_detect, vendor_analyze,
  handle_402, approval_gate, audit, access_governance, pay_invoice).
- `agent/nvidia_client.py` + `reasoning.py` — Nemotron heavy reasoning.
- `payments/stripe_client.py` + `stripe_mcp.py` — buy/provision/pay; MCP preferred → SDK → mock.
- `control_plane/policy_check.py` + `c1_client.py` — policy gate; C1 backend with safe fallback.
- `control_plane/baton_client.py` — access governance via Baton (local, open source).
- `gbrain/` — knowledge graph + anomaly detector + the GBrain MCP client.
- `api/` — FastAPI; seeds a demo state on startup. `ui/` — dark dashboard (Vite/React).
- `verification/reality_report.py` — the honest status probe. `tests/live/` — falsifying tests.

## Hard constraints (from the brief — keep true)

- All spend actions pass through `nemoclaw_harness.execute()`. No direct payment API calls.
- Approval fires on spend over `SPEND_APPROVAL_THRESHOLD` (default 100).
- The audit log is hash-chained and must verify (`make audit` / `verify_chain`).
- Stripe is test-mode only; `sk_live_` keys are refused in code.
- No ConductorOne work-tenant data ever — synthetic SMB data only.

## Running it

```
make dev        # API on :8000 (seeds demo state)
cd ui && npm install && npm run dev   # dashboard on :5173
make demo       # deterministic end-to-end (replays a captured Hermes run)
make test       # offline suite (proves logic + mock shape; live tests skip)
make reality    # the live status matrix — the honest source of truth
python3 -m pytest -m live   # live falsifying tests (need keys; skip cleanly otherwise)
```

Runtime split: tests/demo/API run on system Python 3.9. The Stripe MCP and `mcp`-dependent
paths use the 3.11 `.venv`. Keys live in `.env` (gitignored). A hook may block editing `.env`
from an agent — set keys yourself.

## More

- `ANALYSIS.md` — what it does, value thesis, and intent-fidelity (did the brief survive).
- `docs/submission.md` — hackathon writeup + demo script. `docs/demo_runbook.md` — run-day steps.
- `docs/stripe_onboarding.md` — Stripe MCP / sandbox setup.
