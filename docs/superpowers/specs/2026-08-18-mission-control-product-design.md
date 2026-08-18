# Continuum Mission Control — Local Product Design

**Date:** 2026-08-18  
**Status:** Approved by active goal-mode authorization  
**Milestone:** B — browser-operable local product  
**Scope boundary:** deterministic local agents and enterprise simulator; no Gemini/ADK or Google Cloud claims yet

## Outcome

Milestone B turns the proven semantic runtime into a complete, browser-operable demonstration of the canonical Acme Analytics story:

1. Policy v12 authorizes Security Decision D42 using SOC2 A31 and Vendor Profile r7.
2. Procurement Decision D50 depends on D42; Financial Review D43 is independent.
3. The mission waits for an external procurement activation window.
4. A simulator event upgrades Policy v12 to v13.
5. Deterministic invalidation makes D42 and D50 `STALE`, leaves D43 `VALID`, and blocks activation.
6. Only the Security branch re-runs. Its local deterministic agent discovers that v13 requires a penetration test and creates a durable Commitment.
7. Uploading `pen-test-P9.pdf` satisfies that Commitment exactly once.
8. Security and Procurement issue immutable superseding Decisions; the side-effect ledger commits vendor activation exactly once.
9. The mission completes with Vendor `ACTIVE` and an auditable causal history.

The UI must let a judge answer, without opening a terminal:

- What is the mission doing now?
- What changed in the world?
- Which prior conclusion is no longer authorized, and why?
- Which work will re-run, and which work is preserved?
- What external event is awaited?
- What side effect was blocked or committed?

## Semantic correction from Milestone A

Milestone A deliberately used a pen-test Commitment immediately after `start` to validate Commitment matching and persistence. That fixture is not the final product story and must not be presented as one.

Milestone B changes `start` so that Policy v12 initially approves Security using SOC2 evidence. The mission then waits on an **activation-window Commitment** owned by Procurement. The pen-test Commitment is created only after the v13 event invalidates D42 and the affected Security branch re-evaluates the new policy.

Demo controls modify only versioned world artifacts or emit external events. They never assign Decision states directly.

## Product states and operator actions

The control-plane read model exposes one explicit `scenario_phase` and one contextual `next_action`:

| Phase | Mission | Primary action | Expected semantic result |
|---|---|---|---|
| `CREATED` | `CREATED` | Start mission | Baseline v12 decisions become valid; mission waits on procurement activation window |
| `BASELINE_WAITING` | `WAITING` | Inject Policy v13 | v12 artifact superseded; D42/D50 stale; D43 preserved; activation blocked |
| `POLICY_DRIFT` | `REVALIDATING` | Run affected branch | Security alone re-runs, detects missing pen test, opens Commitment |
| `MISSING_EVIDENCE` | `WAITING` | Upload pen test · +7 days | Commitment satisfied once; D42/D50 superseded; activation committed |
| `COMPLETED` | `COMPLETED` | Reset demo | Fresh isolated mission and simulator world |

All mutating actions require an idempotency/event ID. Replaying an action returns the prior result and creates no duplicate transition, Commitment, Decision, or side effect.

## Domain changes

### Enterprise simulator

Add durable, mission-scoped simulator state:

- Vendor record: `ACME_ANALYTICS`, profile r7, customer PII true, status `PENDING | ACTIVE`.
- Policy store: immutable v12 and v13 artifacts with one current version.
- Document store: initial SOC2 A31; later pen-test P9.
- Procurement system: an activation window is initially pending.

The local adapter is named and surfaced as `Deterministic local agent adapter`. It is not described as Gemini or ADK.

### Start command

`POST /api/missions/{id}/start` atomically:

- transitions mission `CREATED → RUNNING → WAITING`;
- completes Vendor, Security, Financial, and Procurement baseline work;
- preserves the seeded v12 graph in `VALID/READY` state;
- creates a Procurement-owned activation-window Commitment;
- records audit/outbox events for every meaningful transition.

### Policy upgrade

`POST /api/demo/policy/upgrade` atomically:

- creates/supersedes the versioned policy artifact and emits `policy.version.changed`;
- uses the deterministic invalidation kernel to derive D42/D50/action changes;
- cancels the now-unauthorized activation-window Commitment;
- moves the mission to `REVALIDATING`;
- enqueues only Security revalidation work.

The endpoint never sets D42 or D50 by ID. Node IDs exist in the fixture, while the runtime operation starts from the superseded artifact and traverses dependency edges.

