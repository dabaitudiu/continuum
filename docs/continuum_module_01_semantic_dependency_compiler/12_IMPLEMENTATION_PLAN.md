# 12 — Implementation Plan

## Planned budget

**35–45 focused engineering hours**.

This is a planning range, not a timer-based definition of done. If the work finishes far below the range, review whether meaningful evaluation or scope has been skipped before declaring completion.

## Implementation status — 2026-08-19

The v1 Phases A–G code exists, but its model method is not accepted. The authenticated OpenAI lane failed the Phase F quality gate, and paired Experiment 1 triggered K3 for the current critic. On 2026-08-19 the product owner selected Option B: replace the vague critic with Requirement Decomposition, Evidence Binding, an Independent Contradiction Pass, Requirement Completeness, and a Deterministic Acceptance Gate. Option A remains a benchmark baseline only; Option C is rejected.

The replacement design is specified in `15_REPLACEMENT_ARCHITECTURE.md` and is **not yet implemented**. No implementation plan may begin until the product owner reviews that design. No full 120-case paid benchmark, holdout inference, live Gemini acceptance, or Module 02 work is authorized at this stage.

## Replacement sequence after design approval

This is a phase boundary, not authorization to code:

1. freeze method-blind requirement annotations and the 60-case locked holdout before v2 implementation;
2. write a detailed implementation plan with verification checkpoints;
3. freeze the old critic as a benchmark-only legacy arm and remove it from v2/default candidate production wiring;
4. implement typed Requirements and EvidenceBindings plus deterministic validators;
5. implement the dedicated Contradiction and Requirement Completeness stages;
6. implement the deterministic outcome/acceptance gate and canonical transitive mapping;
7. execute preregistered Experiments 2–4, then the three-arm 30-case Experiment 5;
8. stop on any failed progression gate; only a PASS permits full DEV, holdout, then live Gemini in that order.

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
