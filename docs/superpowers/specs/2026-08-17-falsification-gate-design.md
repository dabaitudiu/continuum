# Continuum 36-Hour Falsification Gate Design

**Status:** Awaiting written-spec review

**Date:** 2026-08-17
**Scope:** Falsification prototype only; this is not authorization for the full product build.

## 1. Decision

Build a thin, reusable vertical slice that proves one claim:

> After a versioned external dependency changes, Continuum deterministically identifies the affected decision subgraph, preserves unrelated valid work, blocks downstream action, and dispatches only the currently runnable stale branch.

The gate uses an in-memory repository, a synchronous domain event, a FastAPI control plane, and one React graph screen. It deliberately excludes Gemini, ADK, Firestore, Pub/Sub, commitments, side-effect execution, cloud deployment, and the full Mission Control UI.

Passing this gate authorizes planning the full product. It does not prove the later agent, cloud, commitment, or side-effect hypotheses.

## 2. Spec Corrections Required for the Gate

The current design pack contains four ambiguities that this gate resolves explicitly:

1. `18_BUILD_PLAN.md` stops after Phase 3, but the visual gate requires the Phase 4 graph UI. The gate is therefore a separate **Phase G** thin slice that takes only the necessary pieces from Phases 1–4.
2. `ActivateVendor` must become `BLOCKED`, but `04_DOMAIN_MODEL.md` defines no Action entity. Phase G introduces an `ActionNode` in the graph-domain model. This does not yet create the full side-effect ledger.
3. The older long-form concept document uses D44 for the downstream decision; the current `AGENTS.md` and numbered specifications use D50. Phase G treats D50 as canonical.
4. “Selective re-execution” means actual dispatch evidence, not only a computed list. Phase G dispatches the currently runnable stale root D42 to a deterministic stub revalidator, keeps D50 queued behind D42, and proves D43 is never dispatched.

After the gate decision, the numbered documentation should be amended to reflect the accepted semantics. Do not edit those canonical documents before the gate design is approved.

## 3. Alternatives Considered

### A. Recommended: reusable thin vertical slice

- Python domain kernel + FastAPI.
- In-memory repository behind a small repository protocol.
- Vite + React + React Flow for a data-driven graph.
- Deterministic stub revalidator for dispatch proof.

Why: it is small enough for the time box while preserving the final system’s Python/FastAPI boundary and producing a convincing, non-static UI.

### B. Faster throwaway: Python script + generated static SVG

Why rejected: it minimizes setup but makes the graph look scripted, weakens interaction/provenance inspection, and creates little reusable code for the eventual control plane.

### C. Production-first: Firestore + Pub/Sub + Cloud Run immediately

Why rejected: infrastructure does not answer the falsification question and could consume the entire gate without improving evidence for the thesis.

## 4. Domain Model for Phase G

Phase G implements only these entities:

### WorldArtifact

- `artifact_id: str`
- `artifact_type: str`
- `logical_key: str`
- `version: str`
- `supersedes_artifact_id: str | None`
- `status: CURRENT | SUPERSEDED`

### EvidenceNode

- `evidence_id: str`
- `kind: str`
- `revision: str`
- `status: VALID`

Evidence is factual input. It never changes a decision status directly.

### DecisionNode

- `decision_id: str`
- `decision_type: str`
- `outcome: str`
- `status: VALID | STALE | REVALIDATING`
- `supersedes_decision_id: str | None`
- `execution_count: int`

### ActionNode

- `action_id: str`
- `action_type: str`
- `status: READY | BLOCKED`

### DependencyEdge

- `edge_id: str`
- `from_node_id: str`
- `to_node_id: str`
- `relation_type: SUPPORTED_BY | GOVERNED_BY | DERIVED_FROM | REQUIRES | AUTHORIZES`
- `critical: bool`

Edges always point from dependency/source to dependent/consumer, regardless of the grammatical direction of the relation name.

### DomainEvent

- `event_id: str`
- `event_type: str`
- `payload: dict[str, str]`

For `policy.version.changed`, payload contains:

- `logical_key`
- `old_artifact_id`
- `new_artifact_id`
- `old_version`
- `new_version`

### RevalidationPlan

