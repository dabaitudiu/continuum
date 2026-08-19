# 14 — Codex Handoff

## Mission

Implement **Module 01: Semantic Dependency Compiler** as specified in this directory.

The existing Continuum ACME demo is a feasibility spike, not the final scope.

## Mandatory reading

Read every file in this module directory before implementation, then inspect the current repository interfaces that touch:

- domain graph models;
- agent structured outputs;
- runtime repository;
- audit/outbox;
- current demo fixtures.

## Non-negotiable rules

1. Do not redefine “done”.
2. Do not reclassify P0 requirements as optional.
3. Do not optimize for the ACME canonical demo.
4. Compiler logic must contain no hardcoded `ACME`, `D42`, `D43`, `D50`, `D57`, `D58`, `policy-v12`, `policy-v13`, or `PEN_TEST` semantics.
5. Gemini may propose refs; canonical refs come only from SourceRegistry.
6. Unknown, unauthorized, or stale refs fail deterministically.
7. Do not persist hidden chain-of-thought.
8. Mock executors are valid for tests but never satisfy the live-Gemini acceptance row.
9. The benchmark is product work, not optional evaluation polish.
10. Stop before Module 02 Drift Engine unless every P0 row is PASS or the product owner explicitly changes scope.

## Suggested branch

```text
module/01-semantic-dependency-compiler
```

## Required implementation outputs

At minimum:

```text
backend/app/compiler/
backend/app/sources/
backend/tests/compiler/
bench/dependency/
docs/reports/module-01-dependency-compiler.md
```

Exact folder structure may adapt to the repo, but separation of responsibilities must remain clear.

## Required report

At module completion, produce a report containing:

- architecture implemented;
- deviations from spec;
- benchmark corpus size;
- live Gemini model/config;
- dependency recall/precision;
- contradiction metrics;
- stale-escape/unnecessary-invalidation metrics;
- adversarial results;
- test/CI commands and actual results;
- remaining P1 items;
- explicit GO / REDESIGN recommendation.

## First implementation instruction

Begin only with Phase A (Source identity kernel). After Phase A tests pass, summarize the implementation against its acceptance criteria before starting Phase B. Continue phase-by-phase, but do not ask to shrink scope simply because a narrow demo already works.
