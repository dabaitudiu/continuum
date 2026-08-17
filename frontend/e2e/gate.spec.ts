import { expect, test } from '@playwright/test'

test('policy drift preserves D43 and dispatches only D42', async ({ page }) => {
  const consoleWarnings: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'warning' || message.type() === 'error') {
      consoleWarnings.push(message.text())
    }
  })
  await page.goto('/')
  await expect(page.getByText('All decisions are valid.')).toBeVisible()

  await page.getByRole('button', { name: 'Inject policy v13' }).click()
  await expect(page.getByText('External policy changed.')).toBeVisible()
  await expect(page.getByTestId('node-D42')).toContainText('STALE')
  await expect(page.getByTestId('node-D50')).toContainText('STALE')
  await expect(page.getByTestId('node-D43')).toContainText('VALID')
  await expect(page.getByTestId('node-D43')).toContainText('PRESERVED')
  await expect(page.getByTestId('node-activate-vendor')).toContainText('BLOCKED')
  await expect(page.getByTestId('node-D42')).toBeVisible()
  await expect(page.getByTestId('node-D43')).toBeVisible()
  await expect(page.getByTestId('node-D50')).toBeVisible()
  await expect(page.getByTestId('node-activate-vendor')).toBeVisible()

  await page.getByRole('button', { name: 'Run affected branch' }).click()
  await expect(page.getByTestId('node-D42')).toContainText('REVALIDATING')
  await expect(page.getByTestId('node-D43')).toContainText('VALID')
  await expect(page.getByText('Waiting: D50')).toBeVisible()
  expect(consoleWarnings).toEqual([])
})