- `stale_decision_ids: list[str]`
- `runnable_decision_ids: list[str]`
- `waiting_decision_ids: list[str]`
- `blocked_action_ids: list[str]`
- `retained_decision_ids: list[str]`
- `cause_by_node_id: dict[str, str]`

## 5. Canonical Seed Graph

```text
Policy v12 ──GOVERNED_BY──▶ D42 SecurityApproved ──REQUIRES──▶ D50 ProcurementApproved ──AUTHORIZES──▶ ActivateVendor
SOC2 A31 ───SUPPORTED_BY──▶ D42
Financial F7 ─SUPPORTED_BY▶ D43 FinancialApproved ──REQUIRES──▶ D50
```

All five nodes begin valid/current and all three decisions have `execution_count = 1`.

The upgrade command creates Policy v13, marks v12 `SUPERSEDED`, and emits exactly one `policy.version.changed` event. The simulator/API may create that world input; it must not directly mutate D42, D43, D50, or ActivateVendor.

## 6. Deterministic Invalidation Rules

### Direct invalidation

For the superseded artifact, find outgoing critical edges whose relation is `GOVERNED_BY`, `SUPPORTED_BY`, `DERIVED_FROM`, or `REQUIRES`. A dependent Decision becomes `STALE`.

For the canonical fixture, Policy v12 directly invalidates D42 through its critical `GOVERNED_BY` edge.

### Downstream propagation

Starting from each newly stale Decision, traverse outgoing critical edges:

- `REQUIRES` or `DERIVED_FROM` to a Decision: mark it `STALE`.
- `AUTHORIZES` to an Action: mark it `BLOCKED`.
- `SUPPORTED_BY` and `GOVERNED_BY` do not propagate from a stale Decision.
- Non-critical edges never propagate invalidation.

Traversal uses a visited set, so cycles terminate. Reprocessing the same event is idempotent and creates no additional transitions or dispatches.

### Required post-event state

```text
D42              STALE
D50              STALE
ActivateVendor   BLOCKED
D43              VALID
```

No rule may branch on these identifiers.

## 7. Selective Revalidation and Dispatch

The planner derives, rather than hardcodes:

```text
stale_decision_ids    = [D42, D50]
runnable_decision_ids = [D42]
waiting_decision_ids  = [D50]
blocked_action_ids    = [ActivateVendor]
retained_decision_ids = [D43]
```

A stale Decision is runnable when it has no incoming critical `REQUIRES` or `DERIVED_FROM` edge from another stale Decision.

Running the plan invokes a `DecisionRevalidator` protocol for D42 only. The Phase G deterministic stub records the invocation and changes D42 to `REVALIDATING`; it does not invent a new approval or bypass the future v13 evidence requirement. D50 remains stale and waiting; D43 remains valid with `execution_count = 1`.

This is the smallest honest proof of branch re-execution. Completing D42 requires the later Gemini/evidence/commitment phase and is outside this gate.

## 8. API Surface

Only four endpoints are required:

### `POST /api/demo/reset`

Creates a fresh in-memory canonical fixture and returns its `mission_id`.

### `POST /api/demo/policy/upgrade`

Input: `mission_id`, `event_id`. Creates v13 and sends the event through the runtime. Duplicate `event_id` returns the existing result.

### `GET /api/missions/{mission_id}/graph`

Returns graph nodes, edges, status summary, transition causes, and the current revalidation plan.

### `POST /api/missions/{mission_id}/revalidate`

Dispatches only `runnable_decision_ids`, returns dispatch records, and is idempotent per request id.

No SSE/WebSocket is needed. The UI refreshes from the response to the command it initiated.

## 9. UI Design Read

### Subject, audience, single job

- Subject: policy drift changing the validity of previous enterprise-agent decisions.
- Audience: a hackathon judge unfamiliar with Continuum.
- Single job: understand within 15 seconds that one external change invalidated only part of the graph and preserved unrelated work.
- Copy register: concise professional operations language; no conversational assistant voice and no marketing slogans.

### Direction

