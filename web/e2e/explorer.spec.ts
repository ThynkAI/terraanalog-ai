import { expect, test } from "@playwright/test";

test("explorer: markers, ranked list, detail panel and evidence inspector", async ({ page }) => {
  await page.goto("/explorer?ref=moon-shackleton&obj=rover_mobility");
  const list = page.getByTestId("ranked-list");
  await expect(list.locator("li")).toHaveCount(15);
  await expect(page.locator(".site-marker")).toHaveCount(15);
  // ranks are in descending score order
  const scores = await list.locator("li span.font-mono.text-xs.text-lunar-200").allInnerTexts();
  const nums = scores.map(Number).filter((n) => !Number.isNaN(n));
  expect(nums).toEqual([...nums].sort((a, b) => b - a));
  // keyboard: focus a marker and press Enter
  const marker = page.locator('.site-marker[data-site-id="AQ-MDV"]');
  await marker.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/site=AQ-MDV/);
  const detail = page.getByTestId("site-detail");
  await expect(detail).toContainText("McMurdo Dry Valleys");
  await expect(detail).toContainText("Evidence completeness");
  await detail.getByRole("button", { name: /Illumination contrast/ }).click();
  await expect(detail).toContainText("citation pending from research dataset");
});

test("explorer: filters by analog type, climate and minimum score", async ({ page }) => {
  await page.goto("/explorer?ref=moon-marius-hills&obj=cave_exploration");
  await page.getByLabel("Analog type").selectOption("lava_tube_cave");
  await expect(page.getByTestId("ranked-list").locator("li")).toHaveCount(2);
  await expect(page).toHaveURL(/type=lava_tube_cave/);
  await page.getByLabel("Analog type").selectOption("");
  await page.getByRole("radio", { name: /Mars/ }).click();
  await expect(page).toHaveURL(/body=mars/);
  await expect(page.getByLabel("Planetary reference")).toHaveValue("mars-jezero");
  await expect.poll(() => page.getByTestId("ranked-list").locator("li").count()).toBe(13); // 13 of 15 fixture sites list Mars as a target body (not US-SFV, US-HMK)
  await expect(page.getByTestId("ranked-list")).not.toContainText("San Francisco Volcanic Field");
});

test("explorer: geographic search by name and by coordinates", async ({ page }) => {
  await page.goto("/explorer");
  await expect(page.getByTestId("ranked-list").locator("li")).toHaveCount(15); // wait for hydration + data
  await page.getByLabel(/Geographic search/).fill("Iceland");
  await expect(page.getByLabel(/Geographic search/)).toHaveValue("Iceland");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByTestId("ranked-list").locator("li")).toHaveCount(1);
  await page.getByLabel(/Geographic search/).fill("35.2, -111.6");
  await expect(page.getByLabel("Search radius")).toBeVisible();
  await page.getByLabel("Search radius").selectOption("250");
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByTestId("ranked-list")).toContainText("San Francisco Volcanic Field");
  await expect(page.getByTestId("ranked-list")).not.toContainText("Iceland");
});

test("explorer: deep link restores site, reference and comparison tray", async ({ page }) => {
  await page.goto("/explorer?site=CA-HAU&ref=moon-shackleton&obj=isru&compare=CA-HAU,AQ-MDV");
  await expect(page.getByTestId("site-detail")).toContainText("Haughton");
  await expect(page.getByLabel("Planetary reference")).toHaveValue("moon-shackleton");
  await expect(page.getByLabel("Mission objective")).toHaveValue("isru");
  const tray = page.getByRole("region", { name: "Comparison tray" });
  await expect(tray).toContainText("Comparing (2/4)");
  await tray.getByRole("link", { name: /Open Comparison Lab/ }).click();
  await expect(page).toHaveURL(/\/compare\?ids=CA-HAU,AQ-MDV/);
});

test("recommendation engine explains results and lists non-replicable factors", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Identify cave environments suitable for subsurface robotics tests." }).click();
  const panel = page.getByTestId("recommend-panel");
  await expect(panel).toContainText("Interpreted as:");
  await expect(panel).toContainText("Cave exploration");
  await expect(panel).toContainText("Lava Beds");
  await expect(panel).toContainText("What Earth cannot replicate");
});

test("planetary viewers: select references by list and keyboard", async ({ page }) => {
  await page.goto("/moon");
  await expect(page.getByTestId("reference-detail")).toContainText("Lunar south polar region");
  await page.getByRole("button", { name: /Malapert crater & massif vicinity/ }).first().click();
  await expect(page.getByTestId("reference-detail")).toContainText("-85.00°");
  await expect(page.getByTestId("reference-detail")).toContainText("1737.4 km");
  await page.goto("/mars");
  const gale = page.locator('[data-testid="planet-viewer-mars"] g[role=button]', { hasText: "Gale crater" });
  await gale.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("reference-detail")).toContainText("137.81°");
  await expect(page.getByTestId("reference-detail")).toContainText("3389.5 km");
  await expect(page.getByTestId("match-list").locator("li").first()).toBeVisible();
});
