import type { ContinuumApi, GraphReadModel } from './types'

class ContinuumApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  const body = await response.json()
  if (!response.ok) {
    const detail = body.detail ?? {}
    throw new ContinuumApiError(
      detail.message ?? `Request failed with status ${response.status}`,
      detail.code ?? 'UNKNOWN_API_ERROR',
    )
  }
  return body as T
}

export const httpApi: ContinuumApi = {
  reset: () => request('/api/demo/reset', { method: 'POST' }),
  getGraph: (missionId) => request(`/api/missions/${missionId}/graph`),
  upgradePolicy: (missionId, eventId) =>
    request<GraphReadModel>('/api/demo/policy/upgrade', {
      method: 'POST',
      body: JSON.stringify({ mission_id: missionId, event_id: eventId }),
    }),
  revalidate: (missionId, requestId) =>
    request<GraphReadModel>(`/api/missions/${missionId}/revalidate`, {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId }),
    }),
}