- Main style: **Canvas Builder 70%** — graph topology is the product.
- Supporting style: **Scientific Data UI 30%** — causal evidence, version labels, and status counts must be precise and reproducible.
- Signature: a single causal “impact sweep” from Policy v12 through D42 and D50 to ActivateVendor, while the D43 branch remains visually still and explicitly labeled `PRESERVED`.
- Density: medium professional-tool density.
- Platform: desktop web first, responsive down to tablet; mobile stacks the evidence panel below the graph.

### Excluded candidates

1. Aviation Glass Cockpit / SOC Command: the previous project already used this main style, and repeating it would turn Continuum into a generic monitoring console.
2. Neo-Swiss: it is a known default attractor and its oversized typography would compete with the causal graph.
3. Terminal Hacker: it violates the light-interface rule and would make the product look like backend logs.
4. Bento dashboard: independent cards would fragment the dependency chain and weaken the thesis.

### Visual constants

- Background: `#F4F5F1` mineral white.
- Shared graph surface: `#FBFCF8`.
- Ink: `#19211D`.
- Muted ink/edges: `#6B746E` / `#CBD1CB`.
- Valid: `#287A55`, plus check icon and solid border.
- Stale: `#B33A32`, plus diagonal strike motif and `STALE` label.
- Blocked: `#B56A14`, plus octagonal stop shape and `BLOCKED` label.
- Policy change: `#315C9B`, used only for the changed artifact and impact sweep.
- Radius: 4px for nodes and panels; 2px for compact controls; no pills except tiny status counters when space-constrained.
- Border: 1px; stale root uses 2px.
- Shadow: none.
- Spacing: 8px base, using 8/16/24/32/48.
- Type: `IBM Plex Sans` for UI and `IBM Plex Mono` for IDs, versions, and event records; no display font.
- Motion: one 700–900ms linear impact sweep; all other transitions 120–180ms. `prefers-reduced-motion` changes statuses instantly without losing sequence or meaning.

### Layout

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ CONTINUUM                 Policy v12 → v13           Reset  Inject policy v13│
├──────────────────────────────────────────────────────────────────────────────┤
│ External policy changed.  2 stale · 1 preserved · 1 blocked                │
├───────────────────────────────────────────────────────┬──────────────────────┤
│                                                       │ WHY THIS CHANGED     │
│  Policy v13                                          │ D42 was governed by  │
│      ↓ supersedes                                    │ Security Policy v12. │
│  [Policy v12] ───▶ [D42 STALE] ───▶ [D50 STALE] ───▶│ [Activate BLOCKED]   │
│  [SOC2 A31]  ─────▶      ▲                           │                      │
│                          │                           │ REVALIDATION PLAN    │
│  [Financial F7] ─▶ [D43 VALID · PRESERVED] ─────────▶│ Run now: D42         │
│                                                       │ Waiting: D50         │
│                                                       │ Preserved: D43       │
├───────────────────────────────────────────────────────┴──────────────────────┤
│ EVENT LOG: policy.version.changed → D42 stale → D50 stale → action blocked │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Interaction states

- Initial: v12 current; all decisions valid; action ready.
- Upgrading: trigger disabled and labeled `Applying v13…`.
- Drifted: affected subgraph stale/blocked; D43 preserved.
- Dispatch control: the `Run now: D42` row is a real keyboard-focusable button with accessible name `Run affected branch`; it calls `POST /revalidate`.
- Revalidating: D42 labeled `REVALIDATING`; D50 remains stale/waiting.
- Duplicate event: no visual replay; log says event already processed.
- Error: command area gives the exact failed action and a retry control; existing graph state remains visible.

### Reference extraction

- OpenLineage/Marquez: retain data-driven lineage, directional edges, and click-through metadata; do not copy its dark theme.
  - https://openlineage.io/docs/client/python/
- Temporal Flow: retain a consolidated zoomable execution map and at-a-glance state; do not reduce Continuum to workflow history.
  - https://temporal.io/code-exchange/temporal-flow
- Temporal workflow timeline: retain compact execution evidence in a quiet footer rather than making logs the primary product.
  - https://temporal.io/blog/modernizing-monoliths-with-temporal

## 10. Planned Repository Shape

