# 06 — Validation, Acceptance, and Canonicalization

## Fixed validation order

Structural integrity is checked immediately after the stage that introduces a typed object. Semantic uncertainty is preserved until the relevant semantic stage; source/context incompleteness blocks execution rather than being mistaken for semantic rejection.

### S0G/S0I/S0D Proposal/entity/observation/upstream、universe、normalization、policy and source coverage

Validate one complete `GovernedObservationSet` against the executable `GovernedReadView`、immutable `DecisionProposal` producer/version/outcome/world/semantic-sequence/component-epoch binding、trusted `DecisionEntityContext` roles，and every exact contract-required upstream Decision ID/compilation/envelope/status/outcome/sequence/epoch. Unversioned/future/mixed/bypass material reads are input rejection；a successor never auto-rebinds an upstream role. Then validate registry/universe、normalization and SourceSet hashes. Every deterministic semantic component emits `PolicyUsageTrace`；an interpretation-affecting config read outside the bundle is execution failure `UNVERSIONED_POLICY_INPUT`. Derived manifests bind these inputs but cannot be members of the input world snapshot。

Unavailable/incomplete universe、normalization or selection before model calls yields `RUN_BLOCKED`. Post-call malformed/partial partition coverage yields `RUN_FAILED` with no proposal-admission disposition. A model cannot override either；silent parser omission cannot become `NO_GOVERNING_RULE`。

Validate normalized governing-rule forms/templates and catalog representability. Unsupported logic yields `REJECTED_UNSUPPORTED_LOGIC`；material unregistered/absence/cross-predicate semantics yields `REJECTED_UNSUPPORTED_PREDICATE`（including `ABSENCE_PROOF_NOT_SUPPORTED_P0` / `UNSUPPORTED_CROSS_PREDICATE_RELATION_P0`）；unparsed/review-required normalization blocks. No result has canonical output。

### S1 Requirement template/entity instantiation and accounting

Resolve only independently approved reusable governing/decision-class `RequirementTemplate`s. Deterministically instantiate `PredicateIdentity` from catalog role constraints and `DecisionEntityContext`；models cannot supply entity IDs. Normalize DIRECT_ATOM/ALL_OF、flatten conjunctions、dedupe/sort child semantic IDs and reject cycles.

Instantiation receipts must account exactly once for every normalized obligation/template and retain every representable Requirement/applicability target until Stage 4. Missing/duplicate/conflicting template or illegal entity role fails closed. There is no Stage-1 Requirement/outcome model and no reconciliation between competing authorities. `UNKNOWN_SOURCE_REQUIRED`、invented codes/entities and proposal rationale as authority are not schema members。

### S2 Evidence/applicability coverage and binding integrity

Validate `EvidenceCoveragePlan` hard limits、complete eligible-fragment union、target/eligibility hashes and one fragment wrapper per assigned ref. There is no top-K field. Preflight capacity blocks；post-call missing/truncated/malformed/partial receipts fail execution. Check ref existence、manifest/scope/currentness、source role、already-instantiated target key、exact subject/object entity equality、predicate compatibility、target and three-state entailment。

The model supplies no canonical materiality. `INDETERMINATE` is valid analysis but proof-ineligible. A faithfully observed historical/wrong-entity proposition may be semantic proof-ineligible；a model-emitted unauthorized/fabricated/out-of-plan ref is execution failure. Fuzzy repair is forbidden.

### S3 Contradiction inventory and impact

Validate `ContradictionCoveragePlan` executable hard limits、eligibility matrix、deterministic partition membership and every receipt. Receipt union must equal the full eligible inventory with one fragment wrapper per ref and matching target/input hashes. Preflight hard/dense capacity blocks；post-call missing/truncated/malformed/partial partitions fail execution。

Globally join actual determinate opposing matches only by the same stable predicate/entity/target and overlapping normalized scope/time, including applicability/cross-partition pairs. Cross-predicate invariants are deterministic registered decision-class/template evaluators and never enter this join. Validate refs、truth/value、scope、time and authority. Apply versioned precedence. Derive `VALIDITY_CRITICAL | NON_BLOCKING` from reachability、proof eligibility and resolution state；the model schema has no severity field。

