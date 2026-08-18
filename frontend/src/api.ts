import type { ContinuumApi, GraphReadModel, MissionControlReadModel } from './types'

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
  createDemo: (requestId) => request('/api/missions/demo', {
    method: 'POST',
    body: JSON.stringify({ request_id: requestId }),
  }),
  start: (missionId, requestId) => request(`/api/missions/${missionId}/start`, {
    method: 'POST',
    body: JSON.stringify({ request_id: requestId }),
  }),
  getControl: (missionId) => request<MissionControlReadModel>(`/api/missions/${missionId}/control`),
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
  uploadPenTest: (missionId, eventId) => request('/api/demo/documents/pen-test', {
    method: 'POST',
    body: JSON.stringify({ mission_id: missionId, event_id: eventId }),
  }),
}
