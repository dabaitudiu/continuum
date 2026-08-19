# 09 — Evaluation Benchmark: Continuum Dependency Bench

## Goal

Avoid evaluating the compiler only on the one scenario it was designed around.

## Option B evaluation amendment

The current 120-case corpus remains the visible DEV set and its existing refs、outcomes、contradictions、mutations and thresholds are immutable. The product owner approved Option B's direction but rejected concrete specifications through Revision 3. No individual-case tuning or full paid rerun is authorized.

Before any replacement prompt/schema/logic implementation, only method-blind DEV annotation design may occur:

1. freeze `DEV Requirement Annotation v1` independently of replacement output;
2. per case include immutable proposal outcome/expected validation class、entity-role bindings、Requirement template IDs、stable PredicateIdentity/state/topology、governing/applicability keys、expected Evidence/contradiction matches、temporal expectations and unsupported logic/predicate/absence labels;
3. freeze corpus/catalog/schema refs、annotation hashes、annotator/adjudicator identities and method-blind attestation in an append-only manifest；corrections require a new version + audit diff;
4. prove production code and prompts cannot import/read DEV ground truth;
5. preregister each bounded live experiment.

The implementation agent must **not generate or inspect blind holdout bodies**. Holdout is independently owned outside this repository；development sees only schema/version/count/hash/attestation metadata. It is revealed/run once only after OpenAI full DEV **and Gemini full DEV**, then complete methodology freeze；Gemini is primary blind lane.

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
- cases where only one narrow clause is relevant;
- cross-entity adversaries（Alice/Bob、Vendor A/B）；
- time passage beyond a proof horizon with no source revision；
- enterprise/rule/policy/catalog changes racing an authorization；
- material absence obligations that must be typed unsupported in P0；
- new in-scope cases using frozen reusable catalogs/templates without semantic-schema edits。

## Ground truth

Each case defines:

```text
required_critical_refs
acceptable_supporting_refs
forbidden_or_irrelevant_refs
expected_outcome_constraints
decision_proposal_outcome / expected_validation_class
expected_entity_role_bindings
expected_requirement_template_ids
blocking_contradictions
expected_staleness_after_mutation
expected_temporal_expiry_behavior
expected_semantic_epoch_authorization_behavior
```

Ground truth is manually authored and version-controlled.

For Revision 4, `DEV Requirement Annotation v1` is method-blind and frozen before replacement outputs. It includes proposal validation class、entity roles、template IDs、stable predicates/state/topology、governing/applicability keys、Evidence/contradiction matches、temporal expectations and unsupported labels. Human display/rationale text is not the matching key. It is evaluator-only；corrections publish a new version and invalidate same-version claims rather than editing history。

The domain-agent fixture supplies an immutable proposal outcome from the registered decision-class vocabulary. Replacement model stages do not author outcome/Requirements and need not receive the proposal outcome；they receive only instantiated target descriptors and assigned source fragments. They never receive ground-truth validation class/allowed outcomes。

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

### Requirement Authority and Evidence Coverage

Report template/obligation accounting、effective Requirement recall/precision、domain-rationale omissions recovered by deterministic templates、Evidence/applicability fragment/receipt completion、semantic match recall/precision/no-match false negatives、APPLICABLE/NOT_APPLICABLE/INDETERMINATE confusion and bidirectional applicability stale recall。

### Entailment Calibration

Report a full `ENTAILED_TRUE | ENTAILED_FALSE | INDETERMINATE` matrix separately for `APPLICABILITY_PREDICATE | REQUIREMENT_PREDICATE`。Ambiguous evidence forced binary、policy used as current fact or unproved N/A is a failure。

### Deterministic Proof Materiality

Score model binding candidates separately from Stage-4 selected proof. Canonical critical recall/precision is computed over selected proofs; model-authored importance text is never the canonical label.

### Source、Evidence and Contradiction Coverage

Report universe attestation、fragment normalization accounting、SourceSet selection、Evidence/contradiction eligible inventory、fragment wrappers/actual matches、calls/input/output tokens versus v4 maxima、partitions/receipts、hard-limit/dense blocks and cross-partition recall. A partial inventory is never a completed pass。

