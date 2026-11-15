import { expect, test } from "@playwright/test";

test("overview case cards and scientific section links form a complete review path", async ({ page }, testInfo) => {
  await page.goto("/");
  await expect(page.getByTestId("data-status-badge")).toContainText("Research dataset");
  const mainNav = page.getByRole("navigation", { name: "Main", exact: true });
  const bounds = await mainNav.boundingBox();
  expect(bounds!.height).toBeLessThan(50);
  await expect(page.getByText("Initialising globe…", { exact: true })).toBeHidden({ timeout: 30_000 });
  await expect(page.getByTestId("earth-map").locator("canvas")).toBeVisible();
  await page.screenshot({ path: testInfo.outputPath("final-homepage.png") });
  await page.getByRole("link", { name: /Investigate this case.*Undara/ }).click();
  await expect(page).toHaveURL(/case=undara-cave-robotics/);
  await expect(page.getByLabel("Baseline case summary")).toContainText("62.1");
  await page.screenshot({ path: testInfo.outputPath("final-science-summary.png") });
  await page.getByRole("navigation", { name: "Case study sections" }).getByRole("link", { name: /Benchmarks/ }).click();
  await expect(page).toHaveURL(/#benchmark-title$/);
  await expect(page.getByRole("heading", { name: "Does it add value beyond the benchmarks?" })).toBeInViewport();
});