### S4A/S4V/S4R/S4B Proof selection、disposition-critical verification and completeness

First reduce provisional applicability/direct contradictions/precedence and freeze deterministic candidate order. Stage 4V independently verifies every preselected model-interpreted enterprise proof/applicability role and both material sides of each provisional `VALIDITY_CRITICAL` direct conflict. Only `CONFIRMED` proof/guards can become `CRITICAL`，and only two confirmed model sides can form a blocking `Contradiction`. `REFUTED` removes the observation and S4R reselects/re-reduces；`INDETERMINATE` proof candidates are skipped, while a critical conflict side becomes typed semantic uncertainty rather than confirmed contradiction. Verifier failure is execution failure, not a verdict. Contract-required upstream roles accept only exact current/VALID `UpstreamDecisionBinding`s and become first-class Decision→Decision critical edges。

Compute one assessment per template-instantiated effective Requirement. DIRECT_ATOM uses selected role evidence and contradiction state. ALL_OF uses the fixed conjunction truth table. Verify every time-sensitive selected proof/applicability fact against immutable source time fields and emit finite `[valid_from, valid_until)` guards. Do not demand redundant direct evidence on derived Requirements.

### S5 Outcome and acceptance

Compute an evidence-supported `APPROVE | DENY | REVIEW` validation class from root assessments and compare it with immutable domain-agent `DecisionProposal`. Mismatch rejects/reviews **proposal admission**；it cannot generate a substitute Decision or business outcome. Admitted APPROVE/DENY emits a `DecisionJustification` plus sequence-bound `DecisionValidityEnvelope` and exact unchanged proposal outcome。

## Result-class boundaries

Malformed/unauthorized signed proposal/entity/upstream/observation/world inputs are completed `INPUT_REJECTION` records with no proposal-admission disposition and may skip semantic stages。

Model schema/enum/local-ID/forbidden target/ref/entity、receipt/protocol/verifier/transport failures and internal invariants are `RUN_FAILED` `EXECUTION_FAILURE` records with no proposal-admission disposition. A retry is a new immutable attempt and never reuses partial output。

## Execution-blocking conditions

- credential/provider/budget unavailable before calls;
- source universe `INCOMPLETE | UNKNOWN`;
- normalization `INCOMPLETE | REVIEW_REQUIRED` or missing accounting/review receipt;
- hard limits cannot represent the complete Evidence/applicability or contradiction inventory;
- complete plan exceeds declared context/dense/verification capacity before calls.

These return `RUN_BLOCKED`, not a semantic disposition. Partial contradiction results are never published as complete.

## Non-structural semantic conditions

- domain-agent rationale omits a governing assumption but trusted template instantiation still supplies it；
- a required proof role has no determinate evidence;
- entailment is `INDETERMINATE`;
- applicability is `INDETERMINATE` or conflicts with its candidate proof;
- current authorities conflict;
- supplied proposal outcome disagrees with evidence;
- an exact required upstream Decision is STALE/SUPERSEDED/INVALID；
- selected candidate is REFUTED/INDETERMINATE and no confirmed alternative remains；
- a material side of a provisional critical direct conflict is INDETERMINATE and becomes semantic uncertainty；
- a structurally valid fragment match refers to the wrong entity；
- model advisory materiality text is wrong.

Once representable effective Requirements exist, these must reach contradiction、proof/completeness and Gate as applicable. They do not justify an early structural exit.

## Canonicalization

Canonicalization runs only after `ACCEPTED`.

### Stable proof mapping

- every selected RequirementAssessment maps to a Claim identified from stable predicate/topology semantics, not display text;
- every independently confirmed Stage-4 `SELECTED_PROOF` binding maps SourceFragment → DIRECT Claim through validity-bearing `SUPPORTED_BY | GOVERNED_BY`;
- every selected ALL_OF relationship maps prerequisite Claim → derived Claim;
- selected roots map Claim → Decision;
- exact `DecisionProposal`、`DecisionEntityContext` and `GovernedObservationSet` bind the canonical Decision and unchanged outcome；
- exact `UpstreamDecisionBinding` maps upstream Decision → downstream Decision through `REQUIRES | AUTHORIZES[CRITICAL]`；
- selected applicability facts map through APPLICABLE/NOT_APPLICABLE guard Claims；
- materially used policy refs and selective boundary/rule-set/Evidence/contradiction-eligibility guards map through a `DecisionInterpretation` Claim；full manifests remain audit-only derivation;
- `TemporalValidityGuard` and `DecisionValidityEnvelope` bind trusted expiry/semantic sequence/component epoch to side-effect authorization；
- IDs、ordering and edge dedupe are deterministic.

