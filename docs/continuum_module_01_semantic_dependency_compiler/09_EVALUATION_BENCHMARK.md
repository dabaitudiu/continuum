# 09 — Evaluation Benchmark: Continuum Dependency Bench

## Goal

Avoid evaluating the compiler only on the one scenario it was designed around.

## Option B evaluation amendment

The current 120-case corpus remains the visible DEV set and its existing refs、outcomes、contradictions、mutations and thresholds are immutable. The product owner approved Option B's direction but rejected concrete specifications through Revision 4. No individual-case tuning or full paid rerun is authorized.

Before any replacement prompt/schema/logic implementation, only method-blind DEV annotation design may occur:

1. freeze `DEV Requirement Annotation v1` independently of replacement output;
2. per case include immutable proposal outcome/expected validation class/admission disposition、entity-role and governed-observation bindings、required upstream Decision bindings、Requirement template IDs、stable PredicateIdentity/state/topology、governing/applicability keys、expected Evidence/direct-contradiction/registered-constraint matches、disposition-critical verification truth/semantic uncertainty、temporal sequence/epoch expectations and unsupported labels;
3. freeze corpus/catalog/schema refs、annotation hashes、annotator/adjudicator identities and method-blind attestation in an append-only manifest；corrections require a new version + audit diff;
4. prove production code and prompts cannot import/read DEV ground truth;
5. preregister each bounded live experiment.

The implementation agent must **not generate or inspect blind holdout bodies**. Holdout is independently owned outside this repository；development sees only schema/version/count/hash/attestation metadata. It is revealed/run once only after OpenAI full DEV **and Gemini full DEV**, then complete methodology freeze；Gemini is primary blind lane.

The exact freeze, A/B/N0/N1 ablation, progression, and stop rules are normative in [15_REPLACEMENT_ARCHITECTURE.md](15_REPLACEMENT_ARCHITECTURE.md).

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
- D42→D50→activation upstream Decision dependencies、stale/supersession/non-rewrite；
- governed-read future/mixed/bypass observation attempts；
- model schema/ref/transport failures that must not become business rejection；
- primary-interpreter false proof with independent verifier confirm/refute/reselection；
- direct same-predicate contradiction、registered cross-predicate constraint and unsupported relation categories；
- operational capacity、dense/context/verification blocks retained in denominators；
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
expected_governed_observation_bindings
expected_upstream_decision_bindings
expected_requirement_template_ids
blocking_contradictions
registered_cross_predicate_constraints
unsupported_cross_predicate_relations
disposition_critical_verification_truth
semantic_uncertainty_truth
expected_staleness_after_mutation
expected_temporal_expiry_behavior
expected_semantic_epoch_authorization_behavior
```

Ground truth is manually authored and version-controlled.

For Revision 6, `DEV Requirement Annotation v1` remains method-blind and frozen before replacement outputs. It includes proposal business outcome、expected admission disposition、entity/observation/upstream roles、template IDs、stable predicates/state/topology、governing/applicability keys、Evidence/direct-contradiction/registered-constraint matches、purpose-typed verification/uncertainty truth、temporal sequence/epoch expectations and unsupported labels. Human display/rationale text is not the matching key. It is evaluator-only；corrections publish a new version and invalidate same-version claims rather than editing history。

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

### Direct Contradiction Detection Recall

Direct opposing observations over the same normalized predicate/entity/target flagged. Registered cross-predicate constraint violations and unsupported unregistered relations are separate scored categories and never enter this denominator.

Target P0: **>= 0.90**.

Revision-6 verification metrics use method-blind pair/case truth and publish raw numerators/denominators：

```text
confirmed_contradiction_precision =
  confirmed predicted blocking direct pairs matching truth /
  all confirmed predicted blocking direct pairs

false_contradiction_block_rate =
  non-blocking-truth cases whose admission was blocked by a confirmed contradiction /
  all cases with no expected blocking direct contradiction

human_review_false_positive_rate =
  non-review-truth cases emitted as NEEDS_HUMAN_REVIEW /
  all cases whose expected validation class is not REVIEW
