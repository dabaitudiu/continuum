import { AlertTriangle, RotateCcw, Sparkles } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

import { DecisionGraph } from './components/DecisionGraph'
import { EventLog } from './components/EventLog'
import { ProvenancePanel } from './components/ProvenancePanel'
import type { ContinuumApi, GraphReadModel } from './types'

function uniqueId(prefix: string): string {
  const suffix = globalThis.crypto?.randomUUID?.() ?? `${Date.now()}`
  return `${prefix}-${suffix}`
}

export function App({ api }: { api: ContinuumApi }) {
  const [graph, setGraph] = useState<GraphReadModel | null>(null)
  const [missionId, setMissionId] = useState<string | null>(null)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [busyAction, setBusyAction] = useState<'reset' | 'upgrade' | 'revalidate' | null>('reset')
  const [error, setError] = useState<string | null>(null)

  const reset = useCallback(async () => {
    setBusyAction('reset')
    setError(null)
    try {
      const created = await api.reset()
      const initial = await api.getGraph(created.mission_id)
      setMissionId(created.mission_id)
      setGraph(initial)
      setSelectedId(null)
    } catch (caught) {
      setError(`Reset failed: ${caught instanceof Error ? caught.message : 'unknown error'}`)
    } finally {
      setBusyAction(null)
    }
  }, [api])

  useEffect(() => {
    void reset()
  }, [reset])

  const upgrade = async () => {
    if (!missionId) return
    setBusyAction('upgrade')
    setError(null)
    try {
      const drifted = await api.upgradePolicy(missionId, uniqueId('event'))
      setGraph(drifted)
      setSelectedId(drifted.plan.runnable_decision_ids[0] ?? null)
    } catch (caught) {
      setError(`Policy upgrade failed: ${caught instanceof Error ? caught.message : 'unknown error'}`)
    } finally {
      setBusyAction(null)
    }
  }

  const revalidate = async () => {
    if (!missionId) return
    setBusyAction('revalidate')
    setError(null)
    try {
      setGraph(await api.revalidate(missionId, uniqueId('request')))
    } catch (caught) {
      setError(`Revalidation failed: ${caught instanceof Error ? caught.message : 'unknown error'}`)
    } finally {
      setBusyAction(null)
    }
  }

  if (!graph) {
    return (
      <main className="loading-state">
        <span className="brand-mark">C</span>
        <p>{error ?? 'Loading runtime graph…'}</p>
        {error ? <button onClick={() => void reset()}>Retry reset</button> : null}
      </main>
    )
  }

  const initial = graph.phase === 'INITIAL'
  return (
    <main className={`app-shell phase-${graph.phase.toLowerCase()}`}>
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark">C</span>
          <div>
            <strong>CONTINUUM</strong>
            <small>Decision validity runtime</small>
          </div>
        </div>
        <div className="version-shift" aria-label="Policy version transition">
          <code>POLICY v12</code>
          <span>→</span>
          <code>v13</code>
        </div>
        <div className="topbar__actions">
          <button type="button" className="button-secondary" onClick={() => void reset()} disabled={busyAction !== null}>
            <RotateCcw aria-hidden="true" /> Reset
          </button>
          <button type="button" className="button-primary" onClick={() => void upgrade()} disabled={!initial || busyAction !== null}>
            <Sparkles aria-hidden="true" />
            {busyAction === 'upgrade' ? 'Applying v13…' : 'Inject policy v13'}
          </button>
        </div>
      </header>

      <section className="impact-band" aria-live="polite">
        <div>
          <span className="phase-index">Phase / {graph.phase.toLowerCase()}</span>
          <strong>{initial ? 'All decisions are valid.' : 'External policy changed.'}</strong>
        </div>
        <div className="summary-counts">
          <span className="count-stale">{graph.summary.stale} stale</span>
          <span className="count-preserved">{graph.summary.preserved} preserved</span>
          <span className="count-blocked">{graph.summary.blocked} blocked</span>
        </div>
      </section>

      {error ? (
        <div className="error-banner" role="alert">
          <AlertTriangle aria-hidden="true" />
          <span>{error}</span>
          <button type="button" onClick={() => setError(null)}>Dismiss</button>
        </div>
      ) : null}

      <div className="workspace-grid">
        <DecisionGraph graph={graph} onSelect={setSelectedId} />
        <ProvenancePanel
          graph={graph}
          selectedId={selectedId}
          onRun={() => void revalidate()}
          busy={busyAction !== null}
        />
      </div>
      <EventLog graph={graph} />
    </main>
  )
}
