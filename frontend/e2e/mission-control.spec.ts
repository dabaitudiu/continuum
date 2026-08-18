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

  await page.getByTestId('route-D42').click()
  const securityProvenance = page.getByRole('region', { name: 'Direct provenance for D42' })
  await expect(securityProvenance.getByText('policy-v12')).toBeVisible()
  await expect(securityProvenance.getByText('GOVERNED_BY')).toBeVisible()
  await expect(securityProvenance.getByText('soc2-A31')).toBeVisible()

  await page.getByTestId('route-D43').click()
  const financialProvenance = page.getByRole('region', { name: 'Direct provenance for D43' })
  await expect(financialProvenance.getByText('financial-F7')).toBeVisible()
  await expect(financialProvenance.getByText('SUPPORTED_BY')).toBeVisible()

  await page.getByRole('button', { name: 'Run affected branch' }).click()
  await expect(page.getByText('Pen test required')).toBeVisible()
  await expect(page.getByText('vendor.document.uploaded')).toBeVisible()
  const waitingMissionUrl = page.url()

  await page.reload()

  await expect(page).toHaveURL(waitingMissionUrl)
  await expect(page.getByText('Pen test required')).toBeVisible()
  await expect(page.getByRole('button', { name: 'Upload pen test · +7 days' })).toBeVisible()

  await page.getByRole('button', { name: 'Upload pen test · +7 days' }).click()
  await expect(page.getByRole('button', { name: 'Run scenario again' })).toBeVisible()
  await expect(page.getByTestId('route-D57')).toContainText('VALID')
  await expect(page.getByTestId('route-D43')).toContainText('PRESERVED')
  await expect(page.getByTestId('route-activate-vendor')).toContainText('COMMITTED')
  await expect(page.getByText('Vendor activation committed exactly once')).toBeVisible()
  const completedMissionUrl = page.url()
  const completedMissionId = new URL(completedMissionUrl).pathname.split('/').at(-1)!

  await page.getByRole('button', { name: 'Reset' }).click()
  await expect(page.getByRole('button', { name: 'Start mission' })).toBeVisible()
  await expect(page).not.toHaveURL(completedMissionUrl)
  await page.getByRole('button', { name: 'Mission history' }).click()
  await expect(page.getByText(completedMissionId)).toBeVisible()
  await page.getByRole('button', { name: `Open mission ${completedMissionId}` }).click()

  await expect(page).toHaveURL(completedMissionUrl)
  await expect(page.getByRole('button', { name: 'Run scenario again' })).toBeVisible()
  expect(consoleProblems).toEqual([])
})

test('mobile navigation stays visible and the mission completes from the keyboard', async ({ page }) => {
  const viewportWidth = 320
  await page.setViewportSize({ width: viewportWidth, height: 844 })
  await page.goto('/')

  for (const name of ['Mission route', 'Decision graph', 'Mission history']) {
    const button = page.getByRole('button', { name })
    const bounds = await button.boundingBox()
    expect(bounds, `${name} must have rendered bounds`).not.toBeNull()
    expect(bounds!.x, `${name} must not be clipped on the left`).toBeGreaterThanOrEqual(0)
    expect(bounds!.x + bounds!.width, `${name} must not be clipped on the right`).toBeLessThanOrEqual(viewportWidth)
    expect(await button.evaluate((element) => element.scrollWidth <= element.clientWidth), `${name} text must fit its control`).toBe(true)
  }

  const actions = [
    'Start mission',
    'Inject Policy v13',
    'Run affected branch',
    'Upload pen test · +7 days',
  ]
  for (const action of actions) {
    const button = page.getByRole('button', { name: action })
    await button.focus()
    await page.keyboard.press('Enter')
  }

  await expect(page.getByRole('button', { name: 'Run scenario again' })).toBeVisible()
  await expect(page.getByTestId('route-activate-vendor')).toContainText('COMMITTED')
})
