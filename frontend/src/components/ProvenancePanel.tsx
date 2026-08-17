import { ArrowRight, Play, ShieldCheck } from 'lucide-react'

import type { GraphReadModel } from '../types'

function listOrNone(ids: string[]): string {
  return ids.length ? ids.join(', ') : 'None'
}

export function ProvenancePanel({
  graph,
  selectedId,
  onRun,
  busy,
}: {
  graph: GraphReadModel
  selectedId: string | null
  onRun(): void
  busy: boolean
}) {
  const focusId = selectedId ?? graph.plan.runnable_decision_ids[0] ?? graph.plan.stale_decision_ids[0]
  const causeId = focusId ? graph.causes[focusId] : undefined
  const edge = graph.edges.find(
    (candidate) => candidate.from_node_id === causeId && candidate.to_node_id === focusId,
  )

  return (
    <aside className="evidence-rail" aria-label="Provenance and revalidation plan">
      <section>
        <p className="eyebrow">Why this changed</p>
        {focusId && causeId ? (
          <div className="cause-statement">
            <div className="cause-path">
              <code>{causeId}</code>
              <ArrowRight aria-hidden="true" />
              <code>{focusId}</code>
            </div>
            <p>
              <strong>{focusId}</strong> depends on <strong>{causeId}</strong>
              {edge ? <> through <code>{edge.relation_type}</code></> : null}.
            </p>
          </div>
        ) : (
          <p className="quiet-copy">No invalidation cause is active.</p>
        )}
      </section>

      <section className="plan-section">
        <p className="eyebrow">Revalidation plan</p>
        {graph.plan.runnable_decision_ids.length > 0 ? (
          <button
            type="button"
            className="run-branch"
            aria-label="Run affected branch"
            onClick={onRun}
            disabled={busy}
          >
            <span>
              <Play aria-hidden="true" />
              Run now: {listOrNone(graph.plan.runnable_decision_ids)}
            </span>
            <small>Only the current stale root</small>
          </button>
        ) : (
          <div className="plan-row plan-row--quiet">
            <span>Run now</span>
            <strong>{graph.phase === 'REVALIDATING' ? 'Dispatch active' : 'None'}</strong>
          </div>
        )}
        <div className="plan-row">
          <span>Waiting: {listOrNone(graph.plan.waiting_decision_ids)}</span>
          <small>Unresolved prerequisite</small>
        </div>
        <div className="plan-row plan-row--preserved">
          <span>
            <ShieldCheck aria-hidden="true" />
            Preserved: {listOrNone(graph.plan.retained_decision_ids)}
          </span>
          <small>No rerun</small>
        </div>
      </section>
    </aside>
  )
}
