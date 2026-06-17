# NemoClaw SMB Ops Agent

An autonomous CFO/COO agent for small businesses. It learns the business from one
conversation, watches every vendor invoice, catches anomalies, pays bills on HTTP 402,
and negotiates switches when a vendor stops earning its price.

Built for the **Hermes Agent Accelerated Business Hackathon** (Nous Research x NVIDIA x Stripe).

## How the sponsor tech is used

| Sponsor tech | Role here |
|---|---|
| **Hermes Agent** (Nous Research) | Primary orchestrator. Every SMB-ops capability ships as a Hermes skill (agentskills.io). |
| **NemoClaw** (NVIDIA) | Safe execution harness. Skills run inside the OpenShell sandbox. No action reaches a payment API without passing the harness. |
| **Nemotron 3 Ultra** (NVIDIA) | Heavy reasoner. Fires on high-complexity tasks: vendor analysis, anomaly root cause, negotiation drafts. |
| **Stripe Skills for Hermes** | Payment execution. Auto-pay on 402, subscription up/down on a vendor switch, and the product's own revenue collection. |

Memory runs on **GBrain** (Garry Tan's self-wiring knowledge graph, MIT, MCP server). The
agent routes model calls through **ClawRouter**: routine classification stays on a small
model, heavy reasoning escalates to Nemotron 3 Ultra.

## The core loop

```
HTTP 402  ->  GBrain lookup  ->  policy check  ->  anomaly score  ->  pay (Stripe) or escalate
                (known vendor?)   (authorized?)     (in range?)        (silent)      (to CEO)
```

Every action is hash-chained into a tamper-evident audit log. Spend above a threshold
(default $100) requires approval before execution.

## Quick start

```bash
cp infra/.env.example .env        # fill keys; .env is gitignored
docker-compose -f infra/docker-compose.yml up
# UI on http://localhost:5173, API on http://localhost:8000
pytest tests/                     # core loop tests
```

Stripe runs in test mode throughout. Intuit and the full vendor-switch cascade are seeded
with fixture data for the demo so no live API can fail on camera.

## Governance plane

The control plane is built behind a swappable `policy_check` interface. By default it uses
a local config mock (`control_plane/policy_mock.yaml`). A ConductorOne client is included as
an optional backend, disabled until enabled by config.

## Status

Hackathon build. Submission due EOD Tue June 30, 2026. See `BRIEF.md` for the full
architecture and `TASKS.md` for build progress.

## License

See `LICENSE`.
