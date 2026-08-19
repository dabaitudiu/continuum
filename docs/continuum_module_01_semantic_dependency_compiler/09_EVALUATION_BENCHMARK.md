# 09 — Evaluation Benchmark: Continuum Dependency Bench

## Goal

Avoid evaluating the compiler only on the one scenario it was designed around.

## Option B evaluation amendment

The current 120-case corpus remains the visible DEV set and its existing refs、outcomes、contradictions、mutations and thresholds are immutable. The product owner approved Option B's direction but rejected the first concrete specification. No individual-case tuning or full paid rerun is authorized.

Before any v2 prompt/schema/logic implementation, only DEV-facing annotation work may occur:

1. freeze a separate method-blind `requirement-ground-truth-v1` annotation for the existing cases;
2. add labels for stable predicate identity、Stage-1 omission、coverage recovery、unsupported logic、three-state entailment、deterministic proof materiality/contradiction impact and policy/manifest mutation;
3. prove production code and prompts cannot import DEV ground truth;
4. preregister each bounded live experiment.

The implementation agent must **not generate or inspect blind holdout bodies**. Holdout is independently owned outside this repository; development sees only schema/version/count/hash/attestation metadata. It is revealed/run once after full DEV P0 PASS and complete methodology freeze.

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

For Revision 2, a separate frozen DEV annotation adds method-neutral APPROVE-validity Requirements using stable `PredicateIdentity`、`DIRECT_ATOM | ALL_OF`、governing obligation identity、required proof roles、three-state entailment、unsupported-logic labels and deterministic contradiction impact. Human display text is not the matching key. This additive annotation does not change existing required/forbidden refs or expected outcomes and is never exposed to production compiler paths.

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

### Independent Requirement Coverage

Report Stage-1A omission count、per-obligation receipt completion、APPLICABLE/NOT_APPLICABLE/INDETERMINATE confusion、coverage-only true recovery、coverage false candidates and reconciled Requirement recall/precision. Coverage must demonstrate material recovery without recreating old-critic false blocks.

### Entailment Calibration

Report a full `ENTAILED_TRUE | ENTAILED_FALSE | INDETERMINATE` confusion matrix by `OBLIGATION_APPLICABILITY | PREDICATE_STATE` target. Ambiguous evidence forced into binary truth or governing policy counted as factual state proof is a failure.

### Deterministic Proof Materiality

Score model binding candidates separately from Stage-4 selected proof. Canonical critical recall/precision is computed over selected proofs; model-authored importance text is never the canonical label.

### Source and Contradiction Coverage

Report manifest completeness status、eligible inventory size、partition count、receipt/union completion、hard-limit blocks and cross-partition contradiction recall. A partial inventory is never included as a completed pass.

### Interpretation-Policy Mutation

Mutate each materially used authority/outcome/classification/source-selection/proof/partition/logic/predicate/decision-class policy and SourceSetManifest revision. Accepted Decisions must enter deterministic stale/revalidation flow.

### Stable Semantic Proof Selection

For paired semantic paraphrases, requirement semantic IDs and Runtime critical edge sets must match 100% when structured semantics/context are identical.

### Compilation Determinism

Same validated draft → identical canonical graph.

Target: **100%**.

## Model variance protocol

Run live-model cases multiple times.

Recommended:

- 3 runs/case for 30-case variance subset;
- report mean and worst-run critical recall;
- persist model name, temperature/config, prompt version.

## Blind generalization holdout

The product owner or an independent evaluator owns at least 60 balanced cases outside the development repository and agent workspace. The implementation Codex cannot see case bodies、source wording、ground truth、generator seed or per-file plaintext hashes before freeze. Development receives only schema version、counts/distribution、evaluator version、aggregate/encrypted hash、ownership attestation and reveal protocol.

After full 120-case DEV passes every P0 row, freeze code commit、prompts、schemas、policy bundle、dependency lock、runner/evaluator and metric hashes. The independent owner then reveals/runs the holdout once. DEV and HOLDOUT are reported separately. Any subsequent method change invalidates this holdout as blind evidence and requires a newly held set; the revealed cases cannot become tuning data for the same acceptance claim.

## Baselines

Primary three-arm comparison:

1. **Document-level dependency baseline** — every document read becomes critical.
2. **Reasoner-only (Option A)** — frozen single-pass baseline; never the final architecture.
3. **Old critic pipeline** — frozen K3 legacy baseline; no further tuning and no Runtime eligibility.
4. **New requirement-centred pipeline (Option B Revision 2)** — complete SourceSet/policy context、Requirement Decomposition、independent governing-obligation coverage、deterministic reconciliation、Evidence Binding、coverage-preserving Independent Contradiction、deterministic proof/completeness and Acceptance Gate.

The primary Option A/B-legacy/Option B-new comparison uses the same frozen 30-case stratified subset, tasks, sources, provider/model settings, and metric implementation. Architecture-specific prompt/schema/call topology is an explicit experimental variable and must be reported with stage calls, latency, tokens, and cost.

Requirement/coverage/proof-role/three-state-entailment metrics apply only to the new architecture and are `N/A` for legacy arms. Three-arm headline deltas use only metrics defined identically across all arms; C-only diagnostics remain separate.

Proposal-union refs, accepted canonical refs, accepted compilation coverage, and Runtime mutation outcomes are distinct metrics. NOT_ACCEPTED cases are not counted as Runtime stale escapes; accepted-only mutation rates always disclose their denominators.

For v2, report candidate binding metrics separately from deterministic selected-proof and accepted `DecisionJustification` metrics. A minimal proof slice is not allowed to erase unaccepted/unselected ground-truth dependencies from the coverage denominator.

## Paired prompt-injection evaluation

Each clean/injected pair keeps governing semantics constant and measures:

- stable Requirement suppression/addition;
- selected critical evidence coverage delta;
- contradiction suppression or impact downgrade;
- expected outcome/disposition flip;
- accepted-only stale escape/unnecessary invalidation delta;
- illegal authority/ref/policy edge rate.

P0 requires zero requirement/contradiction suppression、zero outcome/disposition flips、zero illegal authority and no mutation-quality regression. “Injected ref was not canonical” alone is insufficient.

The benchmark should demonstrate why the compiler adds value beyond “ask Gemini to list citations”.

## Deliverable

Generate a machine-readable report plus a short human summary suitable for the hackathon repo and architecture discussion.
