import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import { App } from './App'
import type { ContinuumApi, MissionControlReadModel, ScenarioPhase } from './types'

function control(phase: ScenarioPhase): MissionControlReadModel {
  const drifted = ['POLICY_DRIFT', 'MISSING_EVIDENCE', 'COMPLETED'].includes(phase)
  const completed = phase === 'COMPLETED'
  const missing = phase === 'MISSING_EVIDENCE'
  const next = {
    CREATED: 'START',
    BASELINE_WAITING: 'INJECT_POLICY',
    POLICY_DRIFT: 'RUN_REVALIDATION',
    MISSING_EVIDENCE: 'UPLOAD_PEN_TEST',
    COMPLETED: 'RESET',
  } as const
  return {
    mission: { mission_id: 'demo-001', status: completed ? 'COMPLETED' : phase === 'POLICY_DRIFT' ? 'REVALIDATING' : phase === 'CREATED' ? 'CREATED' : 'WAITING', created_at: '2026-08-18T00:00:00Z', updated_at: '2026-08-18T00:00:00Z' },
    subject: { id: 'ACME', name: 'Acme Analytics' },
    scenario_phase: phase,
    next_action: next[phase],
    execution_mode: 'LOCAL_DETERMINISTIC',
    current_policy: drifted ? 'v13' : 'v12',
    vendor_status: completed ? 'ACTIVE' : 'PENDING',
    agent_lanes: [
      { agent_id: 'vendor-agent', label: 'VENDOR AGENT', status: 'SUCCEEDED', checkpoints: [{ id: 'vendor-intake', label: 'Vendor intake', status: 'VALID', kind: 'work' }] },
      { agent_id: 'security-agent', label: 'SECURITY AGENT', status: missing ? 'WAITING' : 'SUCCEEDED', checkpoints: [
        { id: 'D42', label: 'Security decision', status: drifted ? completed ? 'SUPERSEDED' : 'STALE' : 'VALID', kind: 'decision' },
        ...(missing ? [{ id: 'pen-wait', label: 'Pen test required', status: 'WAITING', kind: 'commitment' as const }] : []),
        ...(completed ? [{ id: 'D57', label: 'Security revalidated', status: 'VALID', kind: 'decision' as const }] : []),
      ] },
      { agent_id: 'procurement-agent', label: 'PROCUREMENT AGENT', status: completed ? 'SUCCEEDED' : 'WAITING', checkpoints: [
        { id: 'D43', label: 'Financial review', status: 'VALID', kind: 'decision', preserved: drifted },
        { id: 'D50', label: 'Procurement decision', status: drifted ? completed ? 'SUPERSEDED' : 'STALE' : 'VALID', kind: 'decision' },
        { id: 'activate-vendor', label: 'Vendor active', status: completed ? 'COMMITTED' : drifted ? 'BLOCKED' : 'READY', kind: 'action' },
      ] },
    ],
    commitments: missing ? [{ commitment_id: 'pen-wait', event_type: 'vendor.document.uploaded', predicate: { vendor_id: 'ACME', document_type: 'PEN_TEST' }, status: 'OPEN', created_at: '2026-08-18T00:00:00Z' }] : [],
    side_effects: completed ? [{ side_effect_id: 'activate', effect_type: 'ACTIVATE_VENDOR', status: 'COMMITTED' }] : [],
    timeline: [{ audit_event_id: `audit-${phase}`, event_sequence: 1, event_type: completed ? 'mission.completed' : 'mission.created', payload: {}, occurred_at: '2026-08-18T00:00:00Z' }],
    graph: { mission_id: 'demo-001', phase: drifted ? 'DRIFTED' : 'INITIAL', summary: { stale: drifted && !completed ? 2 : 0, preserved: 1, blocked: drifted && !completed ? 1 : 0 }, nodes: [], edges: [], plan: { stale_decision_ids: [], runnable_decision_ids: [], waiting_decision_ids: [], blocked_action_ids: [], retained_decision_ids: ['D43'], cause_by_node_id: {} }, causes: {}, events: [], dispatches: [] },
  }
}

describe('App', () => {
  it('operates the canonical story through completion', async () => {
    const api: ContinuumApi = {
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-001' }),
      start: vi.fn().mockResolvedValue({}),
      getControl: vi.fn()
        .mockResolvedValueOnce(control('CREATED'))
        .mockResolvedValueOnce(control('BASELINE_WAITING'))
        .mockResolvedValueOnce(control('POLICY_DRIFT'))
        .mockResolvedValueOnce(control('MISSING_EVIDENCE'))
        .mockResolvedValueOnce(control('COMPLETED')),
      upgradePolicy: vi.fn().mockResolvedValue({}),
      revalidate: vi.fn().mockResolvedValue({}),
      uploadPenTest: vi.fn().mockResolvedValue({}),
    }
    render(<App api={api} />)

    await userEvent.click(await screen.findByRole('button', { name: 'Start mission' }))
    expect(await screen.findByRole('button', { name: 'Inject Policy v13' })).toBeVisible()
    expect(screen.queryByText('Pen test required')).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Inject Policy v13' }))
    expect(await screen.findByTestId('route-D42')).toHaveTextContent('STALE')
    expect(screen.getByTestId('route-D50')).toHaveTextContent('STALE')
    expect(screen.getByTestId('route-D43')).toHaveTextContent('PRESERVED')

    await userEvent.click(screen.getByRole('button', { name: 'Run affected branch' }))
    expect(await screen.findByText('Pen test required')).toBeVisible()
    expect(screen.getByText('vendor.document.uploaded')).toBeVisible()

    await userEvent.click(screen.getByRole('button', { name: 'Upload pen test · +7 days' }))
    expect(await screen.findByRole('button', { name: 'Run scenario again' })).toBeVisible()
    expect(screen.getByTestId('route-D57')).toHaveTextContent('VALID')
    expect(screen.getByTestId('route-activate-vendor')).toHaveTextContent('COMMITTED')
  })
})
