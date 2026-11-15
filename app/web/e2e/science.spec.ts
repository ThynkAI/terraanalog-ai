import { expect, test } from "@playwright/test";

test("scientific cases show benchmark evidence, proxy stress tests and persistent links", async ({ page }, testInfo) => {
  await page.goto("/science?case=undara-cave-robotics");
  const study = page.getByTestId("scientific-case");
  await expect(study).toContainText("Mission-use proposal; novelty unverified");
  await expect(study).toContainText("not a measured cave temperature");
  await expect(page.getByRole("region", { name: "Regional measurement comparison", exact: true })).toContainText("1.2");
  await expect(page.getByRole("region", { name: "Benchmark and stress test results" }).getByRole("row")).toHaveCount(5);
  await page.getByRole("button", { name: "Exclude the cave-temperature proxy", exact: true }).click();
  await expect(study).toContainText("Stress weights active");
  await page.screenshot({ path: testInfo.outputPath("science-undara-benchmarks.png") });
  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download evidence JSON" }).click();
  expect((await downloadPromise).suggestedFilename()).toBe("terraanalog_undara-cave-robotics_evidence.json");
  await page.getByRole("button", { name: /Holuhraun: volcanic terrain/ }).click();
  await expect(page).toHaveURL(/case=holuhraun-mobility/);
  await expect(study).toContainText("Previously published analog");
  await expect(study).toContainText("Exploratory reference");
  await expect(page.getByRole("region", { name: "Published evidence-strict check" })).toContainText("not fixed-reference scores");
  await page.reload();
  await expect(study).toContainText("Holuhraun");
  await page.screenshot({ path: testInfo.outputPath("science-holuhraun-overview.png") });
});
