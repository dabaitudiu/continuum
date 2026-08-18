# Mission Control Local Product Implementation Plan

> **Execution:** Follow this plan autonomously under the active goal. Use test-driven development for every behavior change and verify each checkpoint before committing.

**Goal:** Deliver a complete browser-operated local Continuum demo that performs the canonical v12→v13 selective-revalidation story with durable simulator state, exact Commitments, immutable superseding Decisions, and exactly-once activation.

**Architecture:** Extend the existing `RuntimeSnapshot` aggregate and repository contract with mission-scoped enterprise simulator state. Keep all writes behind `RuntimeCoordinator`; expose a composed control read model for the frontend. The frontend renders one semantic route surface plus a secondary Decision Graph and drives only world-input/command APIs.

**Tech stack:** Python 3.13, FastAPI, Pydantic, SQLite, pytest; React 19, TypeScript, Vite, Vitest/Testing Library, Playwright.

**Authoritative design:** `docs/superpowers/specs/2026-08-18-mission-control-product-design.md`

---

## Task 1: Isolate work and prove the baseline

**Files:** no product changes

1. Create branch `agent/mission-control-product` in `.worktrees/mission-control-product`.
2. Confirm `.worktrees` is ignored and the user-owned `AGENTS.md` edit remains only in the main worktree.
3. Run backend tests with branch coverage, frontend unit tests/build, and Playwright baseline.
4. Record baseline failures before changing code; do not inherit unexplained red tests.

**Checkpoint:** clean isolated branch with the same green baseline as `main`.

## Task 2: Model durable enterprise simulator state

**Files:**

- Modify: `backend/app/runtime/entities.py`
- Modify: `backend/app/runtime/mutations.py`
- Modify: `backend/app/repository/runtime_validation.py`
- Modify: `backend/app/repository/runtime_memory.py`
- Modify: `backend/app/repository/runtime_sqlite.py`
- Modify: `backend/app/demo/runtime_fixture.py`
- Test: `backend/tests/repository/runtime_contract.py`
- Test: `backend/tests/runtime/test_simulator.py`

1. Write failing tests for seeded vendor, current policy artifact, SOC2-only document store, and persistence/restart.
2. Add typed `WorldArtifact`, `VendorRecord`, and `EnterpriseWorld` entities to `RuntimeSnapshot`.
3. Extend atomic mutation/repository persistence without storing an opaque aggregate blob.
4. Seed immutable Policy v12, Vendor Profile r7, SOC2 A31, vendor `PENDING`, and no pen test.
5. Run targeted repository contracts and full backend suite.

**Checkpoint commit:** `feat: persist enterprise simulator world`

## Task 3: Correct mission start semantics

**Files:**

- Modify: `backend/app/runtime/coordinator.py`
- Modify: `backend/app/runtime/commitments.py`
- Modify: `backend/app/runtime/state_machine.py` only if a validated transition is missing
- Test: `backend/tests/runtime/test_coordinator.py`
- Test: `backend/tests/test_runtime_api.py`

1. Replace the Milestone A pen-test-on-start expectation with a failing canonical-story test.
2. On start, complete baseline Vendor/Security/Financial/Procurement work and retain v12-valid graph state.
3. Create one Procurement-owned `procurement.activation.window.opened` Commitment; transition mission to `WAITING`.
4. Add a deterministic Commitment cancellation operation for later invalidation.
5. Assert no pen-test Commitment exists before v13.

**Checkpoint commit:** `fix: align mission start with canonical story`

## Task 4: Integrate policy drift with the runtime aggregate

**Files:**

- Add: `backend/app/runtime/scenario.py`
- Modify: `backend/app/runtime/coordinator.py`
- Modify: `backend/app/domain/invalidation.py` only through reusable public behavior
- Modify: `backend/app/api/runtime_routes.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/runtime/test_scenario.py`
- Test: `backend/tests/test_runtime_api.py`

1. Write a failing command/API test proving the demo control changes the policy artifact and emits an event, rather than assigning node statuses.
2. Traverse from superseded Policy v12 to derive D42/D50/action invalidation; assert D43 stays valid.
3. Cancel the activation-window Commitment, move mission to `REVALIDATING`, and create only Security revalidation work.
4. Make policy-upgrade replay idempotent.
5. Preserve existing graph endpoint response contracts.

**Checkpoint commit:** `feat: drive runtime invalidation from policy events`

## Task 5: Implement affected-branch revalidation and missing evidence

**Files:**

- Add: `backend/app/agents/local_security.py`
- Modify: `backend/app/runtime/scenario.py`
- Modify: `backend/app/api/runtime_routes.py`
- Test: `backend/tests/agents/test_local_security.py`
- Test: `backend/tests/runtime/test_scenario.py`

1. Define and test a structured deterministic local-agent result contract.
2. Revalidate only the Security work against v13 and current artifacts.
3. Produce missing-evidence result and exactly one pen-test Commitment with exact trigger/predicate/resume linkage.
4. Transition Security work and mission to `WAITING`; do not re-run preserved Financial work.
5. Surface `execution_mode=LOCAL_DETERMINISTIC` in the audit/read model.

