# 01 — Product Requirements

## Target user

Platform/Security/Operations teams responsible for enterprise agent fleets and workflows that remain active over long periods.

## User jobs

1. Start a long-lived mission.
2. See which agents and commitments are active.
3. Understand why a past decision was made.
4. Detect when a world-state change makes a decision stale.
5. Revalidate only affected work.
6. Recover after worker/process failure without repeating committed side effects.
7. Audit every decision, tool invocation, policy version, event, and side effect.

## Functional requirements

### FR-1 Mission lifecycle

A mission supports: `CREATED`, `RUNNING`, `WAITING`, `REVALIDATING`, `BLOCKED`, `COMPLETED`, `FAILED`, `CANCELLED`.

### FR-2 Decision provenance

Every material decision must record:

- structured outcome;
- decision type;
- producing agent;
- reasoning summary;
- evidence references;
- dependency references;
- policy/identity context;
- timestamp;
- status.

### FR-3 Dependency graph

The system stores machine-traversable dependency edges between evidence/artifacts/policies and decisions, plus decision-to-decision/action edges.

### FR-4 Drift invalidation

When a dependency changes, affected decisions become `STALE`. Downstream nodes that rely on those decisions become stale or blocked according to deterministic propagation rules.

### FR-5 Selective revalidation

The system creates a revalidation plan containing only stale nodes and their required ancestors/descendants, while preserving unaffected valid work.

### FR-6 Commitment memory

Agents can create durable commitments such as "resume the security review when penetration-test.pdf arrives".

### FR-7 Event wakeup

An external event can match an open commitment and wake the correct mission/agent.

### FR-8 Side-effect safety

Side-effecting tool calls use an idempotency key and ledger states so crash/retry does not repeat a committed action.

### FR-9 Crash recovery

A worker can disappear after durable state has been written; a new worker can recover the mission without losing its semantic state.

### FR-10 Mission Control UI

The UI exposes mission status, timeline, fleet status, commitments, decision graph, drift events, and audit trace.

## Non-functional requirements

- Deterministic core transitions.
- Every important UI status must be backed by persisted runtime state.
- Demo reset must be one click.
- Seed demo must complete in less than four minutes.
- No real customer PII.
- All external systems in the demo are simulated or controlled.
- Failure states must be visible and explainable.

## Contest-specific requirements

- Gemini 3.5+ or newer used materially in agent reasoning.
- At least one Google agent framework; use ADK.
- Google Cloud infrastructure and visible cloud deployment.
- Hosted experience strongly preferred.
- Repo must be reproducible from README instructions.
