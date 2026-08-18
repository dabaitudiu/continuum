import { expect, test } from '@playwright/test'

test('canonical mission resumes selectively and activates once', async ({ page }) => {
  const consoleProblems: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'warning' || message.type() === 'error') consoleProblems.push(message.text())
  })
  await page.goto('/')

  await page.getByRole('button', { name: 'Start mission' }).click()
  await expect(page.getByRole('button', { name: 'Inject Policy v13' })).toBeVisible()
  await expect(page.getByText('Pen test required')).toHaveCount(0)

  await page.getByRole('button', { name: 'Inject Policy v13' }).click()
  await expect(page.getByTestId('route-D42')).toContainText('STALE')
  await expect(page.getByTestId('route-D50')).toContainText('STALE')
  await expect(page.getByTestId('route-D43')).toContainText('PRESERVED')
  await expect(page.getByTestId('route-activate-vendor')).toContainText('BLOCKED')

  await page.getByRole('button', { name: 'Run affected branch' }).click()
  await expect(page.getByText('Pen test required')).toBeVisible()
  await expect(page.getByText('vendor.document.uploaded')).toBeVisible()

  await page.getByRole('button', { name: 'Upload pen test · +7 days' }).click()
  await expect(page.getByRole('button', { name: 'Run scenario again' })).toBeVisible()
  await expect(page.getByTestId('route-D57')).toContainText('VALID')
  await expect(page.getByTestId('route-D43')).toContainText('PRESERVED')
  await expect(page.getByTestId('route-activate-vendor')).toContainText('COMMITTED')
  await expect(page.getByText('Vendor activation committed exactly once')).toBeVisible()
  expect(consoleProblems).toEqual([])
})
