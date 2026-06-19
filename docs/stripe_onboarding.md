# Stripe Onboarding for NemoClaw

## 1. Get a Test Key

**Option A — Stripe Dashboard (fastest)**

1. Sign in at dashboard.stripe.com.
2. Toggle the "Test mode" switch (top-right).
3. Go to Developers > API keys.
4. Copy the Secret key starting with `sk_test_`.
5. Add to `.env`:

```
STRIPE_SECRET_KEY=sk_test_...
```

`payments/stripe_client.py` reads this variable at call time. Any key that does not begin with `sk_test_` is refused; a `sk_live_` key logs a warning and falls back to mock.

**Option B — Stripe CLI sandbox (keyless)**

```bash
stripe sandbox create          # creates an isolated sandbox
stripe login                   # authenticates the CLI
stripe listen --forward-to localhost:8000/webhooks/stripe  # optional: forward events
```

`stripe sandbox create` is documented at docs.stripe.com/building-with-ai. It provisions a fresh test environment without needing a Dashboard account first.

---

## 2. Stripe Skills for Hermes via MCP

NemoClaw routes `pay`, `create_subscription`, and `collect_fee` through the Stripe
MCP server when `STRIPE_SECRET_KEY` is a `sk_test_` key and `npx` is on PATH.
This is the "Stripe Skills for Hermes" path. Set `STRIPE_FORCE_SDK=1` to force
the direct SDK path; leave `STRIPE_SECRET_KEY` unset to use the mock path.

### Backend preference order

1. **MCP** — `npx @stripe/mcp` proxying `mcp.stripe.com` (this section).
   Active when: `npx` on PATH + `STRIPE_SECRET_KEY=sk_test_*` + `STRIPE_FORCE_SDK` not set.
   Result dict includes `"backend": "mcp"`.
2. **SDK** — direct `stripe-python` SDK calls.
   Active when: MCP is off/unavailable + `STRIPE_SECRET_KEY=sk_test_*`.
   Result dict includes `"backend": "sdk"`.
3. **Mock** — deterministic sha256 ids, no network.
   Active when: no key or all live paths fail.
   Result dict includes `"backend": "mock"`.

### Register the Stripe MCP server into Hermes

**Local stdio (recommended for hackathon — uses your Restricted API Key)**

```bash
# The @stripe/mcp server reads STRIPE_SECRET_KEY from env or --api-key flag.
# --tools flag was removed in v0.3.0; scope is controlled by your RAK.
# Verified CLI flags (v0.3.3): --api-key, --stripe-account (no --tools).
hermes mcp add stripe \
  --command "npx" \
  --args "-y @stripe/mcp --api-key=sk_test_..." \
  --transport stdio
```

Or as a JSON entry in your Hermes MCP config (`~/.hermes/mcp.json` or equivalent):

```json
{
  "mcpServers": {
    "stripe": {
      "command": "npx",
      "args": ["-y", "@stripe/mcp", "--api-key=sk_test_..."],
      "transport": "stdio"
    }
  }
}
```

**Remote OAuth (no local process, no key in config)**

```bash
hermes mcp add stripe --url https://mcp.stripe.com --transport streamable-http
```

The remote server authenticates via OAuth — no key passed to the client.
Reference: docs.stripe.com/mcp#remote-server.

### How NemoClaw routes payments through MCP

`payments/stripe_mcp.py` wraps the Python `mcp` SDK (`mcp>=1.0`) with:

- `stripe_mcp_enabled()` — gate check (npx + sk_test_ + not STRIPE_FORCE_SDK)
- `call_tool(name, arguments)` — sync stdio MCP session, one tool call, returns parsed dict
- `mcp_pay(amount_cents, currency, metadata)` — calls `create_payment_intent`
- `mcp_create_subscription(vendor, amount_cents)` — calls `create_product` -> `create_price`
  -> `create_customer` -> `create_subscription` in sequence
- `mcp_collect_fee(amount_cents, metadata)` — calls `create_payment_intent` with fee metadata

`payments/stripe_client.py` calls `stripe_mcp_enabled()` at the top of `pay`,
`create_subscription`, and `collect_fee` and routes through MCP first.

### Verified Stripe MCP tool names (mcp.stripe.com, 2026-06)

The `@stripe/mcp` server (v0.3.3) is a pure stdio proxy to `mcp.stripe.com`.
Tool permissions are granted by the Restricted API Key (RAK) scope — not by a
local flag. The following tool names are exposed by the remote server:

| Tool name | Purpose |
|---|---|
| `create_payment_intent` | Create a PaymentIntent (our `pay` path) |
| `confirm_payment_intent` | Confirm a PaymentIntent (separate step if not auto-confirmed) |
| `retrieve_payment_intent` | Fetch a PaymentIntent by id |
| `list_payment_intents` | List PaymentIntents |
| `create_customer` | Create a Customer (our `create_subscription` step 3) |
| `retrieve_customer` | Fetch a Customer by id |
| `list_customers` | List Customers |
| `create_product` | Create a Product (our `create_subscription` step 1) |
| `retrieve_product` | Fetch a Product by id |
| `list_products` | List Products |
| `create_price` | Create a Price (our `create_subscription` step 2) |
| `retrieve_price` | Fetch a Price by id |
| `list_prices` | List Prices |
| `create_subscription` | Create a Subscription (our `create_subscription` step 4) |
| `retrieve_subscription` | Fetch a Subscription by id |
| `cancel_subscription` | Cancel a Subscription |
| `list_subscriptions` | List Subscriptions |
| `retrieve_balance` | Fetch account balance |
| `list_charges` | List Charges |
| `create_refund` | Issue a Refund |

#SUGGEST_VERIFY: connect with a live `sk_test_` key and call `tools/list` via
the MCP session to confirm the exact tool set against your RAK permissions.
The remote server may add or rename tools as the Stripe MCP surface evolves.

### CLI flags verified (npx @stripe/mcp v0.3.3)

```
Accepted arguments: api-key, stripe-account
Note: --tools flag was removed in v0.3.0. Tool permissions are now controlled
by your Restricted API Key (RAK). Create a RAK with the desired permissions at
https://dashboard.stripe.com/apikeys
```

### Keyless sandbox option

```bash
stripe sandbox create   # provisions a fresh Stripe test environment
stripe login            # authenticates the CLI
```

`stripe sandbox create` is documented at docs.stripe.com/building-with-ai.
It provisions a fresh test environment without a Dashboard account.

---

## 3. Local MCP Server (legacy section — superseded by section 2)

The original entry point `npx @stripe/mcp --api-key=sk_test_...` still works;
the `--tools` flag logged in earlier doc drafts has been removed upstream.
See section 2 for the current integration pattern.

---

## 3. Stripe Agent Skills (4 available)

These are Stripe-published prompt/skill packages for AI agents:

| Skill | Purpose |
|---|---|
| `stripe-best-practices` | Guardrails for safe Stripe API usage in agent contexts |
| `stripe-directory` | Catalog of all Stripe products and which API resources map to which use case |
| `stripe-projects` | Project scaffolding helpers (set up keys, webhooks, test data) |
| `upgrade-stripe` | Migration guides for breaking SDK version changes |

Source: docs.stripe.com/building-with-ai#agent-skills.

---

## 4. NemoClaw Path to Stripe SDK Call Mapping

| NemoClaw path | Function | Stripe SDK call (live branch) |
|---|---|---|
| Buy (HTTP-402 auto-pay) | `pay(vendor, amount, idempotency_key)` | `stripe.PaymentIntent.create(amount=cents, currency="usd", payment_method="pm_card_visa", confirm=True, automatic_payment_methods={"enabled":True,"allow_redirects":"never"})` |
| Provision (vendor switch) | `create_subscription(vendor, amount)` | `stripe.Product.create(name=...)` + `stripe.Price.create(unit_amount=cents, currency="usd", recurring={"interval":"month"})` + `stripe.Customer.create(...)` + `stripe.Subscription.create(customer=id, items=[{"price":price_id}])` |
| Pay for service (0.5% fee) | `collect_fee(amount, basis)` | `stripe.PaymentIntent.create(amount=cents, currency="usd", payment_method="pm_card_visa", confirm=True, metadata={"fee_type":"nemoclaw_platform_fee"})` |
| Cancel old vendor | `cancel_subscription(vendor)` | Mock only (requires stored subscription id — see `#COMPLETION_DRIVE` in source) |

All amounts are in dollars at the function boundary; cents conversion (`int(round(amount * 100))`) happens inside `stripe_client.py`.

---

## 5. Verified Doc References

- Stripe Python SDK (v9+): https://docs.stripe.com/api?lang=python
- PaymentIntent create: https://docs.stripe.com/api/payment_intents/create
- Subscription create: https://docs.stripe.com/api/subscriptions/create
- Test payment methods (`pm_card_visa`): https://docs.stripe.com/testing#cards
- MCP server: https://docs.stripe.com/mcp
- Building with AI / sandbox / agent skills: https://docs.stripe.com/building-with-ai

#SUGGEST_VERIFY: confirm `@stripe/mcp` npm package name against npmjs.com before using in production — package names in early MCP tooling have shifted.
