# 19 — Gemini Handoff Prompts

Use these prompts with the coding agent. Do not ask for the entire project in one prompt.

## Master initialization prompt

> Read `README.md`, `GEMINI.md`, and every numbered design document. Do not write application code yet. First produce a concise implementation map: components, dependency order, unknown Google API details that need official-doc verification, and any contradiction you find in the specs. Treat deterministic invalidation, commitment matching, and side-effect idempotency as non-negotiable runtime semantics. After the map, begin only Phase 1 of `18_BUILD_PLAN.md`.

## Phase transition prompt

> Continue with Phase N from `18_BUILD_PLAN.md`. Before changing code, restate the acceptance criteria for this phase. Implement only what is needed for those criteria. Run the specified tests/checks. If any acceptance criterion fails, debug it now and do not continue to the next phase. At the end, summarize files changed, verification performed, remaining risks, and the exact next phase.

## Phase 3 special prompt — invalidation kernel

> Implement the deterministic invalidation kernel from `06_DECISION_PROVENANCE_AND_INVALIDATION.md` and the exact falsification fixture from `17_36H_FALSIFICATION_GATE.md`. The algorithm must be generic over stored dependency edges and relation types. Do not call Gemini to decide stale propagation. Add tests proving D42 and D50 become stale, D43 remains valid, and ActivateVendor is blocked after Policy v13 supersedes v12.

## Phase 8 special prompt — Gemini agents

> Implement the three ADK agents from `09_AGENTS_AND_TOOLS.md`. Use Gemini 3.5 Flash or a newer contest-eligible Gemini model. Require structured outputs for decisions and dependency proposals. An agent may propose a dependency only by referencing an existing evidence/artifact/decision identifier supplied in its task context. The control plane must validate these references before accepting the proposal. Do not allow the model to mutate canonical state directly.

## Google API verification prompt

> Before using any Google Agent Platform API whose current name, version, location, or launch stage is uncertain, check the latest official Google Cloud / ADK documentation. Prefer GA features for the demo path. Keep Preview features behind optional adapters so the P0 flow remains functional if provisioning fails.

## UI polish prompt

> Review `11_UI_UX_SPEC.md`. Optimize for a judge understanding the policy-drift story at a glance. Do not add decorative dashboards that dilute the Decision Graph. The most important visual sequence is Policy v12->v13, D42/D50 stale, D43 valid, activation blocked, then selective revalidation.

## Pre-video hardening prompt

> Run the complete seeded demo three times from a clean/reset state. Record every failure, nondeterministic behavior, slow API call, and manual intervention. Fix anything that threatens a four-minute unedited demonstration. Do not add new features until three consecutive runs pass.
