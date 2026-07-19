import { test, expect } from "@playwright/test";
import { getLocator } from "../predict";

/**
 * Demo target: saucedemo.com (replaces the earlier geeks-shop/Dickens
 * Museum target — a purpose-built QA practice site is a more honest,
 * stable demo than a real e-commerce page not meant for automated testing).
 *
 * saucedemo.com's DOM uses "data-test" (not "data-testid") for its stable
 * test hooks — if that's ever changed, update the testIdAttribute below.
 * If it changed, this test will fail loudly rather than silently pass.
 *
 * Requires the API running locally first:
 *   uvicorn server.app:app --reload
 */

const TEST_ID_ATTR = "data-test";

test("login on saucedemo using AI-recommended selectors", async ({ page }) => {
  await page.goto("/");

  const usernameLocator = await getLocator(
    { tag: "input", data_testid: "username" },
    TEST_ID_ATTR
  );
  const passwordLocator = await getLocator(
    { tag: "input", data_testid: "password" },
    TEST_ID_ATTR
  );
  const loginButtonLocator = await getLocator(
    { tag: "input", data_testid: "login-button" },
    TEST_ID_ATTR
  );

  await page.locator(usernameLocator).fill("standard_user");
  await page.locator(passwordLocator).fill("secret_sauce");
  await page.locator(loginButtonLocator).click();

  await expect(page).toHaveURL(/inventory\.html/);
  await expect(page.locator(".inventory_list")).toBeVisible();
});
