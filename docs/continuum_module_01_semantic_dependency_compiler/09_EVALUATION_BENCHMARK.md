# 09 — Evaluation Benchmark: Continuum Dependency Bench

## Goal

Avoid evaluating the compiler only on the one scenario it was designed around.

## P0 benchmark size

**Minimum 120 labeled cases** across at least three mission domains.

Recommended composition:

### Domain A — Vendor onboarding (40)

- security policy applicability;
- SOC2 / pen-test evidence;
- data classification;
- residency clauses;
- conflicting document versions.

### Domain B — Production release approval (40)

- test reports;
- change-management policy;
- security scans;
- rollback readiness;
- release permissions.

### Domain C — Privileged access approval (40)

- role eligibility;
- manager approval;
- security training;
- time-limited access;
- identity/permission policy.

## Case classes

Across domains include:

- clean positive decisions;
- clean negative decisions;
- one omitted critical dependency;
- one irrelevant distractor;
- obsolete source revision;
- conflicting sources;
- near-duplicate policy clauses;
- source with prompt injection text;
- multiple simultaneous material dependencies;
- cases where only one narrow clause is relevant.

## Ground truth

Each case defines:

```text
required_critical_refs
acceptable_supporting_refs
forbidden_or_irrelevant_refs
expected_outcome_constraints
blocking_contradictions
expected_staleness_after_mutation
```

Ground truth is manually authored and version-controlled.

The model request receives the complete decision-type outcome vocabulary (`APPROVED`, `DENIED`, `NEEDS_HUMAN_REVIEW`) so the categorical field is well-defined. It never receives the case's ground-truth `allowed_outcomes`; exposing that singleton would leak the answer and invalidate outcome compliance.

## Metrics

### Dependency Critical Recall

Critical ground-truth refs recovered / total critical refs.

Target P0: **>= 0.92** overall; no domain below 0.88.

### Dependency Precision

Accepted critical refs that are ground-truth material / all accepted critical refs.

Target P0: **>= 0.82**.

### Unsupported Reference Rate

Canonical unknown/unauthorized refs accepted.

Target: **0%** by deterministic validator.

### Stale Decision Escape Rate

After a ground-truth material dependency mutates, percent of affected decisions not marked for revalidation downstream.

Compiler+drift integration target: **< 2%** on benchmark.

### Unnecessary Invalidation Rate

Unchanged decisions incorrectly invalidated after unrelated mutations.

Target P0: **< 8%**.

### Contradiction Detection Recall

Material contradictions flagged.

Target P0: **>= 0.90**.

### Compilation Determinism

Same validated draft → identical canonical graph.

Target: **100%**.

## Model variance protocol

Run live-model cases multiple times.

Recommended:

- 3 runs/case for 30-case variance subset;
- report mean and worst-run critical recall;
- persist model name, temperature/config, prompt version.

## Baselines

Compare against:

1. **Document-level dependency baseline** — every document read becomes critical.
2. **Single-pass Gemini refs** — no critic.
3. **Compiler full pipeline** — reasoner + validation + critic + contradiction handling.

The benchmark should demonstrate why the compiler adds value beyond “ask Gemini to list citations”.

## Deliverable

Generate a machine-readable report plus a short human summary suitable for the hackathon repo and architecture discussion.
