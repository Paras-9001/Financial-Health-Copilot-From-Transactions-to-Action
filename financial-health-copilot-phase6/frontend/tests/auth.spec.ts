import { expect, test } from "@playwright/test";

test("signup, demo onboarding, dashboard navigation, and login", async ({ page }) => {
  const email = `phase6-${Date.now()}@example.com`;
  const password = "a-demo-passphrase-123";
  await page.goto("/login");
  await page.getByRole("button", { name: "Create an account", exact: true }).click();
  await page.getByLabel("Your name").fill("Phase Six");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Build your financial picture" })).toBeVisible();

  await page.getByRole("button", { name: /Explore with sample data/ }).click();
  await expect(page.getByRole("heading", { name: "Pick a starting scenario" })).toBeVisible();
  await page.getByRole("button", { name: "Use Ananya" }).click();
  await expect(page.getByRole("heading", { name: "Where am I?" })).toBeVisible();
  await expect(page.getByText("FACT", { exact: true }).first()).toBeVisible();

  await page.getByRole("link", { name: /Spending/ }).click();
  await expect(page.getByRole("heading", { name: "Spending" })).toBeVisible();
  await page.getByRole("button", { name: "Log out" }).click();
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Welcome, Phase." })).toBeVisible();
});

test("unauthenticated protected route redirects to login", async ({ page }) => {
  await page.goto("/chat");
  await expect(page).toHaveURL(/\/login$/);
});
