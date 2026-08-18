import { defineConfig, devices } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const repositoryRoot = fileURLToPath(new URL('..', import.meta.url))
const frontendRoot = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: process.env.CI ? 1 : undefined,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:14173',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: [
    {
      command: 'uv run --project backend uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 18080',
      cwd: repositoryRoot,
      port: 18080,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      command: 'CONTINUUM_API_TARGET=http://127.0.0.1:18080 npm run dev -- --host 127.0.0.1 --port 14173',
      cwd: frontendRoot,
      port: 14173,
      reuseExistingServer: false,
      timeout: 30_000,
    },
  ],
})
