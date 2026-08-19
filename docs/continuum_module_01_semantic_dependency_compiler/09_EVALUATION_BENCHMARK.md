# 09 — Evaluation Benchmark: Continuum Dependency Bench

## Goal

Avoid evaluating the compiler only on the one scenario it was designed around.

## Option B evaluation amendment

The current 120-case corpus remains the DEV set and its existing refs, outcomes, contradictions, mutations, and thresholds are immutable. The product owner approved a requirement-centred replacement architecture, but did **not** authorize tuning against individual cases or a full paid rerun.

Before any v2 prompt/schema/logic implementation:

1. freeze a separate method-blind `requirement-ground-truth-v1` annotation for the existing cases;
2. freeze a 60-case locked generalization set and hash manifest;
3. prove production code and prompts cannot import either ground-truth surface;
4. preregister each bounded live experiment.

The exact freeze, three-arm ablation, progression, and stop rules are normative in [15_REPLACEMENT_ARCHITECTURE.md](15_REPLACEMENT_ARCHITECTURE.md).

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

For v2, a separate frozen annotation adds method-neutral APPROVE-validity Requirements (proposition, expected truth, DIRECT/DERIVED_ALL proof mode, and conjunction DAG). This additive annotation does not change existing required/forbidden refs or expected outcomes. It must be committed before v2 implementation and never exposed to production compiler paths.

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

## Locked generalization set

The holdout contains 60 cases: 20 per domain and two per existing semantic class in each domain. It preserves category balance while changing scenario families, task/source wording, fragment arrangement, source order, and distractor layout. Its manifest records per-file and aggregate SHA-256 plus authoring/schema provenance.

DEV and HOLDOUT results are always reported separately. HOLDOUT receives no live inference until full 120-case DEV passes every P0 metric, and no prompt/logic/threshold change may target an individual holdout case.

## Baselines

Primary three-arm comparison:

1. **Document-level dependency baseline** — every document read becomes critical.
2. **Reasoner-only (Option A)** — frozen single-pass baseline; never the final architecture.
3. **Old critic pipeline** — frozen K3 legacy baseline; no further tuning and no Runtime eligibility.
4. **New requirement-centred pipeline (Option B)** — Requirement Decomposition, Evidence Binding, Independent Contradiction, Requirement Completeness, and Deterministic Acceptance Gate.

The primary Option A/B-legacy/Option B-new comparison uses the same frozen 30-case stratified subset, tasks, sources, provider/model settings, and metric implementation. Architecture-specific prompt/schema/call topology is an explicit experimental variable and must be reported with stage calls, latency, tokens, and cost.

Requirement/proof-mode metrics apply only to the new architecture and are reported as `N/A` for legacy arms. Three-arm headline deltas use only metrics defined identically across all arms; C-only diagnostics remain separate.

Proposal-union refs, accepted canonical refs, accepted compilation coverage, and Runtime mutation outcomes are distinct metrics. NOT_ACCEPTED cases are not counted as Runtime stale escapes; accepted-only mutation rates always disclose their denominators.

For v2, report EvidenceBinding-proposal recall/precision separately from accepted `DecisionJustification` canonical recall/precision and corpus coverage. A minimal proof slice is not allowed to make unaccepted or unselected ground-truth dependencies disappear from the coverage denominator.

The benchmark should demonstrate why the compiler adds value beyond “ask Gemini to list citations”.

## Deliverable

Generate a machine-readable report plus a short human summary suitable for the hackathon repo and architecture discussion.