**Checkpoint commit:** `feat: wait on revalidation evidence`

## Task 6: Resume, supersede, and activate exactly once

**Files:**

- Add: `backend/app/agents/local_procurement.py`
- Modify: `backend/app/runtime/scenario.py`
- Modify: `backend/app/runtime/side_effects.py`
- Modify: `backend/app/api/runtime_routes.py`
- Test: `backend/tests/runtime/test_scenario.py`
- Test: `backend/tests/runtime/test_side_effects.py`
- Test: `backend/tests/test_runtime_restart_api.py`

1. Write failing tests for wrong upload, correct upload, duplicate upload, immutable supersession, and restart safety.
2. Store pen-test artifact and process `vendor.document.uploaded` through Commitment matching.
3. Create a new valid Security Decision superseding D42, then a new Procurement Decision superseding D50 while retaining D43.
4. Make activation READY only after valid current authorizations.
5. Use the side-effect ledger to record `INTENDED → EXECUTING → COMMITTED`, update vendor to `ACTIVE`, and complete the mission.
6. Prove a retry cannot activate twice or duplicate side-effect records.

**Checkpoint commit:** `feat: complete selective resume and activation`

## Task 7: Build the Mission Control read model and API

**Files:**

- Add: `backend/app/api/control_read_model.py`
- Modify: `backend/app/api/runtime_routes.py`
- Test: `backend/tests/test_control_read_model.py`
- Test: `backend/tests/test_runtime_api.py`

1. Write phase-by-phase read-model tests for `CREATED`, `BASELINE_WAITING`, `POLICY_DRIFT`, `MISSING_EVIDENCE`, and `COMPLETED`.
2. Derive `scenario_phase` and `next_action` from canonical state; never persist redundant phase flags.
3. Return mission, agent lanes, checkpoints, Commitments, side effects, graph, event history, policy/vendor status, and execution disclosure.
4. Add `GET /api/missions/{id}/control` and validate 404/domain-error behavior.

**Checkpoint commit:** `feat: expose mission control read model`

## Task 8: Replace the frontend shell with semantic route UI

**Files:**

- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Add: `frontend/src/components/MissionHeader.tsx`
- Add: `frontend/src/components/SemanticRoute.tsx`
- Add: `frontend/src/components/RouteInspector.tsx`
- Add: `frontend/src/components/MissionTimeline.tsx`
- Add: `frontend/src/components/ViewSwitch.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/App.test.tsx`
- Add: `frontend/src/components/SemanticRoute.test.tsx`

1. Write failing UI tests against representative control read models for all phases.
2. Replace auto-reset-on-load with recoverable create/load behavior and explicit busy/error handling.
3. Implement the three-lane semantic route, preserved/stale/block/wait checkpoints, inspector, and contextual action.
4. Retain the existing Decision Graph as a secondary view.
5. Match the checked-in visual benchmark and constants; use no generated bitmap in the shipped UI.
6. Implement keyboard focus, accessible names/live announcements, reduced motion, responsive layouts, and complete loading/error/disabled/success states.

**Checkpoint commit:** `feat: build browser mission control`

## Task 9: Complete browser demo automation

**Files:**

- Modify: `frontend/e2e/falsification-gate.spec.ts` or replace with a mission-control named spec
- Modify: `frontend/playwright.config.ts` only if required
- Add/Modify: test fixtures under `frontend/src/test/`

1. Write an end-to-end test that drives the full browser story.
2. Assert pen-test is absent before v13, D42/D50 stale after v13, D43 preserved, Commitment visible after affected revalidation, and final vendor/mission completion.
3. Assert the activation event/side effect appears once.
4. Cover a narrow viewport smoke test for reachable actions and non-overlapping content.

**Checkpoint commit:** `test: cover complete mission control demo`

## Task 10: Documentation, visual verification, and milestone integration

**Files:**

- Modify: `README.md`
- Modify: `docs/20_DEMO_AND_SUBMISSION.md`
- Add: `docs/reports/mission-control-local-product-report.md`
- Add screenshots under: `docs/reports/assets/`

1. Document exact local run commands and disclose deterministic local agents versus pending Google integration.
2. Start the real backend/frontend, run the scenario in Chromium, and capture at least `POLICY_DRIFT`, `MISSING_EVIDENCE`, and `COMPLETED` screenshots.
3. Compare screenshots to `mission-control-visual-benchmark.png`; fix hierarchy, overflow, contrast, and state legibility regressions.
4. Run backend branch-aware coverage, frontend unit tests, TypeScript/Vite build, Playwright Chromium, and `git diff --check`.
5. Review the final diff for product-semantic accuracy and ensure `AGENTS.md` is not staged.
6. Fast-forward merge the feature branch to local `main`, push `main`, and report the milestone honestly.

**Final checkpoint commit:** `feat: deliver local mission control product`

## Milestone stop/report boundary

Milestone B is complete only when the full canonical story works from a browser and survives a backend restart. Continue immediately to Milestone C (real Google ADK/Gemini agents) after reporting the local product result; do not claim the overall goal complete until the Google Cloud product and submission evidence are real.

