# 13 — Data and Memory Model

## Canonical stores

### Firestore — system of record

Suggested collections:

- `missions`
- `work_items`
- `evidence`
- `decisions`
- `dependency_edges`
- `commitments`
- `side_effects`
- `world_artifacts`
- `domain_events`

For hackathon scale, optimize for clarity and queryability rather than extreme normalization.

## Read models

Mission Control may denormalize counts/status summaries into mission documents, but canonical entities remain individually queryable.

## Event history

`domain_events` is append-oriented. UI timeline reads from it.

## Agent Platform Sessions

Use session history as conversational/invocation context for an agent execution where useful. It is not the canonical mission state.

## Memory Bank

Use for long-term semantic memories that improve agent behavior across sessions, e.g. stable vendor facts or operator preferences.

Do not rely on Memory Bank as the only storage for:

- a security decision;
- a dependency edge;
- an open commitment;
- a committed side effect;
- authorization state.

These require explicit deterministic lifecycle semantics.

## Hashing/versioning

Every policy/document evidence object used as a decision dependency should have a stable logical key plus immutable version/hash.

## Demo reset

Reset creates a new mission namespace rather than destructively deleting old audit data during active development. A separate cleanup utility may remove stale demo missions.
