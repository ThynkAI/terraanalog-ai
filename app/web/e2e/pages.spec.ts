import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const PAGES = [
  { path: "/", h1: /Earth as a testbed/ },
  { path: "/explorer", h1: "Earth Analog Explorer" },
  { path: "/moon", h1: "Moon Reference Explorer" },
  { path: "/mars", h1: "Mars Reference Explorer" },
  { path: "/compare", h1: "Site Comparison Laboratory" },
  { path: "/methodology", h1: "Scientific Methodology" },
  { path: "/data", h1: "Data Sources and Provenance" },
  { path: "/impact", h1: "Project Impact and Team" },
];

for (const p of PAGES) {
  test(`page ${p.path} renders without runtime errors and shows the research-data badge (no synthetic badge)`, async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (e) => errors.push(e.message));
    await page.goto(p.path);
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(p.h1);
    await expect(page.getByTestId("data-status-badge")).toHaveText(/Research dataset/);
    await expect(page.getByTestId("data-status-badge")).not.toHaveText(/Synthetic/);
    await expect(page.getByTestId("research-notice")).toBeVisible();
    expect(errors).toEqual([]);
  });

  test(`page ${p.path} has no serious/critical axe violations`, async ({ page }) => {
    await page.goto(p.path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForLoadState("networkidle");
    const results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
    const bad = results.violations.filter((v) => v.impact === "serious" || v.impact === "critical");
    expect(bad.map((v) => `${v.id}: ${v.nodes.length} nodes — ${v.nodes[0]?.target}`)).toEqual([]);
  });
}

test("skip link and keyboard navigation reach main content", async ({ page }) => {
  await page.goto("/impact");
  await page.keyboard.press("Tab");
  const skip = page.getByRole("link", { name: "Skip to content" });
  await expect(skip).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
});

test("reduced-motion users get a working explorer", async ({ browser }) => {
  const ctx = await browser.newContext({ reducedMotion: "reduce", viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  await page.goto("/explorer?site=EA-021");
  await expect(page.getByTestId("site-detail")).toContainText("Lava Beds");
  await ctx.close();
});
