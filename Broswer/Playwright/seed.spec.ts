import { test, expect } from '@playwright/test';

/**
 * Seed test for ServiceNow Developer Portal.
 *
 * This seed sets up the environment used by the Playwright Test Agents
 * (planner / generator / healer). It navigates to the ServiceNow Developer
 * Portal homepage so generated tests have a ready-to-use `page` context.
 *
 * Credentials are read from the local .env file:
 *   SERVICENOW_USERNAME, SERVICENOW_PASSWORD
 */
test.describe('ServiceNow Developer Portal', () => {
  test('seed', async ({ page }) => {
    await page.goto('https://developer.servicenow.com/dev.do');
    await expect(page).toHaveTitle(/ServiceNow/i);
  });
});
