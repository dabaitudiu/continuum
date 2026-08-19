# Continuum Module 01 — Semantic Dependency Compiler

## Purpose

This package defines the first full-build module after the feasibility spike.

The module turns **probabilistic Gemini decisions** into **machine-verifiable dependency state** that the Continuum runtime can later invalidate deterministically.

It is intentionally deeper than the current ACME reference scenario. The module is not complete merely because a single vendor-onboarding path works.

## Module thesis

> A long-lived agent decision is only safely resumable if the system can identify, validate, persist, and later re-evaluate the material assumptions that made the decision valid.

The compiler therefore transforms:

```text
unstructured enterprise artifacts
+ tool observations
+ Gemini decision proposal

        ↓

validated Decision IR
+ canonical source references
+ material dependency graph
+ provenance record
+ confidence / review status
```

The compiler **does not** decide runtime staleness and **does not** mutate mission state. It produces a validated compilation result; the Continuum runtime remains authoritative.

## Planned engineering budget

**35–45 focused engineering hours** for a competition-grade implementation and evaluation, excluding general platform deployment work.

The budget is expected to be consumed by real uncertainty: document identity, dependency completeness, live-model evaluation, adversarial cases, and benchmark iteration — not by artificial boilerplate.

## Read order

1. `00_MODULE_CHARTER.md`
2. `01_PROBLEM_AND_THESIS.md`
3. `02_ARCHITECTURE.md`
4. `03_ARTIFACT_INGESTION_AND_IDENTITY.md`
5. `04_INTERMEDIATE_REPRESENTATION.md`
6. `05_GEMINI_REASONING_PROTOCOL.md`
7. `06_DEPENDENCY_VALIDATION_AND_CANONICALIZATION.md`
8. `07_COMPLETENESS_AND_CONTRADICTION_CHECKING.md`
9. `08_PERSISTENCE_AND_API_CONTRACTS.md`
10. `09_EVALUATION_BENCHMARK.md`
11. `10_TEST_PLAN.md`
12. `11_SECURITY_AND_ADVERSARIAL_CASES.md`
13. `12_IMPLEMENTATION_PLAN.md`
14. `13_ACCEPTANCE_MATRIX_AND_KILL_CRITERIA.md`
15. `14_CODEX_HANDOFF.md`

## Definition of done

This module is done only when all P0 rows in `13_ACCEPTANCE_MATRIX_AND_KILL_CRITERIA.md` are PASS, including a **live Gemini benchmark**. Codex or any other coding agent may not redefine incomplete P0 work as “optional”, “post-gate”, or “outside the current product boundary”.

## Current status

Phases A–G are implemented and Compiler Lab is locally deliverable. The module itself remains **not done**. The preserved 120-case evidence fails canonical dependency quality, contradiction, outcome, must-block, and acceptance-coverage requirements; the required live Gemini row remains `BLOCKED`. The bounded live paired ablation in `docs/reports/module-01-critic-ablation.md` triggers K3 for the current critic, which recovered no true omission or contradiction signal and added false refs/false blocks. Do not begin Module 02 or remove/replace the critic without product-owner review. See the current acceptance matrix, failure analysis, and ablation report.
