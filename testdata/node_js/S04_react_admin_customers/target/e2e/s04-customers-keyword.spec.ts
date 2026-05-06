import { test, expect } from '@playwright/test'

test.describe('S04 pinned: Customers keyword filter', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth/login?demo=demo&autologin=1')
    await page.waitForURL(/\/dashboard/, { timeout: 30_000 })
    await page.goto('/customers')
    await expect(page.locator('.ant-table-tbody .ant-table-row').first()).toBeVisible({
      timeout: 30_000,
    })
  })

  test('filters by email substring (mock seed: ops@acme)', async ({ page }) => {
    await page.getByPlaceholder(/search name/i).fill('ops@acme')
    await page.getByRole('button', { name: 'Search' }).click()
    await expect(page.locator('.ant-table-tbody')).toContainText(/ops@acme\.com/i)
  })

  test('filters by owner name substring (mock seed: Jamie)', async ({ page }) => {
    await page.getByPlaceholder(/search name/i).fill('Jamie')
    await page.getByRole('button', { name: 'Search' }).click()
    await expect(page.locator('.ant-table-tbody')).toContainText(/Jamie/)
  })

  test('keyword is case insensitive for seeded company Nova', async ({ page }) => {
    await page.getByPlaceholder(/search name/i).fill('nova')
    await page.getByRole('button', { name: 'Search' }).click()
    await expect(page.locator('.ant-table-tbody')).toContainText(/Nova/)
  })

  test('nonsense keyword yields zero data rows', async ({ page }) => {
    await page.getByPlaceholder(/search name/i).fill('__zz_nomatch_xyz__')
    await page.getByRole('button', { name: 'Search' }).click()
    await expect(page.locator('.ant-table-tbody .ant-table-row')).toHaveCount(0)
  })
})
