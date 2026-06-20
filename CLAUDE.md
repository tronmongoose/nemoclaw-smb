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

| Layer | Default state | Keyed/enabled upgrade | Live test? |
|---|---|---|---|
| Audit hash chain | REAL | — | no (local, deterministic) |
| Anomaly detection | REAL | — | no (local math) |
| Policy / approval / TTL | REAL | — | no (local YAML) |
| Knowledge graph | REAL (in-memory) | — | no (local) |
| NemoClaw harness | REAL | — | no (local) |
| Hermes (Nous Portal) | MOCK | LIVE-OK when `NOUS_PORTAL_API_KEY` set | yes — `test_hermes_live` |
| Nemotron (NVIDIA NIM) | MOCK | LIVE-OK when `NVIDIA_NIM_API_KEY` set (550B model, ~30–120s) | yes — `test_nemotron_live` |
| Stripe (SDK + MCP) | MOCK | LIVE-OK (test mode) when `STRIPE_SECRET_KEY=sk_test_…`; `sk_live_` refused; MCP path needs 3.11 venv + npx | yes — `test_stripe_live` |
| NeMo Guardrails | DENYLIST (built-in) | REAL LLMRails when `NEMOCLAW_GUARDRAILS=1` | yes — `test_guardrails_live` |
| Sandbox | in-process fallback | SUBPROCESS isolation when `NEMOCLAW_SANDBOX` set; OpenShell NOT used | yes — `test_sandbox_subprocess_live` |
| Baton (binary) | LIVE-OK (binary verified) | access DATA is a fixture until a connector cred (e.g. GitHub PAT) produces a real c1z | yes — `test_baton_live` (binary only) |
| ConductorOne API | LIVE-OK (graceful fallback to local policy; never crashes on missing key) | live verify needs a real C1 tenant (`C1_API_KEY` + `C1_BASE_URL`) | yes — `test_c1_policy_check_live` |
| GBrain MCP | MOCK (in-memory graph) | LIVE-OK when `GBRAIN_MCP_CMD` set; needs `npm i -g github:garrytan/gbrain` + bun | yes — `test_gbrain_live` |
| Intuit / QuickBooks | MOCK (in-memory ledger) | needs Intuit sandbox creds to go live | no falsifying test — unverified |

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
