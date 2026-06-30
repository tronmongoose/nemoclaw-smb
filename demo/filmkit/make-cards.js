// Render title/end cards as 1440x900 PNGs via the installed Chrome (no drawtext needed).
const { chromium } = require("playwright-core");

const TITLE = `
<html><body style="margin:0;width:1440px;height:900px;background:#0e1116;
 display:flex;flex-direction:column;align-items:center;justify-content:center;
 font-family:Georgia,'Times New Roman',serif;color:#fff">
  <div style="font-size:108px;font-weight:600;letter-spacing:-2px">NemoClaw</div>
  <div style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:36px;
   color:#9fb3c8;margin-top:20px">Hermes coordination for property managers</div>
  <div style="font-family:ui-monospace,Menlo,monospace;font-size:18px;color:#5b6b7d;
   margin-top:46px;letter-spacing:4px;text-transform:uppercase">turnover &middot; scheduling &middot; performance</div>
</body></html>`;

const END = `
<html><body style="margin:0;width:1440px;height:900px;background:#0e1116;
 display:flex;flex-direction:column;align-items:center;justify-content:center;
 font-family:Georgia,'Times New Roman',serif;color:#fff">
  <div style="font-size:62px;font-weight:600">One property manager. Many agents.</div>
  <div style="font-family:-apple-system,Helvetica,Arial,sans-serif;font-size:34px;
   color:#9fb3c8;margin-top:18px">Hermes connects the work</div>
  <div style="font-family:ui-monospace,Menlo,monospace;font-size:18px;color:#5b6b7d;
   margin-top:46px;letter-spacing:4px;text-transform:uppercase">Nous Hermes 4 &middot; governed &middot; audited</div>
</body></html>`;

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });
  await page.setContent(TITLE, { waitUntil: "networkidle" });
  await page.screenshot({ path: "/tmp/nemo-film/title.png" });
  await page.setContent(END, { waitUntil: "networkidle" });
  await page.screenshot({ path: "/tmp/nemo-film/end.png" });
  await browser.close();
  console.log("CARDS_OK");
})().catch((e) => { console.error(e); process.exit(1); });
