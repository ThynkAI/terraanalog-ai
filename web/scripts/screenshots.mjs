// Captures real screenshots of the running app. Usage: BASE_URL=http://127.0.0.1:3000 node scripts/screenshots.mjs
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import path from "node:path";

const BASE = process.env.BASE_URL || "http://127.0.0.1:3000";
const OUT = path.resolve(process.env.OUT_DIR || "../docs/screenshots");
mkdirSync(OUT, { recursive: true });

const shots = [
  { name: "01-mission-overview", url: "/", wait: "text=Top matches · Shackleton" , after: async (p) => { await p.getByRole("button", { name: /lunar polar rovers/ }).first().click(); await p.waitForSelector("text=Interpreted as:"); } },
  { name: "02-earth-explorer-globe", url: "/explorer?ref=moon-shackleton&obj=rover_mobility&site=CA-HAU&compare=CA-HAU,AQ-MDV", wait: "[data-testid=site-detail]", settle: 5000 },
  { name: "03-earth-explorer-satellite-2d", url: "/explorer?ref=mars-jezero&obj=drilling&basemap=satellite&proj=mercator", wait: "[data-testid=ranked-list] li", settle: 6000 },
  { name: "04-moon-reference-shackleton", url: "/moon?ref=moon-shackleton&obj=isru", wait: "[data-testid=reference-detail]", settle: 5000 },
  { name: "05-mars-reference-jezero", url: "/mars?ref=mars-jezero&obj=drilling", wait: "[data-testid=reference-detail]", settle: 5000 },
  { name: "06-comparison-lab-radar", url: "/compare?ids=CA-HAU,AQ-MDV,US-LBN,ES-RIO&ref=moon-shackleton&obj=rover_mobility", wait: "[data-testid=compare-view]", settle: 1500 },
  { name: "07-weight-lab", url: "/compare?tab=weights&ref=moon-shackleton&obj=general&w=operational:2.5,illumination:0.3", wait: "[data-testid=weightlab-table]", settle: 1500 },
  { name: "08-sensitivity", url: "/compare?tab=sensitivity&ref=mars-gale&obj=rover_mobility", wait: "text=Rank stability", settle: 2000 },
  { name: "09-discovery-clusters", url: "/compare?tab=discovery", wait: "text=Cluster membership", settle: 2000 },
  { name: "15-discovery-deckgl-cluster-arcs", url: "/compare?tab=discovery&ref=moon-shackleton", wait: "[data-testid=cluster-arc-map] canvas", settle: 4000, after: async (p) => { await p.locator("[data-testid=cluster-arc-map]").scrollIntoViewIfNeeded(); }, clip: "[data-testid=cluster-arc-map]" },
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
    try {
      await page.goto(BASE + s.url, { waitUntil: "networkidle", timeout: 60000 });
      await page.waitForSelector(s.wait, { timeout: 30000 });
      if (s.after) await s.after(page);
      await page.waitForTimeout(s.settle ?? 800);
      const file = path.join(OUT, `${s.name}${viewport.tag}.png`);
      if (s.clip) await page.locator(s.clip).screenshot({ path: file });
      else await page.screenshot({ path: file, fullPage: s.name.startsWith("02") || s.name.startsWith("03") ? false : true });
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
for (const s of [{ name: "13-mobile-explorer", url: "/explorer?ref=moon-shackleton&site=CA-HAU", wait: "[data-testid=site-detail]" }, { name: "14-mobile-overview", url: "/", wait: "text=Top matches · Shackleton" }].filter((x) => want(x.name))) {
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
