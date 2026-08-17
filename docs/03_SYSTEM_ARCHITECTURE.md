# 03 — System Architecture

## Architectural principle

Use Google-managed Agent Platform capabilities for generic fleet/runtime infrastructure. Build only the missing semantic layer that expresses Continuum's thesis.

## Logical topology

```text
Browser / Mission Control UI
        |
        v
Continuum Control Plane API (Cloud Run)
        |
        +--> Firestore: mission/decision/evidence/commitment/ledger state
        +--> Pub/Sub: world events and wakeups
        +--> Agent Runtime: deployed ADK agents
                    |
                    +--> Vendor Agent
                    +--> Security Agent
                    +--> Procurement Agent
                    |
                    +--> Gemini 3.5+ reasoning
                    +--> Agent Platform Sessions
                    +--> Memory Bank (semantic memory only)
                    +--> governed tools / Agent Gateway (P1)

OpenTelemetry --> Cloud Trace / Logging / Monitoring
```

## Why two runtime layers

### Google Agent Runtime

Owns managed execution/deployment/scaling of individual agent applications and provides platform integration such as Sessions and Memory Bank.

### Continuum semantic runtime

Owns domain semantics that Google Agent Runtime should not be expected to infer:

- mission status;
- decision provenance;
- dependency graph;
- invalidation;
- commitments;
- side-effect ledger;
- selective revalidation.

The Continuum runtime is primarily a durable state machine + graph semantics service, not a competing generic agent host.

## Control plane

Responsibilities:

- create/reset demo mission;
- dispatch agent work;
- ingest agent results;
- validate structured outputs;
- persist state transitions;
- publish events;
- compute invalidation;
- generate revalidation plan;
- expose REST/SSE/WebSocket read models to UI.

## Agent plane

Each ADK agent has narrow tool permissions and a structured response contract. Agents never mutate canonical mission state directly; they propose results through runtime APIs.

## Event plane

Pub/Sub carries events such as:

- `policy.version.changed`
- `vendor.document.uploaded`
- `human.approval.received`
- `agent.work.requested`
- `agent.work.completed`

The runtime remains the authority for state transitions.

## Deployment

Recommended:

- UI: Cloud Run or Firebase Hosting + backend API.
- Control Plane: Cloud Run.
- Agents: Gemini Enterprise Agent Runtime.
- Firestore: Native mode.
- Pub/Sub: single project/region aligned with demo deployment where possible.
- Optional Gateway/Registry resources in the same supported project/region.

## Preview-feature tolerance

P0 must still work if Agent Gateway or specific governance features are unavailable to the project. The submission should demonstrate them only if provisioned reliably before video recording.
