import { expect, test } from "@playwright/test";

test("mission shortcut restores a compatible reference and objective", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: /Put a Mars rover to work/ }).click();
  await expect(page.getByLabel("Planetary reference")).toHaveValue("MARS-REF-02");
  await expect(page.getByLabel("Mission objective")).toHaveValue("MARS_ROVER_MOBILITY");
  await expect(page.getByTestId("ranked-list").locator("li")).toHaveCount(28);
});

test("candidate discovery preserves the filter in shareable URLs", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Explore candidates" }).click();
  await expect(page).toHaveURL(/group=candidate/);
  await expect(page.getByTestId("ranked-list")).toContainText("Holuhraun");
  await expect(page.getByTestId("ranked-list")).not.toContainText("Haughton");
  await page.reload();
  await expect(page.getByTestId("ranked-list")).toContainText("Holuhraun");
});