### Affected-branch revalidation

`POST /api/missions/{id}/revalidate` atomically:

- runs the deterministic local Security adapter against the current artifact versions;
- returns a structured missing-evidence result;
- creates the exact pen-test Commitment from `docs/07_COMMITMENT_MEMORY.md`;
- transitions Security work and mission to `WAITING`;
- leaves preserved work untouched.

### Pen-test arrival and resume

`POST /api/demo/documents/pen-test` atomically:

- stores the versioned document artifact and emits `vendor.document.uploaded`;
- satisfies the matching Commitment exactly once;
- resumes only its linked Security work;
- creates a new Security Decision that supersedes D42;
- creates a new Procurement Decision that supersedes D50 and still depends on preserved D43;
- transitions `ActivateVendor` from `BLOCKED → READY`;
- records side-effect intent, execution, and commit with one idempotency key;
- marks the simulator vendor `ACTIVE` and mission `COMPLETED`.

## API/read model

Add `GET /api/missions/{id}/control`, returning a composed, read-only product view:

- mission identity, status, subject, created/updated time;
- `scenario_phase`, `next_action`, current policy, vendor status;
- three agent lanes and their ordered work/decision checkpoints;
- current and historical Commitments;
- current side effects;
- graph read model;
- ordered audit timeline;
- `execution_mode: LOCAL_DETERMINISTIC`.

Existing graph and runtime endpoints remain compatible. Mutation responses may stay compact; the client refreshes the control read model after each mutation.

## Interaction design

### Design Read

- Artifact: interactive enterprise mission-control prototype
- Audience: hackathon judges, enterprise architects, runtime operators
- Mode: overhaul of the existing shell while preserving light tokens and provenance concepts
- Visual variance: 5/10
- Motion intensity: 4/10
- Information density: 8/10
- Asset dependence: 2/10
- Brand fidelity: 7/10
- Copy register: 8/10, concise professional English

### Chosen visual language

**Primary: Rail Dispatch (65%).** A long-running mission is drawn as three fixed operational lanes—Vendor, Security, Procurement—with signals for Decisions, holds for Commitments, and a shared activation terminus. When policy changes, the affected route becomes visibly severed while the Financial branch stays steady.

**Secondary: Scientific Data UI (35%).** Provenance, artifact versions, event times, causal explanations, and exact statuses use dense tabular rhythm, monospaced identifiers, fine rules, and explicit units/labels.

The visual metaphor remains operational, not illustrative: no locomotives, maps, skeuomorphism, or playful railway decoration.

### Rejected directions

1. **Canvas Builder.** It was the prior prototype's dominant style and makes the dependency graph look like the whole product. It hides the mission narrative and is therefore reserved for the secondary Decision Graph view.
2. **SOC Command.** Alert-heavy dark dashboards create alarm fatigue and falsely frame semantic drift as generic incident monitoring.
3. **Bento.** Independent tiles fragment a causal sequence and weaken the distinction between preserved and invalidated branches.

### Reference principles

- Temporal's Workflow History treats a durable ordered history as the source for reconstructing execution state; Continuum borrows the readable event-history rhythm, not Temporal's product scope: <https://github.com/temporalio/temporal/blob/main/docs/architecture/history-service.md>
- Temporal's UI changelog emphasizes quick workflow comprehension plus a live event feed; Continuum applies that as a mission summary paired with causal timeline: <https://temporal.io/changelog/temporal-web-ui-v2-26-0>
- OpenLineage/Marquez combines lineage graph, run history, and node detail; Continuum similarly separates the route overview from a dedicated provenance graph/detail surface: <https://openlineage.io/getting-started/>
- OpenLineage's failure tutorial uses lineage to trace a changed upstream schema into affected downstream work; Continuum makes this impact path the central visual event: <https://openlineage.io/docs/1.49.0/guides/airflow-quickstart/>

### Screen structure

The viewport is a single working surface, not a grid of cards:

1. **Utility rail:** Continuum wordmark, execution-mode disclosure, mission ID, Reset.
2. **Mission header:** subject, large semantic status, policy/version, vendor status, one contextual primary action.
3. **Semantic route:** the dominant center panel with three agent lanes, ordered checkpoints, dependency crossings, stale severance, preserved marker, and final activation gate.
4. **Inspector:** a persistent right column explaining the currently selected event/checkpoint with source version, cause, consequence, and next action.
5. **Event history:** a dense chronological ledger beneath the route with explicit timestamps and causal labels.
6. **View switch:** `Mission route` is default; `Decision graph` opens the existing detailed graph without replacing the mission context.

