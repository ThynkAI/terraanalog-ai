import { expect, test } from "@playwright/test";

test("comparison: radar, side-by-side table, missing values and CSV export", async ({ page, request }) => {
  await page.goto("/compare?ids=CA-HAU,ES-RIO&ref=mars-jezero&obj=drilling");
  const view = page.getByTestId("compare-view");
  await expect(view.locator(".recharts-radar")).toHaveCount(2);
  await expect(view.getByRole("table")).toContainText("Ice / permafrost relevance");
  await expect(view.getByRole("table")).toContainText("Miss");
  const href = await view.getByRole("link", { name: /Export CSV/ }).getAttribute("href");
  const csv = await (await request.get(href!)).text();
  expect(csv.split("\n")[0]).toContain("SYNTHETIC");
  expect(csv).toContain("ES-RIO");
});

test("comparison: adding/removing sites updates the deep link (max 4)", async ({ page }) => {
  await page.goto("/compare?ids=CA-HAU&ref=moon-shackleton");
  for (const id of ["AQ-MDV", "US-LBN", "IS-ASK", "CL-ATA"]) await page.getByRole("button", { name: id, exact: true }).click();
  await expect(page).toHaveURL(/ids=AQ-MDV%2CUS-LBN%2CIS-ASK%2CCL-ATA|ids=AQ-MDV,US-LBN,IS-ASK,CL-ATA/);
  await expect(page.getByTestId("compare-view").locator(".recharts-radar")).toHaveCount(4);
});

test("weight lab recalculates rankings live", async ({ page }) => {
  await page.goto("/compare?tab=weights&ref=moon-shackleton&obj=general");
  const table = page.getByTestId("weightlab-table");
  await expect(table.locator("tbody tr").first()).toBeVisible();
  const before = await table.locator("tbody tr td:nth-child(2)").allInnerTexts();
  const slider = page.getByLabel(/Operational testing suitability/);
  await slider.focus();
  for (let i = 0; i < 40; i++) await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/w=operational/);
  await expect.poll(async () => (await table.locator("tbody tr td:nth-child(2)").allInnerTexts()).join("|")).not.toBe(before.join("|"));
  await expect(table).toContainText("▲");
});

test("sensitivity and discovery views render charts", async ({ page }) => {
  await page.goto("/compare?tab=sensitivity&ref=mars-gale");
  await expect(page.locator(".recharts-line").first()).toBeVisible();
  await page.getByRole("tab", { name: "Discovery & distributions" }).click();
  await expect(page.getByText("Cluster membership")).toBeVisible();
  await expect(page.locator(".recharts-scatter").first()).toBeVisible();
});

test("PDF report: download link returns a generated PDF for the current comparison", async ({ page, request }) => {
  await page.goto("/compare?ids=CA-HAU,AQ-MDV&ref=moon-shackleton&obj=rover_mobility");
  const link = page.getByTestId("export-pdf");
  await expect(link).toBeVisible();
  const href = (await link.getAttribute("href"))!;
  expect(href).toContain("/api/export/compare.pdf");
  expect(href).toContain("ref_id=moon-shackleton");
  const res = await request.get(href);
  expect(res.status()).toBe(200);
  expect(res.headers()["content-type"]).toContain("application/pdf");
  const body = await res.body();
  expect(body.subarray(0, 5).toString()).toBe("%PDF-");
  const [download] = await Promise.all([page.waitForEvent("download"), link.click()]);
  expect(download.suggestedFilename()).toMatch(/^terraanalog_report_moon-shackleton_rover_mobility\.pdf$/);
});

test("discovery: deck.gl cluster-arc map renders a WebGL canvas with an accessible summary", async ({ page }) => {
  await page.goto("/compare?tab=discovery&ref=moon-shackleton");
  const map = page.getByTestId("cluster-arc-map");
  await map.scrollIntoViewIfNeeded();
  await expect(map.locator("canvas").first()).toBeVisible();
  await expect.poll(async () => map.locator("canvas").count()).toBeGreaterThanOrEqual(2); // MapLibre + deck.gl overlay
  await expect(map.getByRole("img")).toHaveAttribute("aria-label", /cluster 1 anchored at/);
  await expect(page.getByText(/Moon\/Mars coordinates are never drawn on Earth/)).toBeVisible();
});
