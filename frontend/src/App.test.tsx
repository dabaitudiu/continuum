import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { StrictMode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { App } from './App'
import type { ContinuumApi, GraphReadModel, MissionControlReadModel, MissionSummary, ScenarioPhase } from './types'

const noMissions = vi.fn().mockResolvedValue([])

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
  const graph: GraphReadModel = {
    mission_id: 'demo-001',
    phase: drifted ? 'DRIFTED' : 'INITIAL',
    summary: { stale: drifted && !completed ? 2 : 0, preserved: 1, blocked: drifted && !completed ? 1 : 0 },
    nodes: [
      { id: 'policy-v12', kind: 'artifact', label: 'security-policy', status: drifted ? 'SUPERSEDED' : 'CURRENT', version: 'v12' },
      { id: 'soc2-A31', kind: 'evidence', label: 'SOC2_CONTROL', status: 'VALID', revision: 'A31' },
      { id: 'financial-F7', kind: 'evidence', label: 'FINANCIAL_REPORT', status: 'VALID', revision: 'F7' },
      { id: 'D42', kind: 'decision', label: 'SECURITY_REVIEW', status: drifted ? completed ? 'SUPERSEDED' : 'STALE' : 'VALID', outcome: 'APPROVE' },
      { id: 'D43', kind: 'decision', label: 'FINANCIAL_REVIEW', status: 'VALID', outcome: 'PASS' },
      { id: 'D50', kind: 'decision', label: 'PROCUREMENT_REVIEW', status: drifted ? completed ? 'SUPERSEDED' : 'STALE' : 'VALID', outcome: 'APPROVE' },
      { id: 'activate-vendor', kind: 'action', label: 'ACTIVATE_VENDOR', status: drifted && !completed ? 'BLOCKED' : 'READY' },
    ],
    edges: [
      { edge_id: 'policy-D42', from_node_id: 'policy-v12', to_node_id: 'D42', relation_type: 'GOVERNED_BY', critical: true },
      { edge_id: 'soc2-D42', from_node_id: 'soc2-A31', to_node_id: 'D42', relation_type: 'SUPPORTED_BY', critical: true },
      { edge_id: 'financial-D43', from_node_id: 'financial-F7', to_node_id: 'D43', relation_type: 'SUPPORTED_BY', critical: true },
      { edge_id: 'D42-D50', from_node_id: 'D42', to_node_id: 'D50', relation_type: 'REQUIRES', critical: true },
      { edge_id: 'D43-D50', from_node_id: 'D43', to_node_id: 'D50', relation_type: 'REQUIRES', critical: true },
      { edge_id: 'D50-activate', from_node_id: 'D50', to_node_id: 'activate-vendor', relation_type: 'AUTHORIZES', critical: true },
    ],
    plan: { stale_decision_ids: [], runnable_decision_ids: [], waiting_decision_ids: [], blocked_action_ids: [], retained_decision_ids: ['D43'], cause_by_node_id: drifted ? { D42: 'policy-v12', D50: 'D42', 'activate-vendor': 'D50' } : {} },
    causes: drifted ? { D42: 'policy-v12', D50: 'D42', 'activate-vendor': 'D50' } : {},
    events: [],
    dispatches: [],
  }
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
    graph,
  }
}

