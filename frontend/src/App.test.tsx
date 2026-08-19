import { cleanup, render, screen, within } from '@testing-library/react'
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

function compilerStatusFixture() {
  return {
    execution_mode: 'DETERMINISTIC_REFERENCE',
    scenarios: [
      { scenario_id: 'authorized-access', label: 'Authorized access', summary: 'All critical source fragments are current and complete.', expected_disposition: 'ACCEPTED' },
      { scenario_id: 'missing-governing-clause', label: 'Missing governing clause', summary: 'The draft omits the current policy dependency.', expected_disposition: 'REJECTED_INCOMPLETE_DEPENDENCIES' },
    ],
    evidence: {
      deterministic_reference: { status: 'PASS', provider: 'REFERENCE', model: 'deterministic-reference-v1', reason: 'Repeatable product fixture; not live model evidence.', credentials_configured: true },
      openai: {
        status: 'BLOCKED', provider: 'OPENAI', model: 'gpt-5.6-luna', reason: 'OPENAI_API_KEY is not configured', credentials_configured: false,
        budget: { limit_usd: '10.000000000', spent_usd: '0E-9', reserved_usd: '0E-9', remaining_usd: '10.000000000', settled_calls: 0, reserved_calls: 0, pricing_version: 'openai-2026-08-19-v2' },
      },
      gemini: { status: 'BLOCKED', provider: 'GOOGLE', model: 'gemini-3.5-flash', reason: 'Gemini credentials are not configured', credentials_configured: false },
    },
  }
}