```text
backend/
  pyproject.toml
  app/
    main.py
    domain/
      models.py
      invalidation.py
      revalidation.py
    repository/
      protocol.py
      memory.py
    demo/
      fixture.py
  tests/
    test_invalidation.py
    test_revalidation.py
    test_api.py
frontend/
  package.json
  src/
    App.tsx
    api.ts
    graph-model.ts
    components/
      DecisionGraph.tsx
      ProvenancePanel.tsx
      EventLog.tsx
    styles.css
docs/superpowers/specs/assets/
  continuum-gate-ui-benchmark-v2.png
```

Files are split by responsibility. Phase G does not create empty packages for later subsystems.

## 11. Required Automated Proof

1. Canonical v12→v13 fixture produces exactly D42 stale, D50 stale, ActivateVendor blocked, D43 valid.
2. The same engine passes a second fixture with different IDs and a different artifact type.
3. A non-critical edge does not propagate invalidation.
4. A non-validity-bearing edge does not propagate invalidation.
5. Cyclic edges terminate and transition each node at most once.
6. A duplicate `event_id` creates no duplicate transition or dispatch.
7. The planner selects D42 as runnable, D50 as waiting, and D43 as retained.
8. Revalidation dispatch increments D42 only; D43 execution count remains one.
9. The simulator endpoint never writes Decision or Action statuses directly.
10. API reset returns the initial graph; upgrade returns the required graph; revalidate returns only the allowed dispatch.

## 12. Visual Falsification Procedure

Use at least five people unfamiliar with the project. Show the initial state, trigger v13, then ask—without narration:

1. What external thing changed?
2. What work became invalid?
3. What work was preserved?
4. What will rerun next?

Pass when at least four of five answer all four correctly within 15 seconds. Record answer time and incorrect interpretations. Do not coach participants during the timed observation.

## 13. Time Box

- Hours 0–3: approve this spec, finalize benchmark, scaffold test/runtime/UI commands.
- Hours 3–11: domain models, in-memory repository, failing tests, invalidation kernel.
- Hours 11–17: revalidation planner, stub dispatch, idempotency, API.
- Hours 17–27: graph UI and provenance panel matching the approved benchmark.
- Hours 27–32: alternate fixture, cycle/idempotency coverage, browser integration checks.
- Hours 32–36: five-person visual test, defect fixes, gate report.

At hour 36, stop. Do not continue into Gemini, ADK, Firestore, Pub/Sub, or the full product before reporting the gate result.

## 14. Kill / Pivot Decision at Hour 36

Kill or pivot the current thesis if any of these remains true:

- stale/valid status requires an LLM judgment;
- propagation or UI topology depends on canonical demo IDs;
- the graph is effectively a static scripted DAG;
- restart-all is equally simple and equally convincing;
- fewer than four of five observers pass the 15-second test;
- selective dispatch cannot be shown honestly;
- remaining implementation complexity threatens the hackathon schedule.

Proceed only when the automated proof passes, the visual threshold passes, and the result can be summarized as:

> Policy v13 invalidated only the security-dependent branch; Continuum preserved the financial review and reran only the stale root.

## 15. UI Benchmark

Approved-for-review benchmark candidate:

- `docs/superpowers/specs/assets/continuum-gate-ui-benchmark-v2.png`
- Generated with the built-in image generation path using the `ui-mockup` use case.
- The first candidate is retained as `continuum-gate-ui-benchmark.png` for comparison; it is rejected because connector crossings made the Financial F7 → D43 dependency ambiguous and its log mixed the `STALE` and `REVALIDATING` states.

Benchmark review:

- Keep: single shared graph surface, strong affected-versus-preserved contrast, compact causal explanation, status redundancy beyond color, quiet audit footer.
- Implementation correction: use code-rendered labels and edges, so relation names are the canonical enum values rather than the benchmark’s illustrative prose.
- Implementation correction: render `Run now: D42` as an actual button, even though the static benchmark only communicates its visual placement.
- Implementation correction: after `POST /revalidate`, D42 changes to `REVALIDATING` and the event log records dispatch; the benchmark intentionally depicts the earlier drifted state where D42 is still `STALE`.
- Accessibility: keyboard focus, reduced motion, and status text/icons are implementation requirements even where the static benchmark cannot demonstrate them.
