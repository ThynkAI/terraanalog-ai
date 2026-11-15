import { expect, test } from "@playwright/test";

test("comparison: radar, side-by-side table, missing values and CSV export", async ({ page, request }) => {
  await page.goto("/compare?ids=EA-002,EA-004&ref=MOON-REF-01&obj=general");
  const view = page.getByTestId("compare-view");
  await expect(view.locator(".recharts-radar")).toHaveCount(2);
  const table = view.getByRole("table");
  await expect(table).toContainText("Ice / permafrost agreement");
  await expect(table).toContainText("Miss"); // EA-004 dust_sediment is missing in the research data — shown, never imputed
  await expect(table).toContainText("not in score");
  await expect(table).not.toContainText("MOON-REF-02"); // only the selected reference's criteria
  const href = await view.getByRole("link", { name: /Export CSV/ }).getAttribute("href");
  const csv = await (await request.get(href!)).text();
  expect(csv.split("\n")[0]).not.toContain("SYNTHETIC");
  expect(csv).toContain("MOON-REF-01.dust_sediment,dust_sediment,,missing");
  expect(csv).toContain("EA-004");
});

test("comparison: adding/removing sites updates the deep link (max 4)", async ({ page }) => {
  await page.goto("/compare?ids=EA-002&ref=MOON-REF-02");
  for (const id of ["EA-004", "EA-021", "EA-007", "EA-001"]) await page.getByRole("button", { name: id, exact: true }).click();
  await expect(page).toHaveURL(/ids=EA-004%2CEA-021%2CEA-007%2CEA-001|ids=EA-004,EA-021,EA-007,EA-001/);
  await expect(page.getByTestId("compare-view").locator(".recharts-radar")).toHaveCount(4);
});

test("weight lab recalculates rankings live", async ({ page }) => {
  await page.goto("/compare?tab=weights&ref=MOON-REF-02&obj=general");
  const table = page.getByTestId("weightlab-table");
  await expect(table.locator("tbody tr").first()).toBeVisible();
  const before = await table.locator("tbody tr td:nth-child(2)").allInnerTexts();
  await expect(page.getByLabel(/Operational/)).toHaveCount(0); // weight-0 operational score is not a fidelity feature
  const slider = page.getByLabel(/Ice \/ permafrost agreement/);
  await slider.focus();
  for (let i = 0; i < 40; i++) await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/w=ice/);
  await expect.poll(async () => (await table.locator("tbody tr td:nth-child(2)").allInnerTexts()).join("|")).not.toBe(before.join("|"));
  await expect(table).toContainText("▲");
});

test("sensitivity and discovery views render charts", async ({ page }) => {
  await page.goto("/compare?tab=sensitivity&ref=MARS-REF-02");
  await expect(page.locator(".recharts-line").first()).toBeVisible();
  await page.getByRole("tab", { name: "Discovery & distributions" }).click();
  await expect(page.getByText("Cluster membership")).toBeVisible();
  await expect(page.locator(".recharts-scatter").first()).toBeVisible();
});

test("PDF report: download link returns a generated PDF for the current comparison", async ({ page, request }) => {
  await page.goto("/compare?ids=EA-002,EA-004&ref=MOON-REF-01&obj=MOON_ROVER_MOBILITY");
  const link = page.getByTestId("export-pdf");
  await expect(link).toBeVisible();
  const href = (await link.getAttribute("href"))!;
  expect(href).toContain("/api/export/compare.pdf");
  expect(href).toContain("ref_id=MOON-REF-01");
  const res = await request.get(href);
  expect(res.status()).toBe(200);
  expect(res.headers()["content-type"]).toContain("application/pdf");
  const body = await res.body();
  expect(body.subarray(0, 5).toString()).toBe("%PDF-");
  const [download] = await Promise.all([page.waitForEvent("download"), link.click()]);
  expect(download.suggestedFilename()).toMatch(/^terraanalog_report_MOON-REF-01_MOON_ROVER_MOBILITY\.pdf$/);
});

test("discovery: deck.gl cluster-arc map renders a WebGL canvas with an accessible summary", async ({ page }) => {
  await page.goto("/compare?tab=discovery&ref=MOON-REF-02");
  const map = page.getByTestId("cluster-arc-map");
  await map.scrollIntoViewIfNeeded();
  await expect(map.locator("canvas").first()).toBeVisible();
  await expect.poll(async () => map.locator("canvas").count()).toBeGreaterThanOrEqual(2); // MapLibre + deck.gl overlay
  await expect(map.getByRole("img")).toHaveAttribute("aria-label", /cluster 1 anchored at/);
  await expect(page.getByText(/Moon\/Mars coordinates are never drawn on Earth/)).toBeVisible();
});

test("comparison: no reference selected → body default reference is used and explained", async ({ page }) => {
  await page.goto("/compare");
  await expect(page.getByLabel("Planetary reference")).toHaveValue("MOON-REF-01");
  await expect(page.getByTestId("ref-notes")).toContainText("No planetary reference selected");
});
