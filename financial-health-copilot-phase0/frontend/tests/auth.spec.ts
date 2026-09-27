import { test, expect } from "@playwright/test";
test("signup, empty dashboard, logout and login with real API", async ({
  page,
}) => {
  const email = `phase0-${Date.now()}@example.com`;
  const password = "a-demo-passphrase-123";
  await page.goto("/login");
  await page
    .getByRole("button", { name: "Create an account", exact: true })
    .click();
  await page.getByLabel("Your name").fill("Phase Zero");
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Your financial picture starts here" }),
  ).toBeVisible();
  await expect(page.getByText("Awaiting financial data")).toHaveCount(3);
  await page.getByRole("button", { name: "Log out", exact: true }).click();
  await page.getByLabel("Email address").fill(email);
  await page.getByLabel("Password", { exact: true }).fill("incorrect password");
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: "Email or password is incorrect" }),
  ).toBeVisible();
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Log in", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Welcome, Phase." }),
  ).toBeVisible();
  await page.reload();
  await expect(page).toHaveURL(/\/login$/);
});
test("unauthenticated dashboard redirects to login", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login$/);
});