describe('App', () => {
  beforeEach(() => {
    localStorage.clear()
    history.replaceState({}, '', '/')
  })
  afterEach(cleanup)

  it('operates the canonical story through completion', async () => {
    const api: ContinuumApi = {
      listMissions: noMissions,
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

  it('restores the mission encoded in the browser route without creating another', async () => {
    history.replaceState({}, '', '/missions/demo-existing')
    const api: ContinuumApi = {
      listMissions: noMissions,
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-new' }),
      start: vi.fn(),
      getControl: vi.fn().mockResolvedValue({
        ...control('MISSING_EVIDENCE'),
        mission: {
          ...control('MISSING_EVIDENCE').mission,
          mission_id: 'demo-existing',
        },
      }),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
    }

    render(<App api={api} />)

    expect(await screen.findByText('Pen test required')).toBeVisible()
    expect(api.getControl).toHaveBeenCalledWith('demo-existing')
    expect(api.createDemo).not.toHaveBeenCalled()
  })

  it('restores the last mission when opening the root URL', async () => {
    localStorage.setItem('continuum.activeMissionId', 'demo-stored')
    const stored = control('BASELINE_WAITING')
    stored.mission.mission_id = 'demo-stored'
    const api: ContinuumApi = {
      listMissions: noMissions,
      createDemo: vi.fn(),
      start: vi.fn(),
      getControl: vi.fn().mockResolvedValue(stored),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
    }

    render(<App api={api} />)

    expect(await screen.findByRole('button', { name: 'Inject Policy v13' })).toBeVisible()
    expect(location.pathname).toBe('/missions/demo-stored')
    expect(api.createDemo).not.toHaveBeenCalled()
  })

  it('creates only one mission under React StrictMode and records its route', async () => {
    const api: ContinuumApi = {
      listMissions: noMissions,
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-strict' }),
      start: vi.fn(),
      getControl: vi.fn().mockResolvedValue({
        ...control('CREATED'),
        mission: { ...control('CREATED').mission, mission_id: 'demo-strict' },
      }),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
    }

    render(<StrictMode><App api={api} /></StrictMode>)

    expect(await screen.findByRole('button', { name: 'Start mission' })).toBeVisible()
    expect(api.createDemo).toHaveBeenCalledTimes(1)
    expect(location.pathname).toBe('/missions/demo-strict')
    expect(localStorage.getItem('continuum.activeMissionId')).toBe('demo-strict')
  })

  it('replaces a stale mission pointer only when the API confirms it is missing', async () => {
    history.replaceState({}, '', '/missions/demo-gone')
    localStorage.setItem('continuum.activeMissionId', 'demo-gone')
    const missing = Object.assign(new Error('mission does not exist'), {
      code: 'MISSION_NOT_FOUND',
    })
    const api: ContinuumApi = {
      listMissions: noMissions,
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-recovered' }),
      start: vi.fn(),
      getControl: vi.fn()
        .mockRejectedValueOnce(missing)
        .mockResolvedValueOnce({
          ...control('CREATED'),
          mission: { ...control('CREATED').mission, mission_id: 'demo-recovered' },
        }),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
    }

    render(<App api={api} />)

    expect(await screen.findByRole('button', { name: 'Start mission' })).toBeVisible()
    expect(api.createDemo).toHaveBeenCalledTimes(1)
    expect(location.pathname).toBe('/missions/demo-recovered')
    expect(localStorage.getItem('continuum.activeMissionId')).toBe('demo-recovered')
  })

  it('opens a recent mission from mission history', async () => {
    history.replaceState({}, '', '/missions/demo-current')
    const current = control('CREATED')
    current.mission.mission_id = 'demo-current'
    const completed = control('COMPLETED')
    completed.mission.mission_id = 'demo-completed'
    const summaries: MissionSummary[] = [
      {
        mission_id: 'demo-current',
        mission_type: 'VENDOR_ONBOARDING',
        subject_id: 'ACME',
        status: 'CREATED',
        revision: 0,
        event_sequence: 1,
        created_at: '2026-08-18T01:00:00Z',
        updated_at: '2026-08-18T01:00:00Z',
        counts: { work_items: 1, open_commitments: 0, side_effects: 0 },
      },
      {
        mission_id: 'demo-completed',
        mission_type: 'VENDOR_ONBOARDING',
        subject_id: 'ACME',
        status: 'COMPLETED',
        revision: 4,
        event_sequence: 18,
        created_at: '2026-08-18T00:00:00Z',
        updated_at: '2026-08-18T00:30:00Z',
        counts: { work_items: 6, open_commitments: 0, side_effects: 1 },
      },
    ]
    const api: ContinuumApi = {
      listMissions: vi.fn().mockResolvedValue(summaries),
      createDemo: vi.fn(),
      start: vi.fn(),
      getControl: vi.fn()
        .mockResolvedValueOnce(current)
        .mockResolvedValueOnce(completed),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
    }

    render(<App api={api} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Mission history' }))

    expect(await screen.findByText('demo-completed')).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Open mission demo-completed' }))

    expect(await screen.findByRole('button', { name: 'Run scenario again' })).toBeVisible()
    expect(location.pathname).toBe('/missions/demo-completed')
    expect(localStorage.getItem('continuum.activeMissionId')).toBe('demo-completed')
  })

  it('shows the direct policy and evidence provenance for a selected decision', async () => {
    history.replaceState({}, '', '/missions/demo-drifted')
    const drifted = control('POLICY_DRIFT')
    drifted.mission.mission_id = 'demo-drifted'
    const api: ContinuumApi = {
      listMissions: noMissions,
      createDemo: vi.fn(),
      start: vi.fn(),
      getControl: vi.fn().mockResolvedValue(drifted),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
    }

    render(<App api={api} />)
    await userEvent.click(await screen.findByTestId('route-D42'))

    expect(screen.getByText('DIRECT PROVENANCE')).toBeVisible()
    expect(screen.getByText('policy-v12')).toBeVisible()
    expect(screen.getByText('GOVERNED_BY')).toBeVisible()
    expect(screen.getByText('soc2-A31')).toBeVisible()
    expect(screen.getByText('SUPPORTED_BY')).toBeVisible()

    await userEvent.click(screen.getByTestId('route-D43'))

    expect(screen.getByText('financial-F7')).toBeVisible()
    expect(screen.queryByText('policy-v12')).not.toBeInTheDocument()
  })
})