The generated implementation benchmark is stored at
`docs/reports/assets/mission-control-visual-benchmark.png`. It is a composition,
hierarchy, density, and color reference only. Generated microcopy is not
authoritative; all shipped labels come from typed application data and the
copy defined in this document.

### State choreography

- `CREATED`: route geometry is visible but muted; Start is the only dominant action.
- `BASELINE_WAITING`: v12 path is continuous; activation terminus shows an amber external hold.
- `POLICY_DRIFT`: a short signal sweep starts at Policy v13 and stops at D42/D50; D43 never animates or changes color. The inspector states “Preserved: no dependency on Policy v12.”
- `MISSING_EVIDENCE`: Security lane terminates at a visible Commitment hold with its exact event predicate and resume target.
- `COMPLETED`: new superseding checkpoints form a continuous route to `ACTIVE`; old stale checkpoints remain visible as history, not erased.

Motion is CSS-only, respects `prefers-reduced-motion`, and never loops indefinitely. Status meaning is carried by label and shape in addition to color.

### Visual constants

- Canvas: mineral white `#F4F3EF`; working surface `#FCFBF8`; ink `#18201D`.
- Accent: signal green `#167A5A`; stale vermilion `#C74B36`; waiting amber `#B87917`; preserved blue `#396A8C`.
- Borders: 1px `#D6D8D2`; separators 1px; selected checkpoint 2px ink outline.
- Radius: 2px controls/checkpoints, 4px panels; no pill containers except compact status tokens.
- Shadow: only inspector elevation, `0 8px 24px rgba(24,32,29,.08)`.
- Spacing: 4/8/12/16/24/32px scale.
- Type: IBM Plex Sans for interface; IBM Plex Mono for IDs, versions, times, predicates.
- Main route stroke: 2px; invalidated segment uses 2px broken vermilion line; preserved segment uses 2px solid neutral/blue.

### Responsive behavior

- ≥1180px: route and inspector side-by-side; history full width below.
- 760–1179px: inspector becomes a lower detail band; route remains horizontally scrollable with a visible cue.
- <760px: utility/header wrap; agent lanes stack as ordered mini-routes; primary action stays reachable; no information disappears.

### Accessibility and complete states

- Every action is keyboard reachable and has a visible focus ring.
- ARIA live region announces completed semantic transitions.
- Status labels are text, not color alone; route checkpoints expose meaningful accessible names.
- Loading uses reserved geometry and `aria-busy`.
- Empty state offers `Run demo scenario`.
- Error state preserves the last valid read model, states what failed, and offers Retry.
- Mutations disable only the relevant action, show a deterministic progress verb, and protect against double submission.
- Completion provides a success summary and an audit link, without confetti or decorative celebration.

## Test and acceptance contract

### Backend

- Start produces v12 baseline and activation-window wait, never a pen-test Commitment.
- Policy upgrade from the artifact root produces exactly D42/D50 stale, D43 valid, and action blocked.
- Revalidation creates one pen-test Commitment and no other open Commitment.
- Wrong upload event is ignored; correct upload satisfies once; replay is idempotent.
- New Decisions supersede old IDs; old Decisions are retained.
- Side-effect retries cannot duplicate vendor activation.
- Restarting the API with the same SQLite file reconstructs the same phase/read model.

### Frontend

- Each phase renders the correct route, inspector explanation, Commitment, and primary action.
- The preserved D43 branch stays visually unchanged across policy drift.
- Users can operate the entire story with keyboard and browser only.
- Loading, error, disabled, and completed states are tested.
- Existing Decision Graph semantics remain accessible and correct.

### End-to-end

One Playwright test runs reset/create → start → v13 → affected revalidation → pen-test arrival → completion and asserts:

- D42 and D50 are stale after v13;
- D43 remains valid;
- pen-test is not requested before v13;
- Commitment appears after revalidation;
- Vendor ends `ACTIVE` and Mission `COMPLETED`;
- the final activation side effect appears once.

## Explicit non-goals

- No generic workflow or agent builder.
- No free-form mission authoring.
- No generic IAM, memory platform, or Temporal replacement.
- No claims that local deterministic adapters are Gemini, ADK, or deployed on Google Cloud.
- No fault-injection UI unless the core browser story is already stable.
