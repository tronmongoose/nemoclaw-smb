# AUDIT.md: fake vs real accounting for the three-act STR demo

This is the honest ledger. The project rule is "no overclaiming" (see `CLAUDE.md`).
`make reality` is the runtime source of truth and `tests/live/` are the falsifying
tests; this document explains what those tools prove and where the demo deliberately
stops short of live calls. Run them rather than trusting prose. Counts here drift.

## 1. The blunt answer on the keys

`NOUS_PORTAL_API_KEY` (Hermes / Nous Portal) and `NVIDIA_NIM_API_KEY` (Nemotron via
NVIDIA NIM) are stored in `.env` and they work. Proof, not assertion:

- `make reality` prints `Hermes LIVE-OK` and `Nemotron LIVE-OK`, each with a real
  `PONG` response from a live API round-trip (`verification/reality_report.py`
  `probe_hermes` / `probe_nemotron`).
- `tests/live/test_live_integrations.py` exercises the same path:
  `test_hermes_live` and `test_nemotron_live` hit the real endpoint and FAIL if the
  key is missing or the call breaks (they skip cleanly when the key is unset).

But the three-act DEMO does not call them. `make str-demo` runs with `DEMO_MODE=true`,
which makes both reasoning paths return a deterministic, cached trace instead of an
API call:

- `acts/str_owner_agent.py` `_reasoning_trace()` returns a `[DEMO cached trace]` string
  when `demo_mode()` is true. The `model_used` field is a label only.
- `skills/dynamic_pricing_skill.py` `_demo_reasoning_trace()` returns a
  `[model/demo-cached]` string when `demo_mode()` is true.

So three surfaces exercise the keys: the new LIVE toggle (`DEMO_MODE=false`),
`make reality`, and `tests/live/`. The default demo run does not. That is by design,
for a reproducible, credential-free, offline demo. It is also exactly the kind of gap
this document exists to make explicit.

## 2. Component-by-component status

Legend:

- REAL: deterministic local logic or a verified local primitive. No network, no mock.
- DEMO-MOCK: the integration is mocked and labeled `backend="mock"`; audit entries are
  written as if real, but no funds move and no live API is called.
- REAL-WHEN-KEYED: deterministic local logic by default; routes to a live API call when
  a key is present and the LIVE toggle is set.

| Component | Status | Where | Notes |
|---|---|---|---|
| Anomaly math (management-fee overcharge) | REAL | `acts/str_owner_agent.py` `detect_fee_anomaly` | Expected vs charged fee from contract terms; deterministic; no LLM dependency for the math itself. |
| Ed25519 Carryall envelopes | REAL | `payments/envelopes.py` `sign_stripe_envelope` / `sign` / `verify` | Real `cryptography` Ed25519 sign + verify. Uses `authority_runtime` (Carryall) if installed, else a thin Ed25519 signer. Envelope written to the audit log before any Stripe call. |
| SHA-256 audit chain | REAL | `agent/audit_log.py` `append_action` / `verify_chain`; probed by `reality_report.probe_audit_chain` | Hash-chained log; `make audit` / `verify_chain` verifies end to end. Demo run verifies VALID. |
| REQUIRE_APPROVAL gate | REAL | `agent/require_approval.py` `enforce_spend` / `decide`; `acts/str_owner_agent.py` `trigger_payment` | Fires on spend over the threshold ($500 / 50000 cents) and blocks execution by raising `ApprovalRequired`. Demo simulates the approve inline; production caller catches and retries. |
| AEO rubric (non-demo listings) | REAL | `skills/aeo_skill.py` `_run_rubric` + the four `_score_*` helpers | Deterministic 4-dimension scoring (structure / parseability / description / conflict-free), 25 pts each. Pelican Cottage scores ~91/100 through this live rubric (`tests/test_aeo.py::test_pelican_score_above_85`). |
| AEO score for Sweet Clementine | REAL (rubric-computed) | `skills/aeo_skill.py` `_run_clementine` -> `_score_dimensions` | The overall score is the rubric sum of the four dimensions scored against Sweet Clementine's degraded input (`_CLEMENTINE_DEGRADED_SCHEMA` + `_CLEMENTINE_DEGRADED_AMENITIES`), landing about 51/100 in the 45 to 57 band. The canonical JSON-LD, the dog-only `pet_species_conflict` CRITICAL flag, and the optimized opening are the remediation artifacts attached to the result, not the score. Proven by `tests/test_aeo.py::test_clementine_score_is_rubric_computed` and `::test_clementine_score_not_hardcoded_constant`. |
| HTTP-402 loop | REAL | `payments/mpp_server.py` `/price` + `/aeo-audit` | 402-with-`WWW-Authenticate` then 200-with-token cycle is implemented and driven end to end in Act 3 via FastAPI TestClient. Earn events written to the hash chain. |
| Control plane (Baton .c1z + Carryall grant-matching) | REAL (grant-matched by default) | `control_plane/c1_governance.py` `authorize`; `control_plane/c1z_fixtures/`; `control_plane/baton_client.py` `fetch_access` | `authority_runtime` and `carryall_baton` are installed, so `authorize()` routes through `carryall_baton.BatonBackend.check_access` against a bundled `.c1z` and returns `source="baton-carryall"` with a real grant match (verified: principal `str-platform-agent` has `str:price`). No ConductorOne SaaS dependency: a missing C1 tenant is not a blocker. Point `CARRYALL_BATON_C1Z` at a connector-produced `.c1z` to swap in live grants. Falls back to a synthetic `policy_check` decision (`source="synthetic"`) only when the package or c1z is absent; never raises. The entitlement DATA is synthetic; no PANW/C1 work-tenant data. NHI issuance is local, labeled `conductorone-synthetic-demo`. |
| Dynamic pricing math | REAL | `skills/dynamic_pricing_skill.py` `recommend_price` + the `_*_multiplier` / `_blend_rate` / `_confidence` helpers | Deterministic blend of occupancy band, season, events, comp-set median, day-of-week. |
| Dynamic pricing reasoning trace | REAL-WHEN-KEYED (LIVE-when-toggled) | `skills/dynamic_pricing_skill.py` `_demo_reasoning_trace` | Cached string in `DEMO_MODE=true`; calls `call_nemotron` (NVIDIA NIM) when `DEMO_MODE=false` and the key is present. |
| Anomaly reasoning trace | REAL-WHEN-KEYED (LIVE-when-toggled) | `acts/str_owner_agent.py` `_reasoning_trace` | Cached string in `DEMO_MODE=true`; routes to the Nemotron path when `DEMO_MODE=false`. The anomaly math is REAL regardless. |
| Stripe Issuing (cleaner cards) | DEMO-MOCK | `payments/issuing.py` | `backend="mock"`; deterministic mock card id; Carryall envelope signed first; audit written as if real. |
| Stripe Connect (owner accounts) | DEMO-MOCK | `payments/connect.py` | `backend="mock"`; mock connected-account id. |
| Stripe Global Payouts (crew) | DEMO-MOCK | `payments/payouts.py` | `backend="mock"`; mock transfer id; audit written as if real. |
| Metronome UBP (owner invoices) | DEMO-MOCK | `payments/metronome.py` | Invoice math is real; the Metronome API write is mocked (`backend="mock"`). |
| Stripe money movement (Act 1 reconciliation) | DEMO-MOCK, test-mode only | `payments/stripe_client.py` `pay`; `_is_live_key` | All writes mocked in `DEMO_MODE`; `sk_live_` keys are refused in code; live path is test-mode (`sk_test_`) only. No real funds move. |
| MPP token validation | DEMO prefix check | `payments/mpp_server.py` `validate_mpp_token` | A token is accepted iff it starts with `mpp_tok_`. There is no real Stripe-MPP settlement or webhook verification; the production branch is a stub (`#COMPLETION_DRIVE`). |

