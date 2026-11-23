import { expect, test } from "@playwright/test";

test("mobile: menu opens and has no horizontal scroll", async ({ page }) => {
  await page.goto("/docs/quick-start/");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow).toBeLessThanOrEqual(1);
  await page.getByRole("button", { name: "Open menu" }).click();
  await page.getByRole("dialog").getByRole("link", { name: "Security model" }).click();
  await expect(page.getByRole("heading", { level: 1, name: "Security model" })).toBeVisible();
});