### Canonical materiality

Only deterministic proof-selected bindings、applicability guards and materially participating interpretation/coverage guards produce `critical=true` edges. Model prose/labels and whole-manifest inventory never control canonical materiality. Unselected support remains provenance-only or analysis-only.

`CONTRADICTED_BY` is not a direct Runtime invalidation relation and cannot be the sole provenance of an accepted DENY. Counterevidence selected to justify DENY uses an invalidation-bearing support/governance edge.

### No silent semantic repair

Canonicalizer cannot:

- invent or near-match a ref;
- add an omitted Requirement or binding;
- use model materiality/severity as canonical truth;
- resolve authority by model preference;
- coerce unsupported logic;
- invent/ignore an unsupported predicate or trust unproved NOT_APPLICABLE;
- infer `NOT_EXISTS`/absence from an empty retrieval or cross-bind entities；
- add redundant direct edges;
- change the proposed outcome;
- trust an unverified selected enterprise proof or silently substitute an upstream successor；
- omit policy/applicability/selective-coverage provenance that materially produced the justification.

## Stable DENY proof selection

APPROVE includes all necessary root closures. DENY selects one failed proof using:

```text
failure_class_priority from versioned proof policy
→ failed DIRECT predicate_semantic_key
→ sorted selected proof SourceRef identities
→ flattened canonical path topology hash
```

Human-readable proposition text is excluded. Semantically equivalent paraphrases over the same structured predicates/context must select the same Runtime critical dependency set.

## Compilation hash

The Revision-6 hash covers at least:

- exact proposal/producer/outcome/entity/observation/upstream context plus stable predicate/template semantics;
- exact `CompilerPolicyBundle` refs/hashes;
- exact world/universe/policy input IDs and derived `RuleNormalizationManifest`/`SourceSetManifest`/partition receipts;
- requirement template/obligation instantiation receipts、validated applicability justifications and selective guards;
- Evidence plan/partitions/fragment observations/receipts、validated bindings、purpose-typed disposition-critical verification receipts、proof selection and canonical materiality;
- contradiction plan/fragment observations/receipts、provisional global pairs、both-side verification/semantic uncertainty、precedence and deterministic impact;
- RequirementAssessments、validation class、unchanged proposal comparison and DecisionJustification;
- temporal guards、authorization horizon、validated semantic sequence/component epoch and DecisionValidityEnvelope；
- canonical refs/source hashes、world snapshot and stage trace;
- pipeline/compiler/schema/prompt/model metadata required for provenance.

Changing only `proposition_display` must not change the semantic proof key or canonical edge set.

## Runtime invalidation contract

Accepted graph validity depends on proposal/entity/observation/upstream binding、independently confirmed enterprise evidence/applicability facts、temporal horizon and interpretation/coverage semantics. Relevant revisions of upstream Decision status/envelope、selected fragments、catalog/entity roles/normalization/selection/authority/outcome/proof policies、governing rule set or Evidence/contradiction eligibility enter invalidation through stable guards. A full manifest hash change caused only by irrelevant inventory/supporting content must not automatically stale all Decisions。

`RuntimeAcceptanceService` rechecks exact proposal/entity/observation/upstream/mission/world/universe/policy snapshots、derived envelope、selective guards、trusted clock and compilation hash. `PublishEpochTxn` assigns the next contiguous semantic sequence and publishes the complete ChangeSet/read fence without Decision-row fan-out. `ReauthorizeForExecutionTxn` checks every ordered intervening ChangeSet、upstream currentness/horizons and unchanged sequence pointer while atomically transitioning the Side Effect Ledger intent to `EXECUTING` or stale-cancelled. The external call is outside the transaction and uses idempotency/reconciliation. Runtime—not the compiler/model—owns status transitions、sequences/epochs、certificates and authorization.
