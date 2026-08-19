import { afterEach, describe, expect, it, vi } from 'vitest'

import { httpApi } from './api'

describe('HTTP API error boundary', () => {
  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('preserves HTTP status and bounded text for a non-JSON gateway error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response('upstream timeout', {
        status: 504,
        headers: { 'Content-Type': 'text/plain' },
      }),
    ))

    await expect(httpApi.getCompilerLabStatus?.()).rejects.toMatchObject({
      code: 'HTTP_504',
      message: 'Request failed with status 504: upstream timeout',
    })
  })

  it('preserves HTTP status when an error response is a JSON primitive', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(
      new Response('null', {
        status: 502,
        headers: { 'Content-Type': 'application/json' },
      }),
    ))

    await expect(httpApi.getCompilerLabStatus?.()).rejects.toMatchObject({
      code: 'HTTP_502',
      message: 'Request failed with status 502: null',
    })
  })
})
