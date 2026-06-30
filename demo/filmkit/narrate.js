// Capture annotated scene screenshots (caption bar baked in) for the narrated film.
const { chromium } = require("playwright-core");
const BASE = process.env.FILM_BASE || "http://localhost:5174";
const OUT = "/tmp/nemo-film/scenes";

const SCENES = [
  { key: "turnover", tab: "Company", cta: /operations console/i, scrollTo: "Turnover pipeline",
    caption: "Turnover loop: checkout to ready. Sweet Clementine is stalled at inspection." },
  { key: "stall", scrollTo: "Stalled handoffs",
    caption: "Hermes drafts the nudge to whoever is blocking the handoff." },
  { key: "schedule", scrollTo: "Cleaner scheduling",
    clicks: [{ name: /Assign \+ issue card/, waitFor: "CARD PRE-AUTHORIZED" }],
    scrollAfter: "Cleaner scheduling",
    caption: "Hermes reassigns the stalled clean to a free cleaner and pre-authorizes the card." },
  { key: "performance", scrollTo: "Portfolio performance",
    caption: "Over- and under-performers flagged, with a Hermes explanation of why." },
  { key: "portfolio", scrollTo: "Portfolio org map", settle: 2600,
    caption: "The whole book of business as a live graph: firm, owners, properties, crew." },
  { key: "agents", scrollTo: "Agents at work",
    caption: "Every action runs as a named, audited agent." },
  { key: "owner", tab: "Owner", cta: /owner console/i, scrollTo: "Turnover pipeline",
    caption: "The owner sees the same loop for their one property." },
  { key: "swarm_caps", tab: "Swarm", cta: /command center/i,
    clicks: [
      { name: /Run marketing audit/i, waitFor: "marketing readiness score" },
      { name: /Draft guest reply/i, waitFor: "intent" },
      { name: /Run pricing/i, waitFor: "recommended rate" },
    ],
    scrollAfter: "Marketing readiness",
    caption: "The agent sells marketing, sales, and pricing to other agents, paid per call." },
  { key: "swarm_market", scrollTo: "Marketplace earnings",
    caption: "Every call settles over HTTP 402. Live marketplace earnings." },
];

async function clickIf(page, name, t = 5000) {
  try { await page.getByRole("button", { name }).first().click({ timeout: t }); return true; }
  catch (e) { return false; }
}
async function injectCaption(page, text) {
  await page.evaluate((t) => {
    const d = document.createElement("div");
    d.id = "__cap"; d.textContent = t;
    Object.assign(d.style, {
      position: "fixed", left: "0", right: "0", bottom: "0", zIndex: "99999",
      padding: "26px 40px 30px", color: "#fff", fontSize: "30px", lineHeight: "1.3",
      fontFamily: "-apple-system,Helvetica,Arial,sans-serif",
      background: "linear-gradient(to top, rgba(6,9,14,0.96) 60%, rgba(6,9,14,0))",
      textAlign: "center",
    });
    document.body.appendChild(d);
  }, text);
}
async function removeCaption(page) {
  await page.evaluate(() => { const e = document.getElementById("__cap"); if (e) e.remove(); });
}
async function scrollTo(page, text) {
  try {
    await page.getByText(text, { exact: false }).first().scrollIntoViewIfNeeded({ timeout: 4000 });
  } catch (e) { console.error("  scroll miss: " + text); }
  await page.waitForTimeout(700);
}

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  const page = await ctx.newPage();
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.waitForTimeout(1500);

  for (const s of SCENES) {
    if (s.tab) {
      await clickIf(page, s.tab);
      await page.evaluate(() => window.scrollTo({ top: 0 }));
      await page.waitForTimeout(900);
      if (s.cta) { await clickIf(page, s.cta); await page.waitForTimeout(1100); }
    }
    if (s.scrollTo) await scrollTo(page, s.scrollTo);
    if (s.clicks) {
      for (const c of s.clicks) {
        try {
          const b = page.getByRole("button", { name: c.name }).first();
          await b.scrollIntoViewIfNeeded({ timeout: 3000 });
          await page.waitForTimeout(400);
          await b.click({ timeout: 3000 });
          if (c.waitFor) await page.getByText(c.waitFor, { exact: false }).first().waitFor({ timeout: 9000 });
          await page.waitForTimeout(500);
        } catch (e) { console.error("  click miss: " + s.key + " :: " + c.name); }
      }
      if (s.scrollAfter) await scrollTo(page, s.scrollAfter);
    }
    if (s.settle) await page.waitForTimeout(s.settle);
    await injectCaption(page, s.caption);
    await page.waitForTimeout(300);
    await page.screenshot({ path: `${OUT}/${s.key}.png` });
    await removeCaption(page);
  }

  await browser.close();
  console.log("SCENES_OK");
})().catch((e) => { console.error(e); process.exit(1); });
