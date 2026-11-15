import { expect, test } from "@playwright/test";

for (const path of ["/", "/explorer", "/moon", "/mars", "/compare", "/science", "/methodology", "/data", "/impact"]) {
  test(`mobile ${path}: no horizontal overflow`, async ({ page }) => {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await page.waitForLoadState("networkidle");
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflow).toBeLessThanOrEqual(1);
  });
}

test("mobile navigation menu opens and navigates", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Menu" }).click();
  const nav = page.getByRole("navigation", { name: "Main mobile" });
  await expect(nav).toBeVisible();
  await nav.getByRole("link", { name: "Comparison Lab" }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Site Comparison Laboratory");
});

test("mobile explorer: filters collapse behind a toggle and detail panel is reachable", async ({ page }) => {
  await page.goto("/explorer?site=EA-021");
  await expect(page.getByLabel("Analog type")).toBeHidden();
  await page.getByRole("button", { name: "Show" }).first().click();
  await expect(page.getByLabel("Analog type")).toBeVisible();
  await expect(page.getByTestId("site-detail")).toContainText("Lava Beds");
});


test("mobile science case: switching cases and stress test stays usable", async ({ page }) => {
  await page.goto("/science?case=undara-cave-robotics");
  await expect(page.getByTestId("scientific-case")).toContainText("modeled mean annual air temperature");
  await page.getByRole("button", { name: "Exclude the cave-temperature proxy", exact: true }).click();
  await expect(page.getByRole("button", { name: "Restore baseline weights" })).toHaveAttribute("aria-pressed", "true");
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
});


test("mobile navigation dismisses with Escape", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Menu" }).click();
  await expect(page.getByRole("navigation", { name: "Main mobile" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("navigation", { name: "Main mobile" })).toBeHidden();
});
