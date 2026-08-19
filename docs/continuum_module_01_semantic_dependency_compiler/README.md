# Continuum Module 01 — Semantic Dependency Compiler

## Purpose

This package defines the first full-build module after the feasibility spike.

The module validates an immutable **domain-agent DecisionProposal** against machine-verifiable Requirement/evidence state that the Continuum Runtime can later invalidate deterministically. Gemini/OpenAI interpret Evidence and contradictions；they do not author the business outcome or governing Requirements.

It is intentionally deeper than the current ACME reference scenario. The module is not complete merely because a single vendor-onboarding path works.

## Module thesis

> A long-lived agent decision is only safely resumable if the system can identify, validate, persist, and later re-evaluate the material assumptions that made the decision valid.

The compiler therefore transforms:

```text
unstructured enterprise artifacts
+ tool observations
+ immutable domain-agent DecisionProposal / DecisionEntityContext
+ trusted reusable rule/decision-class templates

        ↓

validated Decision IR
+ canonical source references
+ material dependency graph
+ proposal/entity/temporal/epoch provenance envelope
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
16. `15_REPLACEMENT_ARCHITECTURE.md`

## Definition of done

This module is done only when all P0 rows in `13_ACCEPTANCE_MATRIX_AND_KILL_CRITERIA.md` are PASS, including a **live Gemini benchmark**. Codex or any other coding agent may not redefine incomplete P0 work as “optional”, “post-gate”, or “outside the current product boundary”.

## Current status

Phases A–G v1 code exists and Compiler Lab is locally deliverable. The module itself remains **not done**. The preserved 120-case evidence fails canonical dependency quality, contradiction, outcome, must-block, and acceptance-coverage requirements; the required live Gemini row remains `BLOCKED`. The bounded live paired ablation in `docs/reports/module-01-critic-ablation.md` triggers K3 for the current critic, which recovered no true omission or contradiction signal and added false refs/false blocks.

On 2026-08-19/20 the product owner selected Option B's direction and rejected the vague critic plus concrete specifications through Revision 5 while accepting P0-1～P0-33 architecturally. `15_REPLACEMENT_ARCHITECTURE.md` Revision 6 preserves those guarantees and adds proposal-admission terminology、Side Effect Ledger execution-start reauthorization、disposition-critical semantic verification and owner-scope `semantic_sequence` total ordering. It awaits product-owner review and is not implemented. Do not write the replacement implementation plan、modify production compiler、generate/read the blind holdout、call live models、run full paid DEV or begin Module 02.
