import { Radio, Send } from 'lucide-react'

import type { GraphReadModel } from '../types'

export function EventLog({ graph }: { graph: GraphReadModel }) {
  return (
    <footer className="event-log" aria-label="Runtime event log">
      <span className="event-log__title">Event log</span>
      {graph.events.length === 0 && graph.dispatches.length === 0 ? (
        <span className="event-log__empty">Awaiting external change</span>
      ) : null}
      {graph.events.map((event) => (
        <span className="event-record" key={event.event_id}>
          <Radio aria-hidden="true" />
          <code>{event.event_type}</code>
          <span>{event.payload.old_version} → {event.payload.new_version}</span>
        </span>
      ))}
      {graph.dispatches.map((dispatch) => (
        <span className="event-record" key={dispatch.dispatch_id}>
          <Send aria-hidden="true" />
          <code>{dispatch.work_type}</code>
          <span>{dispatch.decision_id}</span>
        </span>
      ))}
    </footer>
  )
}
