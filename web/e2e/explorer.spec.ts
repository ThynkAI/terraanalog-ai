import { expect, test } from "@playwright/test";

test("explorer: markers, ranked list, detail panel and evidence inspector", async ({ page }) => {
  await page.goto("/explorer?ref=MOON-REF-01&obj=MOON_ROVER_MOBILITY");
  const list = page.getByTestId("ranked-list");
  await expect(list.locator("li")).toHaveCount(28);
  await expect(page.locator(".site-marker")).toHaveCount(28);
  // ranks are in descending score order
  const scores = await list.locator("li span.font-mono.text-xs.text-lunar-200").allInnerTexts();
  const nums = scores.map(Number).filter((n) => !Number.isNaN(n));
  expect(nums).toEqual([...nums].sort((a, b) => b - a));
  // keyboard: focus a marker and press Enter
  const marker = page.locator('.site-marker[data-site-id="EA-004"]');
  await marker.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/site=EA-004/);
  const detail = page.getByTestId("site-detail");
  await expect(detail).toContainText("McMurdo Dry Valleys");
  await expect(detail).toContainText("Evidence completeness");
  // value-type badges come from the research data; missing values are shown as "—", never imputed
  await expect(detail).toContainText("Meas");
  await expect(detail).toContainText("Mode");
  await expect(detail).toContainText("Prov");
  await expect(detail.getByTestId("separate-criterion").filter({ hasText: "Operational" })).toContainText("never added to the fidelity score");
  await expect(detail.getByTestId("published-score")).toBeVisible();
  await detail.getByRole("button", { name: /Ice \/ permafrost agreement/ }).click();
  await expect(detail).toContainText("MAAT-logistic permafrost fallback");
});

test("explorer: filters by analog type, climate and minimum score", async ({ page }) => {
  await page.goto("/explorer?ref=MOON-REF-05&obj=MOON_LAVA_TUBE");
  await page.getByLabel("Analog type").selectOption("lava_tube_cave");
  await expect(page.getByTestId("ranked-list").locator("li")).toHaveCount(4);
  await expect(page).toHaveURL(/type=lava_tube_cave/);
  await page.getByLabel("Analog type").selectOption("");
  await page.getByRole("radio", { name: /Mars/ }).click();
  await expect(page).toHaveURL(/body=mars/);
  await expect(page.getByLabel("Planetary reference")).toHaveValue("MARS-REF-01"); // Mars default reference from scoring_config
  await expect(page.getByLabel("Mission objective")).not.toHaveValue("MOON_LAVA_TUBE"); // Moon profile reset for a Mars reference
  await expect.poll(() => page.getByTestId("ranked-list").locator("li").count()).toBe(28); // all 28 research sites list Mars as a target body
});

test("explorer: geographic search by name and by coordinates", async ({ page }) => {
  await page.goto("/explorer");
  await expect(page.getByTestId("ranked-list").locator("li")).toHaveCount(28); // wait for hydration + data
  await page.getByLabel(/Geographic search/).fill("Iceland");
  await expect(page.getByLabel(/Geographic search/)).toHaveValue("Iceland");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByTestId("ranked-list").locator("li")).toHaveCount(2); // Holuhraun + Askja
  await page.getByLabel(/Geographic search/).fill("35.2, -111.6");
  await expect(page.getByLabel("Search radius")).toBeVisible();
  await page.getByLabel("Search radius").selectOption("250");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByTestId("ranked-list")).toContainText("Meteor Crater");
  await expect(page.getByTestId("ranked-list")).not.toContainText("Askja");
});

test("explorer: deep link restores site, reference and comparison tray", async ({ page }) => {
  await page.goto("/explorer?site=EA-002&ref=MOON-REF-02&obj=MOON_ISRU_ICE&compare=EA-002,EA-004");
  await expect(page.getByTestId("site-detail")).toContainText("Haughton");
  await expect(page.getByLabel("Planetary reference")).toHaveValue("MOON-REF-02");
  await expect(page.getByLabel("Mission objective")).toHaveValue("MOON_ISRU_ICE");
  const tray = page.getByRole("region", { name: "Comparison tray" });
  await expect(tray).toContainText("Comparing (2/4)");
  await tray.getByRole("link", { name: /Open Comparison Lab/ }).click();
  await expect(page).toHaveURL(/\/compare\?ids=EA-002,EA-004/);
});

test("recommendation engine explains results and lists non-replicable factors", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Identify cave environments suitable for subsurface robotics tests." }).click();
  const panel = page.getByTestId("recommend-panel");
  await expect(panel).toContainText("Interpreted as:");
  await expect(panel).toContainText("Moon Lava Tube");
  await expect(panel).toContainText("Marius Hills");
  await expect(panel).toContainText("Cueva de los Verdes");
  await expect(panel).toContainText("What Earth cannot replicate");
});

test("planetary viewers: select references by list and keyboard", async ({ page }) => {
  await page.goto("/moon");
  await expect(page.getByTestId("reference-detail")).toContainText("Lunar south polar highlands");
  await expect(page.getByTestId("status-class")).toContainText("candidate region");
  await expect(page.getByTestId("reference-detail")).toContainText("not an approved base site");
  await page.getByRole("button", { name: /Malapert massif/ }).last().click(); // list entry (map markers overlap near the pole)
  await expect(page.getByTestId("reference-detail")).toContainText("-85.99°");
  await expect(page.getByTestId("reference-detail")).toContainText("1737.4 km");
  await page.goto("/mars");
  const gale = page.locator('[data-testid="planet-viewer-mars"] g[role=button]', { hasText: "Gale crater" });
  await gale.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("reference-detail")).toContainText("137.44°");
  await expect(page.getByTestId("reference-detail")).toContainText("3396.19 km");
  await expect(page.getByTestId("match-list").locator("li").first()).toBeVisible();
});
