# 18 — Build Plan

The coding agent should implement these phases in order. Each phase has a stop condition.

## Phase 1 — Repository scaffold and local health

Build:

- frontend shell;
- FastAPI control-plane shell;
- test runner;
- environment configuration;
- local dev commands.

Acceptance:

- one command starts backend;
- one command starts UI;
- backend health endpoint works;
- tests run in CI/local.

Do not add Gemini yet.

## Phase 2 — Domain model and Firestore repository abstraction

Build canonical entities and repository interfaces for Mission, Decision, Evidence, DependencyEdge, Commitment, SideEffect, WorldArtifact, DomainEvent.

Acceptance:

- CRUD/persistence tests;
- illegal enum/state data rejected;
- events can be ordered and queried by mission.

## Phase 3 — Deterministic invalidation kernel

Implement dependency graph traversal and stale propagation.

Acceptance:

- seed graph test exactly matches `17_36H_FALSIFICATION_GATE.md`;
- no hardcoded node IDs.

**STOP and evaluate the 36-hour gate here.**

## Phase 4 — Decision Graph UI

Implement graph API/read model and visual graph.

Acceptance:

- v12->v13 visibly marks only affected nodes;
- node side panel explains source dependency/version;
- unaffected node visibly remains VALID.

## Phase 5 — Mission state machine + commitments

Implement mission/work-item lifecycle, WAIT/WAKE, commitment matching.

Acceptance:

- security revalidation can wait on a pen-test commitment;
- wrong event ignored;
- right event resumes exactly once.

## Phase 6 — Enterprise Simulator

Implement vendor DB, policy store, document store, procurement approval, email/action simulator.

Acceptance:

- reset/start/upgrade-policy/upload-doc actions work without editing DB manually;
- simulator cannot directly mutate decision status.

## Phase 7 — Side-effect ledger

Implement intent/execute/commit protocol for vendor email and activation.

Acceptance:

- duplicate/retry tests pass;
- stale upstream authorization blocks activation.

## Phase 8 — Google ADK + Gemini agents

Implement Vendor, Security, Procurement agents with structured output contracts.

Acceptance:

- security decisions cite valid evidence/dependency IDs;
- v13 missing pen test creates a missing-evidence result/commitment proposal;
- invalid references are rejected by control plane.

## Phase 9 — Async cloud execution

Add Pub/Sub event path and deploy agents/control plane to Google Cloud / Agent Runtime as designed.

Acceptance:

- cloud-deployed demo completes WAIT -> external event -> WAKE;
- visible Google Cloud execution evidence exists.

## Phase 10 — Mission Control UI

Implement timeline, agent fleet status, commitments, blockers, audit.

Acceptance:

- complete demo can be operated from browser;
- no terminal needed for main story.

## Phase 11 — Governance and observability

Add OTel. Then integrate Registry/Gateway/Model Armor/Identity only if available and stable enough.

Acceptance:

- trace/logs visible in Google Cloud;
- domain event links/carries trace IDs where practical;
- no P1 governance feature can break the core demo.

## Phase 12 — Demo hardening and submission

Build resettable demo mode, seeded scenario, fault injection if stable, architecture diagram, README, video script.

Acceptance:

- three clean end-to-end runs;
- four-minute recording script fits;
- public/private repo permissions and spin-up instructions verified.