## 3. The path to real

Two switches turn the labeled-mock surfaces into live calls. Neither moves real money.

1. The LIVE toggle: `DEMO_MODE=false`. With the keys in `.env`, this flips
   `config/demo_mode.py` `demo_mode()` to false, so the dynamic-pricing reasoning trace
   and the anomaly reasoning trace stop returning cached strings and call the live
   Nemotron / Hermes APIs through `agent/nvidia_client.py` and `agent/hermes_client.py`.
   `make reality` and `tests/live/` already prove those calls succeed today. (The older
   single-business demo in `fixtures/demo_runner.py` has its own
   `NEMOCLAW_LIVE_REASONING=1` toggle for the same effect on its vendor-analysis step.)

2. A real-credential c1z for the control plane. The grant-matching ENGINE is already
   live by default: `authorize()` runs `carryall_baton.BatonBackend.check_access`
   against the bundled `.c1z` and returns `source="baton-carryall"`. To make the
   entitlement DATA real, set `CARRYALL_BATON_C1Z` to a `.c1z` produced by a Baton
   connector run with a live credential (for example a GitHub PAT); `authorize()` then
   grant-matches against real entitlements, and `access_inventory()` (the unused-seat
   findings and seat summaries via `control_plane/baton_client.py` `fetch_access`)
   reflects real access. The `baton` binary is already verified live (`make reality`
   shows `Baton LIVE-OK`); only the access DATA is synthetic until a real c1z is supplied.

Stripe is intentionally NOT on this path for the demo. See section 4.

## 4. Stripe stays test-mode and DEMO-mocked

This is deliberate and stays that way for the demo. Stripe Issuing, Connect, Global
Payouts, Metronome UBP, the Act 1 reconciliation PaymentIntent, and MPP settlement are
all DEMO-MOCK: they log every action to the hash-chained audit log as if real, but no
live Stripe API call is made and no funds move. Each mock path is labeled
`backend="mock"` in its module. The live Stripe path that does exist is test-mode only:
`payments/stripe_client.py` refuses any `sk_live_` key via `_is_live_key`, and
`make reality` reports `Stripe-SDK HOLLOW` (refused) if a live key is ever present. No
real charge, transfer, card, or payout is created by this project.

## 5. Note on the Sweet Clementine score

Sweet Clementine's overall AEO score is rubric-computed, not a hardcoded constant.
`audit_listing` routes the Clementine URL/text to `_run_clementine`, which scores a
degraded-input request (`_CLEMENTINE_DEGRADED_SCHEMA` + `_CLEMENTINE_DEGRADED_AMENITIES`)
through the same four `_score_*` helpers every other listing uses, then sums them (lands
about 51/100). What is canonical for the demo is the REMEDIATION output attached to the
result: the proposed JSON-LD, the dog-only `pet_species_conflict` CRITICAL flag, and the
optimized opening. The score itself moves when the input changes
(`tests/test_aeo.py::test_clementine_score_not_hardcoded_constant`), and the four
dimensions sum to the overall (`::test_clementine_score_is_rubric_computed`). The same
rubric scores every other listing (Pelican about 91/100).
