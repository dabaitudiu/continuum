import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { App } from './App'
import type { ContinuumApi, GraphReadModel, GraphNodeDto } from './types'

const initialNodes: GraphNodeDto[] = [
  { id: 'policy-v12', kind: 'artifact', label: 'Security policy', status: 'CURRENT', version: 'v12' },
  { id: 'soc2-A31', kind: 'evidence', label: 'SOC2 control', status: 'VALID', revision: 'A31' },
  { id: 'financial-F7', kind: 'evidence', label: 'Financial report', status: 'VALID', revision: 'F7' },
  { id: 'D42', kind: 'decision', label: 'Security review', status: 'VALID', execution_count: 1 },
  { id: 'D43', kind: 'decision', label: 'Financial review', status: 'VALID', execution_count: 1 },
  { id: 'D50', kind: 'decision', label: 'Procurement review', status: 'VALID', execution_count: 1 },
  { id: 'activate-vendor', kind: 'action', label: 'Activate vendor', status: 'READY' },
]

const edges: GraphReadModel['edges'] = [
  { edge_id: 'policy-D42', from_node_id: 'policy-v12', to_node_id: 'D42', relation_type: 'GOVERNED_BY', critical: true },
  { edge_id: 'soc2-D42', from_node_id: 'soc2-A31', to_node_id: 'D42', relation_type: 'SUPPORTED_BY', critical: true },
  { edge_id: 'financial-D43', from_node_id: 'financial-F7', to_node_id: 'D43', relation_type: 'SUPPORTED_BY', critical: true },
  { edge_id: 'D42-D50', from_node_id: 'D42', to_node_id: 'D50', relation_type: 'REQUIRES', critical: true },
  { edge_id: 'D43-D50', from_node_id: 'D43', to_node_id: 'D50', relation_type: 'REQUIRES', critical: true },
  { edge_id: 'D50-activate', from_node_id: 'D50', to_node_id: 'activate-vendor', relation_type: 'AUTHORIZES', critical: true },
]

function readModel(phase: GraphReadModel['phase']): GraphReadModel {
  const drifted = phase !== 'INITIAL'
  const nodes = initialNodes.map((node) => {
    if (!drifted) return { ...node }
    if (node.id === 'policy-v12') return { ...node, status: 'SUPERSEDED' as const }
    if (node.id === 'D42') {
      return {
        ...node,
        status: phase === 'REVALIDATING' ? 'REVALIDATING' as const : 'STALE' as const,
        execution_count: phase === 'REVALIDATING' ? 2 : 1,
      }
    }
    if (node.id === 'D50') return { ...node, status: 'STALE' as const }
    if (node.id === 'activate-vendor') return { ...node, status: 'BLOCKED' as const }
    return { ...node }
  })
  if (drifted) {
    nodes.splice(1, 0, {
      id: 'policy-v13',
      kind: 'artifact',
      label: 'Security policy',
      status: 'CURRENT',
      version: 'v13',
      supersedes_artifact_id: 'policy-v12',
    })
  }
  return {
    mission_id: 'demo-001',
    phase,
    summary: drifted
      ? { stale: phase === 'REVALIDATING' ? 1 : 2, preserved: 1, blocked: 1 }
      : { stale: 0, preserved: 3, blocked: 0 },
    nodes,
    edges,
    plan: drifted
      ? {
          stale_decision_ids: phase === 'REVALIDATING' ? ['D50'] : ['D42', 'D50'],
          runnable_decision_ids: phase === 'REVALIDATING' ? [] : ['D42'],
          waiting_decision_ids: ['D50'],
          blocked_action_ids: ['activate-vendor'],
          retained_decision_ids: ['D43'],
          cause_by_node_id: { D42: 'policy-v12', D50: 'D42', 'activate-vendor': 'D50' },
        }
      : {
          stale_decision_ids: [],
          runnable_decision_ids: [],
          waiting_decision_ids: [],
          blocked_action_ids: [],
          retained_decision_ids: ['D42', 'D43', 'D50'],
          cause_by_node_id: {},
        },
    causes: drifted ? { D42: 'policy-v12', D50: 'D42', 'activate-vendor': 'D50' } : {},
    events: drifted
      ? [{ event_id: 'evt-1', event_type: 'policy.version.changed', payload: {} }]
      : [],
    dispatches: phase === 'REVALIDATING'
      ? [{ dispatch_id: 'dispatch-1', request_id: 'request-1', decision_id: 'D42', work_type: 'REVALIDATE_DECISION', status: 'DISPATCHED' }]
      : [],
  }
}

function createFakeApi(): ContinuumApi & {
  upgradePolicy: ReturnType<typeof vi.fn>
  revalidate: ReturnType<typeof vi.fn>
} {
  return {
    reset: vi.fn().mockResolvedValue({ mission_id: 'demo-001' }),
    getGraph: vi.fn().mockResolvedValue(readModel('INITIAL')),
    upgradePolicy: vi.fn().mockResolvedValue(readModel('DRIFTED')),
    revalidate: vi.fn().mockResolvedValue(readModel('REVALIDATING')),
  }
}

describe('App', () => {
  it('shows drift impact, preserved work, and dispatches only D42', async () => {
    const api = createFakeApi()
    render(<App api={api} />)

    expect(await screen.findByText('All decisions are valid.')).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Inject policy v13' }))
    expect(await screen.findByText('External policy changed.')).toBeVisible()
    expect(screen.getByText('2 stale')).toBeVisible()
    expect(screen.getByText('1 preserved')).toBeVisible()
    expect(screen.getByTestId('node-D43')).toHaveTextContent('PRESERVED')

    await userEvent.click(screen.getByRole('button', { name: 'Run affected branch' }))
    expect(api.revalidate).toHaveBeenCalledWith('demo-001', expect.any(String))
    await waitFor(() => expect(screen.getByText('REVALIDATING')).toBeVisible())
    expect(screen.getByText('Waiting: D50')).toBeVisible()
  })
})
