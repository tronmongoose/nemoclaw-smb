# NemoClaw STR — 2.5 minute demo run-of-show

The one idea: **one governed agent, three scales, real models and money rails.** Owner to Company
to Swarm, the page temperature shifts warm to cool to electric as the scale grows.

Sponsors on screen: **NVIDIA** (Nemotron reasoning), **Nous Research** (Hermes), **Stripe**
(Issuing, Connect, Metronome, HTTP-402), **C1** (governance, scoped NHIs).

## Pre-flight (do this before you hit record)

1. Start the API on the fast model and warm the cache so every load is instant and LIVE-badged:
   ```
   NEMOTRON_MODEL=nvidia/nemotron-3-super-120b-a12b HERMES_MODEL=nousresearch/hermes-4-70b \
     python3 -m uvicorn api.main:app --port 8000
   cd ui && npm run dev
   python3 /tmp/prewarm.py        # fills the live cache (real Nemotron + Hermes calls)
   ```
2. Open `http://localhost:5173` full screen. Confirm the top toggle reads **LIVE** (cyan).
3. Optional flagship shot: to show a fresh model call mid-demo, append `?fresh=true` to a console
   action by hand, or accept the cached instant result (already real, already LIVE-labeled).

## Run of show (~2:40)

### 0:00 - 0:25 — Owner: the hook
- Land on **01 Owner** (warm sand). Pier behind the hero.
- Beat: "I own one short-term rental in Oceanside. I am terrible at the books."
- Point at the live card: **Income $4,200 / Mgmt fee $924 / Net $3,276**, "Clawdia caught a $84
  overcharge." Note the **AGENT LIVE** dot.
- Click **Enter the owner console**.

### 0:25 - 0:50 — Owner: the proof
- The reconciliation agent caught a **$84 management-fee overcharge** (22% charged vs 20% contract).
- Point at the **LIVE nemotron** badge on the reasoning. This is a real NVIDIA Nemotron call.
- Point at **C1 NHI** (scoped identity) governing the correction payment, and the **audit chain**.
- Beat: "It reads the statement before I do, holds the correction for my approval, and logs everything."

### 0:50 - 1:20 — Company: scale up
- Click **02 Company**. The whole page cools to dark slate. "Same agent, now a property manager."
- Live card: **5 properties / 3 owners / $14,600 monthly**, agents working in the feed.
- Scroll the console: **Stripe Issuing** single-use cleaner card per checkout, **Connect + Global
  Payouts** crew settlement, **Metronome** owner invoices.
- Beat: "Every checkout issues a least-privilege card under a C1 scoped identity, then settles at
  month end."

### 1:20 - 2:20 — Swarm: the business (spend the most time here)
- Click **03 Swarm**. Page goes electric-dark. Hero: **License one agent. Upgrade every host.**
- Beat: "This is the business. One agent, licensed to every property manager. It upgrades their
  marketing, sales, and pricing, and earns per call in an agent marketplace."
- Click **Enter the command center**, then run the three upgrades (each returns instantly, LIVE):
  - **Marketing readiness** (Run marketing audit): Nemotron grades how findable and bookable the
    listing is for AI booking agents. **LIVE nemotron**.
  - **Sales** (Draft guest reply): **Nous Hermes** triages the inquiry intent and drafts the on-brand
    reply plus an anniversary-package upsell. **LIVE hermes**. This is the money shot.
  - **Pricing** (Run pricing): Nemotron returns **$345** for the peak Comic-Con Saturday. **LIVE nemotron**.
- Point at each **agent earned $1.50 / $1.00 / $0.25, C1 authorized** pill and the **Agent
  marketplace** earn loop (Stripe 402 then 200).
- Beat: "Three real model calls, two providers, every one metered by Stripe and governed by C1."

### 2:20 - 2:40 — Tech layer: the judging moment
- Click **TECH LAYER** (top right). The strip drops in: where each sponsor plugs into this portal.
- Click **Full sponsor matrix**: NVIDIA / Stripe / Nous / C1 down, Owner / Company / Swarm across,
  with live call counts. Then **Live verification**: real env status, Verify-live buttons.
- Close: "One governed agent. Three scales. Real reasoning, real money rails, real governance. That
  is NemoClaw."

## Proof points to land (say at least three)
- **LIVE badges** with real model ids and latencies (not canned).
- **Two providers exercised live**: NVIDIA Nemotron and Nous Hermes.
- **Stripe HTTP-402** earn loop (402 then 200) on every paid call.
- **C1** scoped NHIs governing every action, hash-chained **audit** behind it.
- The **temperature shift** warm to cool to electric as scale grows.

## If a live call is slow on camera
Loads are cached (instant). Only a forced `?fresh=true` re-calls the model. Keep the toggle on LIVE;
the cached results are genuine past live calls and still read LIVE with their real latency.
