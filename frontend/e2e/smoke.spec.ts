import { expect, test } from '@playwright/test'

test('landing page renders and links to login', async ({ page }) => {
  await page.goto('/')
  await expect(page.locator('body')).toContainText(/BotForge/i)
  await page.goto('/login')
  await expect(page.locator('input[type="email"]')).toBeVisible()
  await expect(page.locator('input[type="password"]')).toBeVisible()
})

test('mock credentials open the dashboard', async ({ page }) => {
  await page.goto('/login')
  await page.locator('form button[type="submit"]').click()
  await expect(page).toHaveURL(/\/app/)
  await expect(page.locator('body')).toContainText(/BotForge/i)
})
