import { expect, test } from "@playwright/test";

test("Scenario 7 recalculates and explains a new transaction through the UI", async ({ page }) => {
  const email = `phase7-${Date.now()}@example.com`;
  await page.goto("/login");
  await page.getByRole("button", { name: "Create an account", exact: true }).click();
  await page.getByLabel("Your name").fill("Phase Seven");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("phase-seven-passphrase");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await page.getByRole("button", { name: /Explore with sample data/ }).click();
  await page.getByRole("button", { name: "Use Ananya" }).click();
  await expect(page.getByRole("heading", { name: "Where am I?" })).toBeVisible();

  await page.getByRole("link", { name: /Transactions/ }).first().click();
  await page.getByRole("button", { name: /Add transaction/ }).click();
  await page.getByLabel("Account").selectOption({ label: "Ananya Checking" });
  await page.getByLabel("Date").fill("2026-09-28");
  await page.getByLabel("Amount").fill("12000");
  await page.getByLabel("Description").fill("UNPLANNED MEDICAL EXPENSE");
  await page.getByRole("button", { name: "Save and recalculate" }).click();

  const toast = page.getByRole("status").filter({ hasText: "FINANCIAL PICTURE UPDATED" });
  await expect(toast).toBeVisible();
  await expect(toast).toContainText("Expenses changed");
  await expect(toast).toContainText(/Cash buffer changed|New risk detected|Top recommendation changed/);
  await toast.getByRole("link", { name: /See what changed/ }).click();
  await expect(page).toHaveURL(/\/recommendations$/);
  await expect(page.getByRole("heading", { name: "Recommendations" })).toBeVisible();
  await expect(page.locator(".recommendation-list .insight-card").first()).toBeVisible();
});
