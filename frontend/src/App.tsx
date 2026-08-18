import {
  AlertTriangle,
  ArrowRight,
  Check,
  CircleStop,
  Clock3,
  GitBranch,
  RotateCcw,
  ShieldCheck,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

import { DecisionGraph } from './components/DecisionGraph'
import type {
  ContinuumApi,
  MissionControlReadModel,
  MissionSummary,
  NextAction,
  RouteCheckpoint,
} from './types'

function uniqueId(prefix: string): string {
  const suffix = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}`
  return `${prefix}-${suffix}`
}

const activeMissionKey = 'continuum.activeMissionId'

function missionIdFromRoute(): string | null {
  const match = window.location.pathname.match(/^\/missions\/([^/]+)\/?$/)
  if (!match) return null
  try {
    return decodeURIComponent(match[1])
  } catch {
    return null
  }
}

function storedMissionId(): string | null {
  try {
    return localStorage.getItem(activeMissionKey)
  } catch {
    return null
  }
}

function rememberMission(missionId: string): void {
  try {
    localStorage.setItem(activeMissionKey, missionId)
  } catch {
    // The route remains the durable browser pointer when storage is unavailable.
  }
  const path = `/missions/${encodeURIComponent(missionId)}`
  if (window.location.pathname !== path) window.history.replaceState({}, '', path)
}

function forgetMission(): void {
  try {
    localStorage.removeItem(activeMissionKey)
  } catch {
    // A failed storage cleanup must not block recovery from the canonical API.
  }
  window.history.replaceState({}, '', '/')
}

function isMissionNotFound(error: unknown): boolean {
  return typeof error === 'object'
    && error !== null
    && 'code' in error
    && error.code === 'MISSION_NOT_FOUND'
}

const actionCopy: Record<NextAction, { label: string; busy: string }> = {
  START: { label: 'Start mission', busy: 'Starting agents…' },
  INJECT_POLICY: { label: 'Inject Policy v13', busy: 'Applying policy event…' },
  RUN_REVALIDATION: { label: 'Run affected branch', busy: 'Revalidating security…' },
  UPLOAD_PEN_TEST: { label: 'Upload pen test · +7 days', busy: 'Resuming mission…' },
  RESET: { label: 'Run scenario again', busy: 'Creating fresh mission…' },
}

const phaseCopy = {
  CREATED: ['READY TO START', 'A seeded vendor, policy, and evidence set is ready.'],
  BASELINE_WAITING: ['WAITING', 'Policy v12 authorized the route. Procurement is waiting on an external activation window.'],
  POLICY_DRIFT: ['REVALIDATING', 'Policy v13 severed only the decisions that depended on v12.'],
  MISSING_EVIDENCE: ['WAITING FOR EVIDENCE', 'Security revalidation requires one external penetration-test document.'],
  COMPLETED: ['COMPLETED', 'The resumed route produced fresh authorization and activated the vendor exactly once.'],
} as const

export function App({ api }: { api: ContinuumApi }) {
  const [control, setControl] = useState<MissionControlReadModel | null>(null)
  const [busy, setBusy] = useState(false)
  const [historyBusy, setHistoryBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [view, setView] = useState<'route' | 'graph' | 'missions'>('route')
  const [missions, setMissions] = useState<MissionSummary[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const initialized = useRef(false)

  const createScenario = useCallback(async () => {
    setBusy(true)
    setError(null)
    try {
      const created = await api.createDemo(uniqueId('create'))
      const createdControl = await api.getControl(created.mission_id)
      rememberMission(created.mission_id)
      setControl(createdControl)
      setSelectedId(null)
      setView('route')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to create the demo mission')
    } finally {
      setBusy(false)
    }
  }, [api])

  const restoreOrCreateScenario = useCallback(async () => {
    const missionId = missionIdFromRoute() ?? storedMissionId()
    if (!missionId) {
      await createScenario()
      return
    }
    setBusy(true)
    setError(null)
    try {
      const restored = await api.getControl(missionId)
      rememberMission(missionId)
      setControl(restored)
    } catch (caught) {
      if (isMissionNotFound(caught)) {
        forgetMission()
        await createScenario()
        return
      }
      setError(caught instanceof Error ? caught.message : 'Unable to restore the mission')
    } finally {
      setBusy(false)
    }
  }, [api, createScenario])

  useEffect(() => {
    if (initialized.current) return
    initialized.current = true
    void restoreOrCreateScenario()
  }, [restoreOrCreateScenario])

  const runAction = async () => {
    if (!control || busy) return
    setBusy(true)
    setError(null)
    const missionId = control.mission.mission_id
    try {
      switch (control.next_action) {
        case 'START':
          await api.start(missionId, uniqueId('start'))
          break
        case 'INJECT_POLICY':
          await api.upgradePolicy(missionId, uniqueId('policy'))
          break
        case 'RUN_REVALIDATION':
          await api.revalidate(missionId, uniqueId('revalidate'))
          break
        case 'UPLOAD_PEN_TEST':
          await api.uploadPenTest(missionId, uniqueId('pen-test'))
          break
        case 'RESET':
          await createScenario()
          return
      }
      setControl(await api.getControl(missionId))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Mission command failed')
    } finally {
      setBusy(false)
    }
  }

  const openHistory = async () => {
    setView('missions')
    setHistoryBusy(true)
    setError(null)
    try {
      setMissions(await api.listMissions(20))
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to load mission history')
    } finally {
      setHistoryBusy(false)
    }
  }

  const openMission = async (missionId: string) => {
    if (busy || missionId === control?.mission.mission_id) {
      setView('route')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const restored = await api.getControl(missionId)
      rememberMission(missionId)
      setControl(restored)
      setSelectedId(null)
      setView('route')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Unable to open the mission')
    } finally {
      setBusy(false)
    }
  }

  if (!control) {
    return (
      <main className="loading-state" aria-busy={busy}>
        <span className="brand-mark">C</span>
        <p>{error ?? 'Preparing deterministic mission…'}</p>
        {error ? <button onClick={() => void createScenario()}>Retry</button> : null}
      </main>
    )
  }

  const [phaseLabel, phaseDescription] = phaseCopy[control.scenario_phase]
  const selected = control.agent_lanes
    .flatMap((lane) => lane.checkpoints)
    .find((checkpoint) => checkpoint.id === selectedId)

  return (
    <main className={`mission-shell phase-${control.scenario_phase.toLowerCase()}`}>
      <header className="utility-rail">
        <div className="continuum-wordmark"><span>C</span><strong>CONTINUUM</strong></div>
        <nav aria-label="Mission views">
          <button className={view === 'route' ? 'is-active' : ''} onClick={() => setView('route')}>Mission route</button>
          <button className={view === 'graph' ? 'is-active' : ''} onClick={() => setView('graph')}>Decision graph</button>
          <button className={view === 'missions' ? 'is-active' : ''} onClick={() => void openHistory()}>Mission history</button>
        </nav>
        <div className="mode-disclosure">
          <i />
          {control.execution_mode === 'GOOGLE_ADK_GEMINI'
            ? 'GOOGLE ADK · GEMINI'
            : 'LOCAL DETERMINISTIC'}
        </div>
        <button className="reset-button" onClick={() => void createScenario()} disabled={busy}><RotateCcw /> Reset</button>
      </header>

      <section className="mission-heading">
        <div>
          <p className="eyebrow">VENDOR ONBOARDING / {control.subject.id}</p>
          <h1>{control.subject.name}</h1>
          <div className="mission-state"><span>{phaseLabel}</span><p>{phaseDescription}</p></div>
        </div>
        <dl className="mission-facts">
          <div><dt>MISSION ID</dt><dd>{control.mission.mission_id.slice(0, 22)}</dd></div>
          <div><dt>POLICY</dt><dd>{control.current_policy}</dd></div>
          <div><dt>VENDOR</dt><dd className={`vendor-${control.vendor_status.toLowerCase()}`}>{control.vendor_status}</dd></div>
        </dl>
        <button className="primary-command" onClick={() => void runAction()} disabled={busy}>
          <span>{busy ? actionCopy[control.next_action].busy : actionCopy[control.next_action].label}</span>
          <ArrowRight aria-hidden="true" />
        </button>
      </section>

      {error ? <div className="error-banner" role="alert"><AlertTriangle />{error}<button onClick={() => setError(null)}>Dismiss</button></div> : null}
      <div className="announcement" aria-live="polite">{phaseLabel}: {phaseDescription}</div>

      {view === 'missions' ? (
        <MissionHistory
          activeMissionId={control.mission.mission_id}
          busy={historyBusy}
          missions={missions}
          onOpen={openMission}
        />
      ) : view === 'route' ? (
        <div className="route-workspace">
          <section className="route-panel" aria-label="Semantic mission route">
            <div className="route-caption"><span>SEMANTIC ROUTE</span><small>Current authorization path · click any checkpoint for provenance</small></div>
            {control.agent_lanes.map((lane) => (
              <div className="agent-lane" key={lane.agent_id}>
                <div className="lane-label">
                  {lane.agent_id === 'security-agent' ? <ShieldCheck /> : lane.agent_id === 'procurement-agent' ? <GitBranch /> : <Check />}
                  <div><strong>{lane.label}</strong><code>{lane.agent_id}</code></div>
                  <span>{lane.status}</span>
                </div>
                <div className="lane-track">
                  {lane.checkpoints.map((checkpoint, index) => (
                    <div className="checkpoint-wrap" key={checkpoint.id}>
                      {index > 0 ? <span className={`track-segment segment-${checkpoint.status.toLowerCase()}`} /> : null}
                      <Checkpoint checkpoint={checkpoint} selected={selectedId === checkpoint.id} onSelect={setSelectedId} />
                    </div>
                  ))}
                </div>
              </div>
            ))}
            <RouteLegend />
          </section>
          <Inspector control={control} selected={selected} />
        </div>
      ) : (
        <section className="graph-workspace">
          <DecisionGraph graph={control.graph} onSelect={setSelectedId} />
        </section>
      )}

      {view !== 'missions' ? <MissionTimeline control={control} /> : null}
    </main>
  )
}

function MissionHistory({
  activeMissionId,
  busy,
  missions,
  onOpen,
}: {
  activeMissionId: string
  busy: boolean
  missions: MissionSummary[]
  onOpen(missionId: string): void
}) {
  return (
    <section className="mission-history" aria-label="Recent missions" aria-busy={busy}>
      <header>
        <div>
          <p className="eyebrow">DURABLE RUNTIME / RECOVERY INDEX</p>
          <h2>Recent missions</h2>
        </div>
        <p>Open any preserved Mission namespace and continue from its exact semantic state.</p>
      </header>
      <div className="mission-history-table" role="table" aria-label="Mission history">
        <div className="mission-history-row mission-history-columns" role="row">
          <span>MISSION</span><span>STATUS</span><span>UPDATED</span><span>COMMITMENTS</span><span />
        </div>
        {missions.map((mission) => {
          const isActive = mission.mission_id === activeMissionId
          return (
            <div className={`mission-history-row ${isActive ? 'is-current' : ''}`} role="row" key={mission.mission_id}>
              <div><code>{mission.mission_id}</code><small>{mission.mission_type} · {mission.subject_id}</small></div>
              <span className={`mission-status status-${mission.status.toLowerCase()}`}>{mission.status}</span>
              <time dateTime={mission.updated_at}>{new Date(mission.updated_at).toLocaleString('en-GB')}</time>
              <span>{mission.counts.open_commitments} open</span>
              <button type="button" onClick={() => onOpen(mission.mission_id)} aria-label={`Open mission ${mission.mission_id}`}>
                {isActive ? 'Current' : 'Open mission'} <ArrowRight aria-hidden="true" />
              </button>
            </div>
          )
        })}
        {busy ? <p className="history-empty">Loading durable missions…</p> : null}
        {!busy && missions.length === 0 ? <p className="history-empty">No durable missions found.</p> : null}
      </div>
    </section>
  )
}

function Checkpoint({ checkpoint, selected, onSelect }: { checkpoint: RouteCheckpoint; selected: boolean; onSelect(id: string): void }) {
  const status = checkpoint.preserved ? 'PRESERVED' : checkpoint.status
  return (
    <button
      type="button"
      className={`route-checkpoint checkpoint-${checkpoint.kind} status-${checkpoint.status.toLowerCase()} ${selected ? 'is-selected' : ''}`}
      onClick={() => onSelect(checkpoint.id)}
      aria-label={`${checkpoint.label}: ${status}`}
      data-testid={`route-${checkpoint.id}`}
    >
      <code>{checkpoint.id.length > 18 ? checkpoint.kind.toUpperCase() : checkpoint.id}</code>
      <strong>{checkpoint.label}</strong>
      <span>{status}</span>
    </button>
  )
}

function RouteLegend() {
  return <div className="route-legend" aria-label="Route legend"><span><i className="valid" />Valid</span><span><i className="stale" />Stale</span><span><i className="waiting" />Waiting</span><span><i className="preserved" />Preserved</span></div>
}

function Inspector({ control, selected }: { control: MissionControlReadModel; selected?: RouteCheckpoint }) {
  const penWait = control.commitments.find((item) => item.status === 'OPEN' && item.event_type === 'vendor.document.uploaded')
  const content = useMemo(() => {
    if (selected) return { title: selected.label, body: `Checkpoint ${selected.id} is ${selected.preserved ? 'VALID and preserved' : selected.status}.`, reason: selected.preserved ? 'No dependency path reaches this decision from Policy v12.' : 'State is derived from the canonical dependency graph.' }
    if (control.scenario_phase === 'POLICY_DRIFT') return { title: 'Why this stopped', body: 'Policy v13 requires penetration-test evidence for AI vendors handling customer PII.', reason: 'D42 became STALE. D50 inherited that invalidation. D43 has no policy dependency and remains VALID.' }
    if (control.scenario_phase === 'MISSING_EVIDENCE') return { title: 'Current commitment', body: 'Security is waiting for PEN_TEST evidence.', reason: 'The exact external event below will wake only the linked Security work.' }
    if (control.scenario_phase === 'COMPLETED') return { title: 'Fresh authorization', body: 'D57 superseded D42 and D58 superseded D50.', reason: 'ActivateVendor was committed once under D58; Acme Analytics is ACTIVE.' }
    return { title: 'Semantic resume', body: 'Continuum remembers why each decision was valid.', reason: 'If a governing artifact changes, only causally affected work is invalidated and resumed.' }
  }, [control.scenario_phase, selected])
  return (
    <aside className="route-inspector">
      <p className="eyebrow">INSPECTOR / CAUSAL EXPLANATION</p>
      <h2>{content.title}</h2>
      <p>{content.body}</p>
      <div className="inspector-reason"><CircleStop /><span>{content.reason}</span></div>
      {penWait ? <div className="commitment-readout"><Clock3 /><div><small>AWAITED EVENT</small><code>{penWait.event_type}</code><small>PREDICATE</small><code>vendor_id=ACME · document_type=PEN_TEST</code></div></div> : null}
      <dl>
        <div><dt>Policy</dt><dd>{control.current_policy}</dd></div>
        <div><dt>Mission</dt><dd>{control.mission.status}</dd></div>
        <div><dt>Open commitments</dt><dd>{control.commitments.filter((item) => item.status === 'OPEN').length}</dd></div>
        <div><dt>Side effects</dt><dd>{control.side_effects.length}</dd></div>
      </dl>
    </aside>
  )
}

function MissionTimeline({ control }: { control: MissionControlReadModel }) {
  return (
    <section className="timeline-panel">
      <header><div><strong>EVENT HISTORY</strong><span><i /> LIVE</span></div><small>Immutable runtime audit · newest first</small></header>
      <div className="timeline-table" role="table" aria-label="Mission event history">
        {control.timeline.slice(0, 9).map((event) => (
          <div className="timeline-row" role="row" key={event.audit_event_id}>
            <time>{new Date(event.occurred_at).toLocaleTimeString('en-GB', { hour12: false })}</time>
            <code>{event.event_type}</code>
            <span>{timelineDetail(event.event_type, event.payload)}</span>
            <small>#{String(event.event_sequence).padStart(3, '0')}</small>
          </div>
        ))}
      </div>
    </section>
  )
}

function timelineDetail(type: string, payload: Record<string, unknown>): string {
  if (type === 'decision.stale') return `${payload.decision_id} invalidated by ${payload.cause_artifact_id}`
  if (type === 'commitment.created') return 'Durable PEN_TEST wait registered'
  if (type === 'decision.superseded') return `${payload.old_decision_id} → ${payload.new_decision_id}`
  if (type === 'side_effect.committed') return 'Vendor activation committed exactly once'
  return String(payload.status ?? payload.outcome ?? payload.vendor_status ?? 'Recorded by deterministic runtime')
}
