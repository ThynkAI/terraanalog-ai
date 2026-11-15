// Captures real screenshots of the running app. Usage: BASE_URL=http://127.0.0.1:3000 node scripts/screenshots.mjs
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import path from "node:path";

const BASE = process.env.BASE_URL || "http://127.0.0.1:3000";
const OUT = path.resolve(process.env.OUT_DIR || "../docs/screenshots");
mkdirSync(OUT, { recursive: true });

// URLs use the research dataset ids (data/research, the default TERRA_DATA_DIR).
const shots = [
  { name: "01-mission-overview", url: "/", wait: "text=Top matches · Lunar south polar highlands", after: async (p) => { await p.getByRole("button", { name: /lunar polar rovers/ }).first().click(); await p.waitForSelector("text=Interpreted as:"); } },
  { name: "02-earth-explorer-globe", url: "/explorer?ref=MOON-REF-02&obj=MOON_ISRU_ICE&site=EA-002&compare=EA-002,EA-004", wait: "[data-testid=site-detail]", settle: 5000 },
  { name: "03-earth-explorer-satellite-2d", url: "/explorer?ref=MARS-REF-01&obj=MARS_ASTROBIO_SEDIMENTS&basemap=satellite&proj=mercator", wait: "[data-testid=ranked-list] li", settle: 6000 },
  { name: "04-moon-reference-shackleton", url: "/moon?ref=MOON-REF-02&obj=MOON_ISRU_ICE", wait: "[data-testid=reference-detail]", settle: 5000 },
  { name: "05-mars-reference-jezero", url: "/mars?ref=MARS-REF-01&obj=MARS_ASTROBIO_SEDIMENTS", wait: "[data-testid=reference-detail]", settle: 5000 },
  { name: "06-comparison-lab-radar", url: "/compare?ids=EA-002,EA-004,EA-021,EA-001&ref=MOON-REF-01&obj=MOON_ROVER_MOBILITY", wait: "[data-testid=compare-view]", settle: 1500 },
  { name: "07-weight-lab", url: "/compare?tab=weights&ref=MOON-REF-02&obj=general&w=ice:2.5,aridity:0.3", wait: "[data-testid=weightlab-table]", settle: 1500 },
  { name: "08-sensitivity", url: "/compare?tab=sensitivity&ref=MARS-REF-02&obj=MARS_ROVER_MOBILITY", wait: "text=Rank stability", settle: 2000 },
  { name: "09-discovery-clusters", url: "/compare?tab=discovery&ref=MOON-REF-01", wait: "text=Cluster membership", settle: 2000 },
  { name: "15-discovery-deckgl-cluster-arcs", url: "/compare?tab=discovery&ref=MOON-REF-02", wait: "[data-testid=cluster-arc-map] canvas", settle: 4000, after: async (p) => { await p.locator("[data-testid=cluster-arc-map]").scrollIntoViewIfNeeded(); }, clip: "[data-testid=cluster-arc-map]" },
  { name: "17-site-detail-value-types", url: "/explorer?ref=MOON-REF-01&obj=MOON_ROVER_MOBILITY&site=EA-004", wait: "[data-testid=site-detail]", settle: 2500, clip: "[data-testid=site-detail]",
    tall: true },
  { name: "10-methodology", url: "/methodology", wait: "text=Body weights", settle: 1500 },
  { name: "11-data-provenance", url: "/data", wait: "text=Dataset catalog", settle: 1500 },
  { name: "12-impact-team", url: "/impact", wait: "text=Roadmap", settle: 500 },
];

// ONLY=06,09 captures a subset (prefix match) without touching the other screenshots.
const ONLY = (process.env.ONLY || "").split(",").filter(Boolean);
const want = (n) => !ONLY.length || ONLY.some((o) => n.startsWith(o));
const browser = await chromium.launch({ args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const results = [];
for (const viewport of [{ w: 1600, h: 1000, tag: "" }]) {
  const ctx = await browser.newContext({ viewport: { width: viewport.w, height: viewport.h }, deviceScaleFactor: 1 });
  for (const s of shots.filter((x) => want(x.name))) {
    const page = await ctx.newPage();
    if (s.tall) await page.setViewportSize({ width: viewport.w, height: 2600 }); // side panel fits without inner scrolling
    try {
      await page.goto(BASE + s.url, { waitUntil: "networkidle", timeout: 60000 });
      await page.waitForSelector(s.wait, { timeout: 30000 });
      if (s.after) await s.after(page);
      await page.waitForTimeout(s.settle ?? 800);
      const file = path.join(OUT, `${s.name}${viewport.tag}.png`);
      if (s.clip && s.tall) {
        const bb = await page.locator(s.clip).boundingBox();
        await page.screenshot({ path: file, clip: { x: bb.x - 8, y: bb.y - 8, width: bb.width + 16, height: Math.min(bb.height + 16, 1500) } });
      } else if (s.clip) await page.locator(s.clip).screenshot({ path: file });
      else if (s.name.startsWith("02") || s.name.startsWith("03")) await page.screenshot({ path: file });
      else {
        // Very tall full-page captures (> ~8k px) tile/repeat in headless Chromium, so cap the height.
        const h = await page.evaluate(() => document.documentElement.scrollHeight);
        await page.screenshot({ path: file, fullPage: true, clip: { x: 0, y: 0, width: viewport.w, height: Math.min(h, 4200) } });
      }
      results.push(["ok", file]);
    } catch (e) {
      results.push(["FAILED", s.name, String(e).split("\n")[0]]);
    }
    await page.close();
  }
  await ctx.close();
}
// mobile
const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
for (const s of [{ name: "13-mobile-explorer", url: "/explorer?ref=MOON-REF-02&site=EA-002", wait: "[data-testid=site-detail]" }, { name: "14-mobile-overview", url: "/", wait: "text=Top matches · Lunar south polar highlands" }].filter((x) => want(x.name))) {
  const page = await mctx.newPage();
  try {
    await page.goto(BASE + s.url, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector(s.wait, { timeout: 30000 });
    await page.waitForTimeout(3000);
    const file = path.join(OUT, `${s.name}.png`);
    await page.screenshot({ path: file, fullPage: false });
    results.push(["ok", file]);
  } catch (e) {
    results.push(["FAILED", s.name, String(e).split("\n")[0]]);
  }
  await page.close();
}
await browser.close();
for (const r of results) console.log(r.join("  "));
if (results.some((r) => r[0] !== "ok")) process.exitCode = 1;
