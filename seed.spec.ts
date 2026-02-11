import { test, expect } from '@playwright/test';

// ✅ Store user info as variables (simple)
const ABSHER_URL =
  'https://www.absher.sa/wps/portal/individuals/Home/homepublic';

// ⚠️ Prefer env vars for secrets (recommended)
// In PowerShell:
//   $env:ABSHER_USERNAME="your-id-or-username"
//   $env:ABSHER_PASSWORD="your-password"
const USERNAME = 'Ahmed Ashraf';
const PASSWORD = '123';

test.describe('Absher login', () => {
  test('login with stored variables', async ({ page }) => {
    // 1) Open Absher home
    await page.goto(ABSHER_URL);
    await page.waitForLoadState('networkidle');

    // 2) Accept cookies if present
    const agreeBtn = page.getByRole('button', { name: /^agree$/i });
    if (await agreeBtn.isVisible().catch(() => false)) {
      await agreeBtn.click();
    }

    // 3) Locate fields (robust approach)
    // These placeholders are visible in your screenshot
    const usernameInput = page.getByPlaceholder(/username or id number/i);
    const passwordInput = page.getByPlaceholder(/^password$/i);

    // 4) Fill credentials
    await usernameInput.fill(USERNAME);
    await passwordInput.fill(PASSWORD);

    // 5) Click "Log in"
    await page.getByRole('button', { name: /^log in$/i }).click();

    // 6) Wait for navigation / result
    await page.waitForLoadState('networkidle');

    // 7) Basic verification (choose one that matches your real behavior)
    // Option A: URL changes away from homepublic
    await expect(page).not.toHaveURL(/homepublic/i);

    // Option B (alternative): you see something that only appears after login
    // await expect(page.getByText(/dashboard|services|my services/i)).toBeVisible();
  });
});
