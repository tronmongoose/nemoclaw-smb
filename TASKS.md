# Build Tasks — NemoClaw SMB Ops Agent

Demo-first. Real: Hermes orchestration, Stripe Skills (test mode), one visible Nemotron 3
Ultra reasoning task, GBrain memory, NemoClaw sandbox, hash-chained audit. Mocked with seed
data: Intuit reconciliation, full vendor-switch cascade, the "402 in the wild" webhook.

## Phase 0 — Scaffold (done)
- [x] Repo tree, git init, .gitignore, .env.example, README, LICENSE, BRIEF.md (corrected)
- [x] pyproject / requirements, docker-compose skeleton

## Phase 1 — Port wave (LIFT/ADAPT from bjornswarm + carryall)
- [ ] `agent/claw_router.py` — LIFT from `bjornswarm/pipelines/clawrouter.py`. Swap backends
      for Hermes-small (routine) vs Nemotron 3 Ultra (heavy). Keep complexity scoring.
- [ ] `agent/audit_log.py` — LIFT hash chain from `bjornswarm/coding_harness/security/audit.py`.
      Entry payload = spend/approval/access actions. `verify_chain()` must pass.
- [ ] `agent/require_approval.py` — ADAPT carryall `constraints.py`/`approvals.py` +
      `bjornswarm/pipelines/quality_gate.py`. Add `spend_threshold` (amount > $100).
- [ ] `gbrain/invoice_ingestion.py` — LIFT recurring-charge + categorization from
      `bjornswarm/pipelines/subscription_import.py`.
- [ ] `gbrain/anomaly_detector.py` — REFERENCE z-score from `bjornswarm/pipelines/granite_categorize.py`.
      Group by vendor; mean + 2 std baseline, Nemotron-enhanced reasoning on flagged items.

## Phase 2 — Integration glue + skill pack
- [ ] `agent/skills/` — Hermes skill wrappers (agentskills.io): onboarding, invoice-ingest,
      anomaly-detect, vendor-analyze, 402-handler, approval-gate, audit.
- [ ] `agent/nemoclaw_harness.py` — sandbox wiring; all skill execution routes through it.
- [ ] `payments/stripe_client.py` + `payments/payment_402_handler.py` — Stripe Skills;
      FastAPI 402 webhook listener; ≥2 Stripe actions (auto-pay, subscription change).
- [ ] `payments/intuit_reconciler.py` — mocked, seed-data backed.
- [ ] `gbrain/knowledge_graph.py` + `gbrain/onboarding.py` — GBrain MCP client (real) with
      local-contract mock fallback.
- [ ] `control_plane/policy_check.py` (interface) + `policy_mock.yaml` + `c1_client.py`
      (optional, disabled until C1 blessing).
- [ ] `procurement/vendor_analyzer.py` + `negotiation_drafter.py` + `vendor_switcher.py`
      (switcher mocked cascade for demo).
- [ ] `api/main.py` FastAPI + routes (onboarding, invoices, approvals, webhooks).

## Phase 3 — UI
- [ ] Force-graph knowledge graph (ADAPT `bjornswarm` D3 `VaultTab.tsx`).
- [ ] Invoice feed + anomaly flags, approval modal (full context), savings dashboard
      with NemoClaw's own fee line.

## Phase 4 — Seed data + demo + verify
- [ ] `fixtures/` — 12-person design studio (Adobe/Figma/AWS/Gusto); Adobe +23% anomaly;
      Affinity alternative; scripted 402.
- [ ] `tests/` — test_402_handler, test_anomaly_detector, test_policy_check, test_vendor_switcher.
- [ ] End-to-end demo dry-run (6-scene arc), zero live-API dependency.
- [ ] Demo video script + submission writeup draft. C1 copy gated on blessing.

## Owner-blocked (Erik)
- [ ] C1 blessing before shipping C1 code or "ConductorOne UBP" copy publicly.
- [ ] Confirm Hermes/NIM/Stripe-test/Intuit-sandbox/GBrain access (BRIEF open-Qs).
- [ ] Nous Discord submissions channel + form link for Day-14 submit.
