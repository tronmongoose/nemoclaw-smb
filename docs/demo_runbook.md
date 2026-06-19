# Demo Runbook

Run-day steps. Three terminals plus a browser. Everything below works offline on seed data.

## Pre-flight (once)

```bash
cd ~/projects/nemoclaw-smb
make install
cd ui && npm install && cd ..
make test          # expect: 197 passed
```

## Run the demo

**Terminal 1 — API (seeded backend):**
```bash
make dev
# http://localhost:8000 — seeds on startup: invoices loaded, Adobe anomaly 402 run once,
# one pending approval, valid audit chain
```

**Terminal 2 — dashboard:**
```bash
cd ui && npm run dev
# http://localhost:5173
```
Open the browser. You should see: the vendor knowledge graph, the invoice feed with the
Adobe row flagged, the approval queue showing Adobe $340, and the savings panel with the
NemoClaw fee line.

**Terminal 3 — narrated loop:**
```bash
make demo
```
This prints the 6-scene arc: Hermes orchestration (replayed), the Adobe anomaly + Baton seat
finding, Nemotron alternatives, the vendor switch, the AWS auto-pay through the NemoClaw
pipeline, and the closing savings + audit verification.

## The live moment (on camera)

Approve the Adobe item in the dashboard (or via API):
```bash
curl -s localhost:8000/approvals/pending          # grab the id
curl -s -X POST localhost:8000/approvals/<id>/decide \
  -H 'content-type: application/json' \
  -d '{"approved": true, "decided_by": "ceo"}'
curl -s 'localhost:8000/audit?limit=5'            # chain grew, verify.ok still true
```

## Optional: prove live Hermes orchestration

Stochastic, so do this off-camera or accept variance. Needs `NOUS_PORTAL_API_KEY` in `.env`.
```bash
python3 -c "
import os
for line in open('.env'):
    line=line.strip()
    if line and not line.startswith('#') and '=' in line:
        k,v=line.split('=',1); os.environ.setdefault(k.strip(),v.strip())
from agent.hermes_orchestrator import orchestrate
r=orchestrate('Review this month invoices for overspend and decide whether to approve the AWS renewal.', max_steps=6)
print([(s['skill'],s['outcome']) for s in r['steps']]); print(r['final'][:200])
"
```

## Optional: prove live Stripe (test mode)

Needs `STRIPE_SECRET_KEY=sk_test_...` and Node. Use the 3.11 venv (where `mcp` is installed):
```bash
.venv/bin/python -c "from payments import stripe_client as s; print(s.pay('AWS', 50.0, 'demo').get('backend'))"
# 'mcp' when the Stripe MCP server reaches mcp.stripe.com; 'sdk' if MCP unavailable; 'mock' with no key
```
To register Stripe Skills into the Hermes runtime itself: see `docs/stripe_onboarding.md`
(`hermes mcp add`).

## Troubleshooting

- **Dashboard empty:** API not running or wrong port. Check Terminal 1, confirm
  `curl localhost:8000/health`.
- **`make demo` shows `[live-mock]` instead of `[replay]`:** the capture file is missing.
  It is committed at `fixtures/captured/hermes_run.json`; the live-mock path is still correct,
  just non-deterministic.
- **`mcp` import error on system Python:** expected. System Python is 3.9; the Stripe MCP
  live path uses the 3.11 venv. Tests and demo do not need it.
- **Audit chain says not ok:** re-run `make dev` to reseed; the demo chain is rebuilt on
  startup.

## One-line pitch

An autonomous CFO that watches every invoice, pays through Stripe, escalates what looks
wrong, deprovisions what nobody uses, and charges 0.5% for the service. Governed path,
fast path. Every action audited.