### Interpretation-Policy Mutation

Mutate each materially used catalog/entity-role/normalization/selection/authority/outcome/proof policy、governing rule set、applicability fact and Evidence/contradiction-eligibility guard. Relevant Decisions must stale；irrelevant inventory/supporting changes must not automatically stale. Report `coverage_induced_unnecessary_invalidation_rate` with denominator。

### Proposal、Entity、Temporal and Epoch Safety

Report proposal validation/disposition confusion、canonical outcome-substitution attempts（target 0）、cross-entity false matches/canonicalizations（canonical target 0）、temporal-guard horizon completeness、authorization at/beyond exact expiry（escape target 0）、and side-effect authorization across enterprise/new-rule/policy/catalog epoch races without a complete irrelevance certificate chain（escape target 0）。

### K6 / Manual Specification Generality

Per domain report predicate count、normalized-rule-template count、decision-class template count、case-specific predicate/rule/dependency-template count（all target 0）、cases requiring catalog/schema change、`schema_reuse_rate_on_new_in_scope_cases`（target 1.00 under frozen semantics）and `new_case_success_without_semantic_schema_modification`. A schema edit keyed to a known/revealed case invalidates that generality claim。

### Stable Semantic Proof Selection

For paired semantic paraphrases, requirement semantic IDs and Runtime critical edge sets must match 100% when structured semantics/context are identical.

### Compilation Determinism

Same validated proposal/entity/snapshots/clock/epoch → identical canonical graph/envelope.

Target: **100%**.

## Model variance protocol

Run live-model cases multiple times.

Recommended:

- 3 runs/case for 30-case variance subset;
- report mean and worst-run critical recall;
- persist model name, temperature/config, prompt version.

## Blind generalization holdout

The product owner or an independent evaluator owns at least 60 balanced cases outside the development repository and agent workspace. The implementation Codex cannot see case bodies、source wording、ground truth、generator seed or per-file plaintext hashes before freeze. Development receives only schema version、counts/distribution、evaluator version、aggregate/encrypted hash、ownership attestation and reveal protocol.

After Experiment 6A OpenAI full DEV and 6B Gemini full DEV, Experiment 7 freezes code commit、prompts、schemas、policy bundle、predicate catalog、normalization/selection policies、both model configs、dependency lock、runner/evaluator and metric hashes. Experiment 8 reveals/runs once with Gemini primary and OpenAI optional secondary. Any subsequent method change requires a fresh independent set。

## Baselines

Primary three-arm comparison:

1. **Document-level dependency baseline** — every document read becomes critical.
2. **Reasoner-only (Option A)** — frozen single-pass baseline; never the final architecture.
3. **Old critic pipeline** — frozen K3 legacy baseline; no further tuning and no Runtime eligibility.
4. **New requirement-centred pipeline (Option B Revision 4)** — immutable domain proposal/entity context、authoritative universe + complete normalization、trusted reusable template instantiation、complete Evidence/applicability coverage、scalable independent contradiction、deterministic proof/temporal envelope and proposal Gate.

The primary Option A/B-legacy/Option B-new comparison uses the same frozen 30-case stratified subset, tasks, sources, provider/model settings, and metric implementation. Architecture-specific prompt/schema/call topology is an explicit experimental variable and must be reported with stage calls, latency, tokens, and cost.

Template/entity/Evidence coverage/proof-role/three-state-entailment/temporal/epoch metrics apply only to the new architecture and are `N/A` for legacy arms. Three-arm headline deltas use only metrics defined identically across all arms；C-only diagnostics remain separate.

Proposal-union refs, accepted canonical refs, accepted compilation coverage, and Runtime mutation outcomes are distinct metrics. NOT_ACCEPTED cases are not counted as Runtime stale escapes; accepted-only mutation rates always disclose their denominators.

For the replacement, report fragment search wrappers/matches、candidate bindings、applicability proof、selected proof and accepted `DecisionJustification` separately. A minimal proof slice cannot erase missed ground-truth semantics from the Evidence/Requirement denominator。

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
