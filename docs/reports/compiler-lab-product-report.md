# Compiler Lab Local Product Report

**Date:** 2026-08-19
**Scope:** Semantic Dependency Compiler Phases B–G
**Product result:** PASS — browser-operated deterministic reference product
**Module 01 P0 result:** BLOCKED — authenticated live-model evidence is absent

## Delivered product flow

Compiler Lab is a fourth top-level Continuum view. It runs four bounded server-side reference cases and renders the actual compilation aggregate rather than a static mock:

1. `authorized-access` → `ACCEPTED`, followed by an explicit Runtime commit and audit-linked receipt;
2. `missing-governing-clause` → `REJECTED_INCOMPLETE_DEPENDENCIES`;
3. `conflicting-authorities` → `NEEDS_HUMAN_REVIEW`;
4. `obsolete-policy-ref` → `REJECTED_STALE_SOURCE`.

The screen exposes `Execution mode: DETERMINISTIC_REFERENCE`, the backend-authored six-stage `REQUESTED → DRAFT_RECEIVED → VALIDATED → REVIEWED → COMPILED → RUNTIME_ACCEPTED` trace with MODEL/COMPILER/RUNTIME ownership and explicit `DONE / ACTIVE / SKIPPED / WAITING` truth, exact revision/representation/fragment-qualified source refs, source hashes, canonical claims, dependency relations, deterministic and critic findings, compilation disposition, immutable compilation hash, and Runtime receipt. A validator rejection marks unexecuted review/compiler/runtime stages `SKIPPED`; blocking dispositions never expose a Runtime mutation control.

## Runtime boundary

- The internal compiler API creates immutable request → draft → result aggregates and is disabled by default unless an internal service capability is configured.
- General acceptance requires a constant-time checked runtime capability header.
- The public product demo uses a separate in-process registration boundary: a recognizable request prefix alone is insufficient to access Runtime mutation.
- Public reference runs validate a bounded request ID and enforce a per-client sliding-window rate limit before creating compiler aggregates.
- Acceptance checks the exact mission revision and world snapshot used for compilation.
- Decision, Claim, Evidence, dependency edges, audit, inbox, and outbox commit atomically; replay returns the existing receipt without a second mission revision.
- Source revisions bind to the currently active Runtime artifact instance, so update → recompile → update remains invalidatable.
- A separate outbox relay worker pages over the Firestore pending-outbox projection; a Cloud Scheduler trigger invokes its Cloud Run Job every two minutes with OAuth, so old pending Missions cannot be starved by newer idle Missions and retries do not require command replay.
- The compiler can propose canonical state, but deterministic Runtime code remains the only owner of state transitions.

## Honest model-evidence boundary

Compiler Lab permanently separates three evidence lanes:

- `DETERMINISTIC REFERENCE`: `PASS`; proves fixture, compiler, repository, API, and UI wiring only.
- `OPENAI EVIDENCE`: `BLOCKED`; `OPENAI_API_KEY` was not present. The transport and persisted reserve/settle ledger exist, with an immutable cumulative hard cap of $10. Call IDs grant execution ownership once; ambiguous post-send failures retain the worst-case reservation and cannot be replayed through the ledger.
- `GEMINI EVIDENCE`: `BLOCKED`; neither Gemini key nor configured Vertex credentials were present.

No deterministic score is reported as live-model performance. OpenAI can provide an additional falsification lane but does not replace the module's explicit live-Gemini P0 requirement.

## Visual verification

- `docs/reports/assets/compiler-lab-visual-benchmark.png` — generated design benchmark.
- `docs/reports/assets/compiler-lab-product.png` — real 1440×1024 browser result with Runtime receipt.
- `docs/reports/assets/compiler-lab-mobile.png` — real 320×844 responsive result.

Desktop measurement produced the intended `264px / 856px / 320px` source, provenance, and ledger columns. Desktop and mobile document widths equal their viewports; the mobile navigation keeps all four product views in bounds. Browser console capture contained no warning or error.

## Automated evidence

- The full backend suite reports **449 passed, 2 live credential tests skipped**, with **89% branch-aware coverage**.
- The frontend suite reports **19/19 passed**, followed by a successful TypeScript/Vite production build.
- Compiler demo/API tests cover failure-closed default behavior, generic API isolation, honest PASS/FAIL/BLOCKED evidence status, all four dispositions, exactly-once acceptance, prefix-forgery refusal, and reference replay.
- Frontend behavior tests cover accepted compilation through Runtime receipt and rejected compilation without a mutation action.
- Four Playwright Chromium end-to-end tests cover the canonical Semantic Resume story, keyboard/mobile Mission Control, accepted and blocked Compiler Lab paths, and compiled-state 320px overflow checks.
- This report does not promote the two skipped live tests to passes; their lanes remain `BLOCKED` in the generated benchmark report.

## Stop condition

The Compiler Lab product and Phases B–G implementation are delivered. Do not proceed to a full Drift Engine build until the `BLOCKED`/`PARTIAL` rows in the Module 01 P0 matrix are resolved, especially live Gemini, live dependency quality metrics, live prompt-injection findings, and K6.