```

An `INDETERMINATE` contradiction-side receipt is counted under semantic uncertainty/human-review metrics, never as a confirmed predicted contradiction. N0→N1 reports paired safety deltas plus additional calls、input/output tokens、latency and settled cost on identical primary outputs。

### Requirement Authority and Evidence Coverage

Report template/obligation accounting、effective Requirement recall/precision、domain-rationale omissions recovered by deterministic templates、Evidence/applicability fragment/receipt completion、semantic match recall/precision/no-match false negatives、APPLICABLE/NOT_APPLICABLE/INDETERMINATE confusion and bidirectional applicability stale recall。

### Entailment Calibration

Report a full `ENTAILED_TRUE | ENTAILED_FALSE | INDETERMINATE` matrix separately for `APPLICABILITY_PREDICATE | REQUIREMENT_PREDICATE`。Ambiguous evidence forced binary、policy used as current fact or unproved N/A is a failure。

### Deterministic Proof Materiality

Score primary binding candidates、N0 unverified disposition-critical claims and N1 independently verified claims separately. Canonical critical recall/precision is computed only over confirmed N1 proofs；confirmed contradiction precision counts only both-side-confirmed conflicts. Report false-proof acceptance、false contradiction block rate、semantic-uncertainty rate、human-review false-positive rate、reselection/re-reduction success、outcome/stale-safety delta、calls、tokens、latency and settled cost。

### Source、Evidence and Contradiction Coverage

Report universe attestation、fragment normalization accounting、SourceSet selection、Evidence/contradiction eligible inventory、fragment wrappers/actual matches、verification attempts、calls/input/output tokens versus v5 maxima、partitions/receipts、hard-limit/dense/verification blocks and cross-partition recall. A partial inventory is never a completed pass。

### Interpretation-Policy Mutation

Mutate each materially used catalog/entity-role/normalization/selection/authority/outcome/proof policy、governing rule set、applicability fact and Evidence/contradiction-eligibility guard. Relevant Decisions must stale；irrelevant inventory/supporting changes must not automatically stale. Report `coverage_induced_unnecessary_invalidation_rate` with denominator。

### Proposal、Observation、Upstream Decision、Temporal and Epoch Safety

Report proposal-admission/business-outcome rendering confusion、result-class confusion、canonical outcome substitution（target 0）、cross-entity canonicalization（target 0）、governed-read mixed/future/bypass rejection、D→D binding/transitive stale/supersession non-rewrite、temporal expiry escape（target 0）、contiguous semantic-sequence/range/replay correctness、and side-effect authorization-to-`EXECUTING` escape across relevant ChangeSets（target 0）。Epoch publication requires zero Decision-row writes；duplicate logical external effects target 0 and every crash-point reconciliation result is reported。

### Operational Executability

Per provider/model/domain/decision class report raw mission denominators、`successful_compilation_rate_under_supported_limits`（P0 >=0.90）、`context_limit_block_rate`（P0 <=0.10）、blocked/failed/outside-limit counts and median/p95 calls、input/output tokens、latency、settled cost. Every trusted-input-valid attempt remains in resource distributions；blocked missions are never filtered from headline denominators. Numeric p95 ceilings come from the frozen `OperationalLimitProfile`；unset/missing metrics fail the gate。

### K6 / Manual Specification Generality

Per domain report predicate count、normalized-rule-template count、decision-class template count、case-specific predicate/rule/dependency-template count（all target 0）、cases requiring catalog/schema change、`schema_reuse_rate_on_new_in_scope_cases`（target 1.00 under frozen semantics）and `new_case_success_without_semantic_schema_modification`. A schema edit keyed to a known/revealed case invalidates that generality claim。

### Stable Semantic Proof Selection

For paired semantic paraphrases, requirement semantic IDs and Runtime critical edge sets must match 100% when structured semantics/context are identical.

### Compilation Determinism

Same validated proposal/entity/observation/upstream/snapshots、primary+verification outputs、clock/epoch → identical canonical graph/envelope.

Target: **100%**.

## Model variance protocol

Run live-model cases multiple times.

Recommended:

- 3 runs/case for 30-case variance subset;
- report mean and worst-run critical recall;
- persist model name, temperature/config, prompt version.

## Blind generalization holdout

The product owner or an independent evaluator owns at least 60 balanced cases outside the development repository and agent workspace. The implementation Codex cannot see case bodies、source wording、ground truth、generator seed or per-file plaintext hashes before freeze. Development receives only schema version、counts/distribution、evaluator version、aggregate/encrypted hash、ownership attestation and reveal protocol.

After Experiment 6A OpenAI full DEV and 6B Gemini full DEV, Experiment 7 freezes code commit、prompts、schemas、policy bundle、predicate catalog、normalization/selection/verification/operational policies、both model configs、dependency lock、runner/evaluator and metric hashes. Experiment 8 reveals/runs once with Gemini primary and OpenAI optional secondary. Any subsequent method change requires a fresh independent set。

## Baselines

Primary comparison:

1. **Document-level dependency baseline** — every document read becomes critical.
2. **Reasoner-only (Option A)** — frozen single-pass baseline; never the final architecture.
3. **Old critic pipeline** — frozen K3 legacy baseline; no further tuning and no Runtime eligibility.
4. **Revision-6 N0 unverified disposition-critical semantics** — complete new Option-B primary outputs/reducers but no independent verification of selected proof/applicability or contradiction sides；ablation-only。
5. **Revision-6 N1 verified disposition-critical semantics** — governed observations、exact upstream Decisions、complete Evidence/applicability/direct contradiction、purpose-typed independent verification、deterministic admission Gate、ordered ChangeSet authorization and Side Effect Ledger final reauthorization；only production candidate。

The A/B/N0/N1 comparison uses the same frozen 30-case stratified subset、tasks、sources、provider/model settings and metric implementation. N0/N1 reuse identical Evidence/contradiction primary outputs and differ only in verification/removal/reselection/re-reduction. “N” is the new Option-B arm；rejected product Option C remains absent。

Template/entity/observation/upstream/Evidence coverage/proof/three-state-entailment/temporal/epoch metrics apply only to the new architecture and are `N/A` for legacy arms. Cross-arm headline deltas use only common metrics；C-only diagnostics remain separate。

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