function compilerViewFixture(status = 'ACCEPTED', withReceipt = false) {
  const sourceRefs = [
    'policy:access@v13!policy-representation#$.rule',
    'record:employee@r18!employee-representation#$.status',
    'record:access-request@r45!request-representation#$.scope',
  ]
  const claims = [
    ['policy-rule', 'RULE', 'Current policy requires active employment and manager approval.', sourceRefs[0], 'GOVERNED_BY'],
    ['employee-status', 'FACT', 'The requester has an active FTE engineering record.', sourceRefs[1], 'SUPPORTED_BY'],
    ['request-scope', 'FACT', 'The request is limited to production read access for Project Phoenix.', sourceRefs[2], 'SUPPORTED_BY'],
  ]
  const accepted = status === 'ACCEPTED'
  return {
    scenario_id: accepted ? 'authorized-access' : 'missing-governing-clause',
    scenario_label: accepted ? 'Authorized access' : 'Missing governing clause',
    scenario_summary: accepted ? 'All critical source fragments are current and complete.' : 'The draft omits the current policy dependency.',
    execution_mode: 'DETERMINISTIC_REFERENCE',
    aggregate: {
      request: {
        request_id: `reference-compiler:${accepted ? 'authorized-access' : 'missing-governing-clause'}:abc123`,
        mission_id: 'compiler-reference-1', work_item_id: 'compile-access', agent_id: 'reference-compiler-adapter',
        world_snapshot_id: 'world:compiler-reference:v13', expected_mission_revision: 0,
        decision_type: 'PRIVILEGED_ACCESS_REVIEW', risk_class: 'HIGH', owner_scope: 'tenant:continuum-reference',
        allowed_source_refs: sourceRefs, allow_historical: false, created_at: '2026-08-19T04:30:00Z',
      },
      state: 'COMPILED',
      draft: {
        request_id: 'reference-compiler:authorized-access:abc123', decision_type: 'PRIVILEGED_ACCESS_REVIEW', proposed_outcome: 'APPROVED',
        claims: claims.map(([id, type, statement, ref, relation]) => ({
          claim_local_id: id, claim_type: type, statement,
          dependencies: [{ source_ref: ref, relation, materiality: 'CRITICAL', purpose: 'Critical authorization input' }],
          derived_from_claims: [], materiality: 'CRITICAL', confidence: 1,
        })),
        decision_dependencies: [], unresolved_questions: [], rationale_summary: 'The bounded source set was evaluated.',
        model_metadata: { provider: 'REFERENCE', model_name: 'deterministic-reference-v1', prompt_version: 'reasoner-v1', temperature: 0, execution_id: 'reference:reasoner:1', input_tokens: 0, cached_input_tokens: 0, output_tokens: 0 },
      },
      result: {
        compilation_id: accepted ? 'compilation:123' : 'blocked:123', request_id: 'reference-compiler:authorized-access:abc123', status,
        decision_candidate: accepted ? { decision_id: 'decision:123', decision_type: 'PRIVILEGED_ACCESS_REVIEW', outcome: 'APPROVED', rationale_summary: 'The bounded source set was evaluated.' } : null,
        canonical_claims: accepted ? claims.map(([id, type, statement]) => ({ claim_id: `claim:${id}`, claim_local_id: id, claim_type: type, statement, materiality: 'CRITICAL', confidence: 1 })) : [],
        canonical_edges: [], validation_findings: [],
        critic_findings: accepted ? [] : [{ finding_id: 'critic:missing:0000', finding_type: 'MISSING_DEPENDENCY', severity: 'CRITICAL', message: 'The governing privileged access policy clause is missing.', candidate_ref: sourceRefs[0], claim_local_id: null }],
        contradictions: [], compiler_version: 'sdc-1', validation_policy_version: 'validation-v1',
        compilation_hash: accepted ? 'a'.repeat(64) : null,
        model_metadata: { provider: 'REFERENCE', model_name: 'deterministic-reference-v1', prompt_version: 'reasoner-v1', temperature: 0, execution_id: 'reference:reasoner:1', input_tokens: 0, cached_input_tokens: 0, output_tokens: 0 },
        critic_model_metadata: null,
        executed_stages: accepted ? ['VALIDATED', 'REVIEWED', 'COMPILED'] : ['VALIDATED'],
      },
      outbox: [], updated_at: '2026-08-19T04:30:00Z',
    },
    sources: sourceRefs.map((source_ref, index) => ({
      source_ref, logical_key: ['privileged-access-policy', 'employee-directory-record', 'access-request-record'][index],
      artifact_type: index === 0 ? 'POLICY' : 'RECORD', source_type: index === 0 ? 'POLICY' : 'STRUCTURED_RECORD', trust_class: 'AUTHORITATIVE', authority_rank: index === 0 ? 100 : 80,
      revision_label: ['v13', 'r18', 'r45'][index], source_hash: String(index + 1).repeat(64), fragment_hash: String(index + 4).repeat(64), logical_path: ['$.rule', '$.status', '$.scope'][index], content: 'Reference content', historical: false,
    })),
    evidence: compilerStatusFixture().evidence,
    stage_trace: [
      { stage: 'REQUESTED', owner: 'COMPILER', state: 'DONE' },
      { stage: 'DRAFT_RECEIVED', owner: 'MODEL PROPOSAL', state: 'DONE' },
      { stage: 'VALIDATED', owner: 'COMPILER', state: 'DONE' },
      { stage: 'REVIEWED', owner: 'MODEL PROPOSAL', state: accepted ? 'DONE' : 'SKIPPED' },
      { stage: 'COMPILED', owner: 'COMPILER', state: accepted ? 'DONE' : 'SKIPPED' },
      { stage: 'RUNTIME_ACCEPTED', owner: 'RUNTIME', state: withReceipt ? 'DONE' : accepted ? 'ACTIVE' : 'SKIPPED' },
    ],
    runtime_receipt: withReceipt ? {
      duplicate: false, mission_id: 'compiler-reference-1', mission_revision: 1, decision_id: 'decision:123',
      claim_ids: ['claim:policy-rule', 'claim:employee-status', 'claim:request-scope'], evidence_ids: sourceRefs,
      compilation_id: 'compilation:123', compilation_hash: 'a'.repeat(64), audit_event_id: 'audit:compiler-accept:123', audit_link: '/api/demo/compiler/reference-compiler:authorized-access:abc123',
    } : null,
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

  it('shows deterministic progress and blocks a duplicate command while it is pending', async () => {
    let resolveStart!: () => void
    const pendingStart = new Promise<Record<string, never>>((resolve) => {
      resolveStart = () => resolve({})
    })
    const api: ContinuumApi = {
      listMissions: noMissions,
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-001' }),
      start: vi.fn().mockReturnValue(pendingStart),
      getControl: vi.fn()
        .mockResolvedValueOnce(control('CREATED'))
        .mockResolvedValueOnce(control('BASELINE_WAITING')),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
    }

    render(<App api={api} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Start mission' }))

    expect(screen.getByRole('button', { name: 'Starting agents…' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Mission history' })).toBeEnabled()

    resolveStart()
    expect(await screen.findByRole('button', { name: 'Inject Policy v13' })).toBeVisible()
    expect(api.start).toHaveBeenCalledTimes(1)
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

  it('retries restoration of the same durable mission after a transient failure', async () => {
    history.replaceState({}, '', '/missions/demo-existing')
    const restored = control('MISSING_EVIDENCE')
    restored.mission.mission_id = 'demo-existing'
    const api: ContinuumApi = {
      listMissions: noMissions,
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-new' }),
      start: vi.fn(),
      getControl: vi.fn()
        .mockRejectedValueOnce(new Error('runtime temporarily unavailable'))
        .mockResolvedValueOnce(restored),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
    }

    render(<App api={api} />)

    expect(await screen.findByText('runtime temporarily unavailable')).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByText('Pen test required')).toBeVisible()
    expect(api.getControl).toHaveBeenNthCalledWith(2, 'demo-existing')
    expect(api.createDemo).not.toHaveBeenCalled()
    expect(location.pathname).toBe('/missions/demo-existing')
  })

  it('reuses the scenario idempotency key when creation is retried', async () => {
    const api: ContinuumApi = {
      listMissions: noMissions,
      createDemo: vi.fn()
        .mockRejectedValueOnce(new Error('creation response was lost'))
        .mockResolvedValueOnce({ mission_id: 'demo-created-once' }),
      start: vi.fn(),
      getControl: vi.fn().mockResolvedValue({
        ...control('CREATED'),
        mission: { ...control('CREATED').mission, mission_id: 'demo-created-once' },
      }),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
    }

    render(<App api={api} />)

    expect(await screen.findByText('creation response was lost')).toBeVisible()
    const firstRequestId = vi.mocked(api.createDemo).mock.calls[0][0]
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByRole('button', { name: 'Start mission' })).toBeVisible()
    expect(api.createDemo).toHaveBeenNthCalledWith(2, firstRequestId)
    expect(location.pathname).toBe('/missions/demo-created-once')
  })

  it('retries a failed mission command without losing the current phase', async () => {
    const api: ContinuumApi = {
      listMissions: noMissions,
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-001' }),
      start: vi.fn()
        .mockRejectedValueOnce(new Error('command temporarily unavailable'))
        .mockResolvedValueOnce({}),
      getControl: vi.fn()
        .mockResolvedValueOnce(control('CREATED'))
        .mockResolvedValueOnce(control('BASELINE_WAITING')),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
    }

    render(<App api={api} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Start mission' }))

    expect(await screen.findByText('command temporarily unavailable')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Start mission' })).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Retry command' }))

    expect(await screen.findByRole('button', { name: 'Inject Policy v13' })).toBeVisible()
    expect(api.start).toHaveBeenCalledTimes(2)
    const firstRequestId = vi.mocked(api.start).mock.calls[0][1]
    expect(api.start).toHaveBeenNthCalledWith(2, 'demo-001', firstRequestId)
  })

  it('retries mission history loading in place', async () => {
    const active = control('CREATED')
    const summary: MissionSummary = {
      mission_id: 'demo-001',
      mission_type: 'VENDOR_ONBOARDING',
      subject_id: 'ACME',
      status: 'CREATED',
      revision: 0,
      event_sequence: 1,
      created_at: '2026-08-18T01:00:00Z',
      updated_at: '2026-08-18T01:00:00Z',
      counts: { work_items: 1, open_commitments: 0, side_effects: 0 },
    }
    const api: ContinuumApi = {
      listMissions: vi.fn()
        .mockRejectedValueOnce(new Error('history temporarily unavailable'))
        .mockResolvedValueOnce([summary]),
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-001' }),
      start: vi.fn(),
      getControl: vi.fn().mockResolvedValue(active),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
    }

    render(<App api={api} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Mission history' }))

    expect(await screen.findByText('history temporarily unavailable')).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Retry history' }))

    expect(await screen.findByRole('button', { name: 'Open mission demo-001' })).toBeVisible()
    expect(api.listMissions).toHaveBeenCalledTimes(2)
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

  it('operates Compiler Lab from exact source refs through a runtime receipt', async () => {
    const compiled = compilerViewFixture()
    const accepted = compilerViewFixture('ACCEPTED', true)
    const api = {
      listMissions: noMissions,
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-001' }),
      start: vi.fn(),
      getControl: vi.fn().mockResolvedValue(control('CREATED')),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
      getCompilerLabStatus: vi.fn().mockResolvedValue(compilerStatusFixture()),
      runCompilerScenario: vi.fn().mockResolvedValue(compiled),
      acceptCompilerScenario: vi.fn().mockResolvedValue(accepted),
    } as unknown as ContinuumApi

    render(<App api={api} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Compiler Lab' }))

    expect(await screen.findByText('SEMANTIC DEPENDENCY COMPILER / MODULE 01')).toBeVisible()
    expect(screen.getByText('Execution mode: DETERMINISTIC_REFERENCE')).toBeVisible()
    for (const stage of ['REQUESTED', 'DRAFT_RECEIVED', 'VALIDATED', 'REVIEWED', 'COMPILED', 'RUNTIME_ACCEPTED']) {
      expect(screen.getByText(stage)).toBeVisible()
    }
    expect(screen.getByText('OPENAI EVIDENCE')).toBeVisible()
    expect(screen.getByText('KEY NOT CONFIGURED')).toBeVisible()
    expect(screen.getByText('$0.00 / $10.00 CUMULATIVE CAP')).toBeVisible()

    await userEvent.click(screen.getByRole('button', { name: 'Run reference compilation' }))

    expect((await screen.findAllByText(source => source.includes('policy:access@v13!'))).length).toBeGreaterThanOrEqual(2)
    expect(screen.getByText('Current policy requires active employment and manager approval.')).toBeVisible()
    expect(screen.getByText('Compilation disposition: ACCEPTED')).toBeVisible()
    expect(screen.getByText('a'.repeat(64))).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Commit accepted compilation to Runtime' }))

    expect(await screen.findByText('RUNTIME ACCEPTED')).toBeVisible()
    expect(screen.getAllByText('decision:123')[0]).toBeVisible()
    expect(screen.getByText('audit:compiler-accept:123')).toBeVisible()
  })

  it('shows recorded OpenAI failure even when the current key is unavailable', async () => {
    const status = compilerStatusFixture()
    status.evidence.openai = {
      ...status.evidence.openai,
      status: 'FAIL',
      reason: 'The recorded live evidence run failed its model or metric gate',
      credentials_configured: false,
    }
    const api = {
      listMissions: noMissions,
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-001' }),
      start: vi.fn(),
      getControl: vi.fn().mockResolvedValue(control('CREATED')),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
      getCompilerLabStatus: vi.fn().mockResolvedValue(status),
    } as unknown as ContinuumApi

    render(<App api={api} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Compiler Lab' }))

    const openaiEvidence = (await screen.findByText('OPENAI EVIDENCE')).closest(
      '.evidence-cell',
    )
    expect(openaiEvidence).not.toBeNull()
    expect(within(openaiEvidence as HTMLElement).getAllByText('FAIL')).toHaveLength(2)
    expect(
      within(openaiEvidence as HTMLElement).getByText('KEY NOT CONFIGURED'),
    ).toBeVisible()
  })

  it('shows compiler rejection evidence and never offers a runtime mutation', async () => {
    const rejected = compilerViewFixture('REJECTED_INCOMPLETE_DEPENDENCIES')
    const api = {
      listMissions: noMissions,
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-001' }),
      start: vi.fn(),
      getControl: vi.fn().mockResolvedValue(control('CREATED')),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
      getCompilerLabStatus: vi.fn().mockResolvedValue(compilerStatusFixture()),
      runCompilerScenario: vi.fn().mockResolvedValue(rejected),
      acceptCompilerScenario: vi.fn(),
    } as unknown as ContinuumApi

    render(<App api={api} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Compiler Lab' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Missing governing clause' }))
    await userEvent.click(screen.getByRole('button', { name: 'Run reference compilation' }))

    expect(await screen.findByText('Compilation disposition: REJECTED_INCOMPLETE_DEPENDENCIES')).toBeVisible()
    expect(screen.getByText('The governing privileged access policy clause is missing.')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Commit accepted compilation to Runtime' })).not.toBeInTheDocument()
    expect(api.acceptCompilerScenario).not.toHaveBeenCalled()
  })

  it('retries Runtime acceptance without discarding the accepted compilation', async () => {
    const compiled = compilerViewFixture()
    const accepted = compilerViewFixture('ACCEPTED', true)
    const api = {
      listMissions: noMissions,
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-001' }),
      start: vi.fn(),
      getControl: vi.fn().mockResolvedValue(control('CREATED')),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
      getCompilerLabStatus: vi.fn().mockResolvedValue(compilerStatusFixture()),
      runCompilerScenario: vi.fn().mockResolvedValue(compiled),
      acceptCompilerScenario: vi.fn()
        .mockRejectedValueOnce(new Error('Runtime temporarily unavailable'))
        .mockResolvedValueOnce(accepted),
    } as unknown as ContinuumApi

    render(<App api={api} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Compiler Lab' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Run reference compilation' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Commit accepted compilation to Runtime' }))

    expect(await screen.findByText('Runtime temporarily unavailable')).toBeVisible()
    expect(screen.getByText('Compilation disposition: ACCEPTED')).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Retry' }))

    expect(await screen.findByText('RUNTIME ACCEPTED')).toBeVisible()
    expect(api.acceptCompilerScenario).toHaveBeenCalledTimes(2)
    expect(api.runCompilerScenario).toHaveBeenCalledTimes(1)
  })

  it('keeps the previous compilation visible when a rerun fails', async () => {
    const compiled = compilerViewFixture()
    const api = {
      listMissions: noMissions,
      createDemo: vi.fn().mockResolvedValue({ mission_id: 'demo-001' }),
      start: vi.fn(),
      getControl: vi.fn().mockResolvedValue(control('CREATED')),
      upgradePolicy: vi.fn(),
      revalidate: vi.fn(),
      uploadPenTest: vi.fn(),
      getCompilerLabStatus: vi.fn().mockResolvedValue(compilerStatusFixture()),
      runCompilerScenario: vi.fn()
        .mockResolvedValueOnce(compiled)
        .mockRejectedValueOnce(new Error('Compilation service unavailable')),
      acceptCompilerScenario: vi.fn(),
    } as unknown as ContinuumApi

    render(<App api={api} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Compiler Lab' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Run reference compilation' }))
    expect(await screen.findByText('Compilation disposition: ACCEPTED')).toBeVisible()

    await userEvent.click(screen.getByRole('button', { name: 'Run reference compilation' }))

    expect(await screen.findByText('Compilation service unavailable')).toBeVisible()
    expect(screen.getByText('Compilation disposition: ACCEPTED')).toBeVisible()
    expect(screen.getByText('a'.repeat(64))).toBeVisible()
  })
})
