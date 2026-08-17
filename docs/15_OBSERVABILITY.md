# 15 — Observability

## Two layers

### Platform telemetry

OpenTelemetry traces/logs/metrics for model calls, agent invocations, tool calls, latency, tokens, errors.

### Domain audit ledger

Business-semantic events:

- decision.created
- decision.stale
- decision.superseded
- commitment.created
- commitment.satisfied
- side_effect.intended
- side_effect.committed
- mission.waiting
- mission.resumed
- policy.version.changed

Do not confuse the two. A Cloud trace explains execution mechanics; the domain ledger explains why a business state changed.

## Trace structure

Suggested span hierarchy:

```text
mission.resume
  revalidate_world_state
  compute_invalidation
  dispatch_security_agent
    gemini.reason
    tool.get_policy
    tool.get_document
  persist_decision
  dispatch_procurement_agent
```

## Correlation

Persist `trace_id` on domain events and agent work items where practical so UI can connect semantic history to Cloud trace evidence.

## Metrics

MVP metrics:

- active missions;
- waiting missions;
- stale decisions detected;
- revalidation work items;
- avoided rerun count;
- duplicate side effects prevented;
- agent/model call latency;
- token usage.

## Demo observability shot

The submission video should briefly show Google Cloud trace/log evidence proving the backend is genuinely deployed and executing.
