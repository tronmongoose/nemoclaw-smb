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

## 2. Local MCP Server for Hermes Runtime Tools

Stripe publishes an MCP server that exposes Stripe's API as tool calls. Two deployment modes:

**Local (npx, recommended for hackathon)**

```bash
npx @stripe/mcp --tools=all --api-key=sk_test_...
```

Common tool subsets:
- `--tools=payment_intents` — pay path only
- `--tools=subscriptions,products,prices` — provision path
- `--tools=all` — full surface

The server listens on stdio by default. Point Hermes (or Claude Desktop) at it via the MCP client config. Reference: docs.stripe.com/mcp.

**Remote OAuth (no local process)**

Add the remote server to your MCP client config:

```json
{
  "mcpServers": {
    "stripe": {
      "command": "npx",
      "args": ["-y", "@stripe/agent-toolkit"],
      "env": { "STRIPE_SECRET_KEY": "sk_test_..." }
    }
  }
}
```

Or connect via `https://mcp.stripe.com` using OAuth — the remote server handles auth without passing a key to the client. Reference: docs.stripe.com/mcp#remote-server.

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
