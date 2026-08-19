# Compiler Lab Local Product Report

**Date:** 2026-08-19
**Scope:** Semantic Dependency Compiler Phases B–G
**Product result:** PASS — browser-operated deterministic reference product
**Module 01 P0 result:** NOT READY — authenticated OpenAI evidence fails the gate; Gemini remains blocked

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
- A separate outbox relay worker transactionally backfills legacy projection schema, then pages over the Firestore pending-outbox projection; deployment also removes the obsolete project-level runtime invoker grant before a least-privilege Scheduler identity is bound only to that Cloud Run Job and invokes it every two minutes with OAuth. Old pending Missions cannot be starved by newer idle Missions, and retries do not require command replay.
- The compiler can propose canonical state, but deterministic Runtime code remains the only owner of state transitions.

## Honest model-evidence boundary

Compiler Lab permanently separates three evidence lanes:

- `DETERMINISTIC REFERENCE`: `PASS`; proves fixture, compiler, repository, API, and UI wiring only.
- `OPENAI EVIDENCE`: `FAIL`; an authenticated `gpt-5.6-luna` run completed 120 primary cases plus 90 variance observations. Critical recall is 98.21%, but precision is 65.48%, contradiction recall is 0%, outcome compliance is 42.50%, must-block compliance is 26.67%, and stale escape is 80.56%. The report-recorded run cost is $0.419523600 for 272 settled attempts, including 309,424 cache-write tokens. The persisted reserve/settle ledger retains an immutable cumulative hard cap of $10: SDK retries are disabled, service tier is fixed to `default`, cache writes are charged at 1.25× uncached input, call IDs grant execution ownership once, and ambiguous or legacy exposure retains a conservative worst-case UNKNOWN hold.
- `GEMINI EVIDENCE`: `BLOCKED`; neither Gemini key nor configured Vertex credentials were present.

No deterministic score is reported as live-model performance. Recorded evidence status and current credential availability are disclosed independently: the historical OpenAI `FAIL` remains visible when no key is loaded, while the UI also says that the current key is unavailable. OpenAI can provide an additional falsification lane but does not replace the module's explicit live-Gemini P0 requirement.

## Visual verification

- `docs/reports/assets/compiler-lab-visual-benchmark.png` — generated design benchmark.
- `docs/reports/assets/compiler-lab-product.png` — real 1440×1024 browser result with Runtime receipt.
- `docs/reports/assets/compiler-lab-mobile.png` — real 320×844 responsive result.

Desktop measurement produced the intended `264px / 856px / 320px` source, provenance, and ledger columns. Desktop and mobile document widths equal their viewports; the mobile navigation keeps all four product views in bounds. Browser console capture contained no warning or error.

## Automated evidence

- The full backend suite passes: 458 tests passed, 2 authenticated live tests skipped without injected credentials, and branch-aware coverage is 89%.
- The frontend suite passes 20/20 tests and the production TypeScript/Vite build succeeds.
- Compiler demo/API tests cover failure-closed default behavior, generic API isolation, honest PASS/FAIL/BLOCKED evidence status, all four dispositions, exactly-once acceptance, prefix-forgery refusal, and reference replay.
- Frontend behavior tests cover accepted compilation through Runtime receipt and rejected compilation without a mutation action.
- Four Playwright Chromium end-to-end tests cover the canonical Semantic Resume story, keyboard/mobile Mission Control, accepted and blocked Compiler Lab paths, and compiled-state 320px overflow checks.
- The generated benchmark report preserves the authenticated OpenAI metric failure and the credential-blocked Gemini lane independently; neither is promoted by deterministic fixtures.

## Stop condition

The Compiler Lab product and Phases B–G implementation are delivered. Do not proceed to a full Drift Engine build while the OpenAI quality rows are `FAIL` or the required Gemini row is `BLOCKED`. The next bounded work is compiler-method redesign/ablation against the failed precision, contradiction, outcome, must-block, and stale-escape rows—not expansion into Module 02.
