# 12 — Implementation Plan

## Planned budget

**35–45 focused engineering hours**.

This is a planning range, not a timer-based definition of done. If the work finishes far below the range, review whether meaningful evaluation or scope has been skipped before declaring completion.

## Implementation status — 2026-08-19

The v1 Phases A–G code exists, but its model method is not accepted. The authenticated OpenAI lane failed the Phase F quality gate, and paired Experiment 1 triggered K3 for the current critic. On 2026-08-19 the product owner selected Option B's direction, rejected the vague critic, and then **rejected the first concrete Option B specification** on 11 P0 architectural blockers. Option A remains a benchmark baseline only; Option C is rejected.

Revision 2 is specified in `15_REPLACEMENT_ARCHITECTURE.md` and is **under review, not approved or implemented**. The product owner explicitly prohibited writing a v2 implementation plan at this stage. No production compiler change、blind-holdout generation/read、live model call、full 120 paid benchmark、live Gemini acceptance or Module 02 work is authorized.

## V2 planning gate

No Revision-2 implementation sequence is specified here because the concrete architecture has not been approved. After product-owner approval, a separate planning step may translate the approved contracts into verification checkpoints.

The independently owned blind holdout is **not** a development-plan artifact. The implementation agent may see only metadata until full DEV PASS and methodology freeze; it must not generate、read or commit holdout bodies.

The historical phases below describe the v1 build and remain for audit; they are not evidence that the replacement architecture is complete.

## Phase A — Source identity kernel (5–6h)

Build:

- Artifact / Revision / ParsedRepresentation / Fragment models;
- stable reference parser/formatter;
- content hashes;
- world-snapshot binding;
- SourceRegistry interface and local store.

Acceptance:

- revisions immutable;
- refs round-trip;
- stale/current lookup works;
- parser versions of one revision coexist and old provenance resolves exactly;
- equal-content business revision labels coexist;
- arbitrary structured JSON field names round-trip;
- structured JSON field refs remain stable;
- list insertion cannot silently retarget an existing dependency.

## Phase B — IR and compiler skeleton (4–5h)

Build:

- DecisionDraft;
- ClaimDraft;
- DependencyRef;
- CompilationResult;
- finding types;
- compiler service pipeline.

Acceptance:

- schema fixtures compile/reject correctly;
- no runtime mutation occurs.

## Phase C — Deterministic validator/canonicalizer (6–7h)

Build:

- ref integrity;
- scope validation;
- temporal validation;
- relation constraints;
- materiality rules;
- deterministic canonicalization;
- compilation hash.

Acceptance:

- unknown/stale/unauthorized refs cannot compile;
- same draft yields identical canonical output.

## Phase D — Gemini reasoner integration (5–6h)

Build:

- read-only source tools;
- structured reasoner output;
- retry/error handling;
- prompt versioning;
- model metadata capture.

Acceptance:

- live Gemini produces valid proposals on multi-source cases;
- no fake executor used as evidence for completion.

## Phase E — Completeness + contradiction pipeline (5–6h)

Build:

- critic schema/prompt;
- contradiction finding model;
- authority precedence rules;
- review/reject dispositions.

Acceptance:

- deliberate omission cases are caught;
- unresolved material contradiction blocks approval.

## Phase F — Continuum Dependency Bench (7–9h)

Build:

- 120 labeled cases across three domains;
- runner;
- metrics;
- variance subset;
- baselines;
- report generator.

Acceptance:

- metrics computed reproducibly;
- targets in acceptance matrix met or module is declared not ready.

## Phase G — Runtime integration (3–4h)

Build:

- compilation acceptance endpoint;
- graph mutation translation;
- optimistic revision/world-snapshot check;
- audit linkage by compilation_id.

Acceptance:

- accepted compilation creates canonical runtime provenance;
- stale world snapshot cannot be committed.

## Stop condition

Do not begin Drift Engine full implementation until Module 01 P0 acceptance is complete, because Drift Engine quality depends on dependency quality.
