import type {
  CompilerLabStatusDto,
  CompilerLabViewDto,
  ContinuumApi,
  GraphReadModel,
  MissionControlReadModel,
  MissionSummary,
} from './types'

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
  const raw = await response.text()
  let body: Record<string, unknown> = {}
  if (raw) {
    try {
      body = JSON.parse(raw) as Record<string, unknown>
    } catch {
      body = { raw: raw.slice(0, 500) }
    }
  }
  if (!response.ok) {
    const detail = typeof body.detail === 'object' && body.detail !== null
      ? body.detail as Record<string, unknown>
      : {}
    throw new ContinuumApiError(
      typeof detail.message === 'string'
        ? detail.message
        : `Request failed with status ${response.status}${typeof body.raw === 'string' ? `: ${body.raw}` : ''}`,
      typeof detail.code === 'string' ? detail.code : `HTTP_${response.status}`,
    )
  }
  return body as T
}

export const httpApi: ContinuumApi = {
  listMissions: (limit = 20) => request<MissionSummary[]>(`/api/missions?limit=${limit}`),
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
  getCompilerLabStatus: () => request<CompilerLabStatusDto>('/api/demo/compiler/status'),
  runCompilerScenario: (scenarioId, requestId) =>
    request<CompilerLabViewDto>(`/api/demo/compiler/scenarios/${encodeURIComponent(scenarioId)}`, {
      method: 'POST',
      body: JSON.stringify({ request_id: requestId }),
    }),
  acceptCompilerScenario: (requestId) =>
    request<CompilerLabViewDto>(`/api/demo/compiler/${encodeURIComponent(requestId)}/accept`, {
      method: 'POST',
    }),
}
