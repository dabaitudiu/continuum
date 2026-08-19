# 04 — Intermediate Representation (IR)

## Status and versioning

The product owner approved Option B's direction but rejected the first concrete specification and Revision 2. These Revision-3 contracts are **design contracts under review, not implemented contracts**. Their normative definitions are in [15_REPLACEMENT_ARCHITECTURE.md](15_REPLACEMENT_ARCHITECTURE.md).

Implemented `DecisionDraft`、`ClaimDraft`、`DependencyRef`、`CriticProposal` and `CriticReview` remain immutable v1 legacy types for persisted evidence and ablation replay. They are not production fallbacks and cannot be silently reinterpreted as Revision-3 objects.

## Design goal

The IR separates ten questions:

1. Which authoritative source universe was attested and completely enumerated?
2. Did normalization account for every source fragment without silent omission?
3. Which subset/rule/contradiction boundaries were selected?
4. Which stable semantic gates does Stage 1 propose?
5. Which material obligations and applicability conditions does the independent pass find?
6. Which determinate bindings prove APPLICABLE or NOT_APPLICABLE?
7. Which exact source fragments entail/refute/leave each gate indeterminate?
8. Which propositions conflict across the complete inventory?
9. Which validated bindings/guards become canonical CRITICAL dependencies?
10. Does deterministic outcome/disposition logic permit canonicalization?

## Trusted context objects

### `CompilerPolicyBundle`

Contains refs into a separate `CompilerPolicySnapshot` for universe/selection、normalization/review、authority/outcome、decision class、predicate catalog、proof、partition and supported logic. All materially used refs become Runtime validity provenance.

Every deterministic semantics component emits a `PolicyUsageTrace` containing the exact policy ref and rule keys it read. An unregistered config read is `UNVERSIONED_POLICY_INPUT` and prevents canonicalization.

### `SourceUniverseSnapshot` / `RuleNormalizationManifest` / `SourceSetManifest`

The authoritative registry snapshot envelope enumerates owner scope、namespaces、artifact revisions and watermarks；it is a trusted input root, not a member of the world it enumerates. Normalization and selection are compiler-derived artifacts that bind exact input snapshot/policy IDs and never join that input world。Only a complete validated chain may proceed。

### `PredicateIdentity`

```text
predicate_catalog_id              resolved from the policy bundle; not a SourceRef
predicate_code
subject: entity_type + stable entity_id
comparator: IS | EQUALS | EXISTS | NOT_EXISTS
typed_object
scope_qualifiers
temporal_qualifiers
```

Canonical semantic identity is derived from these structured fields. Human-readable proposition text is excluded from hashes and ordering.

## Model proposal objects

### `DecisionAnalysisProposal`

```text
request_id
decision_type
proposed_outcome
requirements[]
rationale_summary
```

The outcome remains untrusted. The model never receives benchmark expected outcomes.

### `Requirement`

```text
requirement_id                 deterministic after validation
predicate_identity?            DIRECT_ATOM only
proposition_display            non-authoritative
kind
expected_state: TRUE | FALSE
logical_form: DIRECT_ATOM | ALL_OF
child_requirement_ids[]
required_proof_roles[]          contract-derived
origin: DECOMPOSITION | COVERAGE_PASS | BOTH
governing_obligation_keys[]
rationale_summary
```

Requirements are necessary semantic propositions, never refs. Nested ALL_OF is flattened、deduped and sorted by semantic identity. Unsupported OR/threshold/exception/quantified forms cannot enter the effective set.

### `RequirementCoverageObservation` / `RequirementCoverageCandidate`

```text
RequirementCoverageObservation
  governing_obligation_key
  normalized_rule_id
  proposed_applicability: APPLICABLE | NOT_APPLICABLE | INDETERMINATE
  applicability_binding_candidates[]
  applicability_summary
  requirement_candidate_local_ids[]

RequirementCoverageReceipt
  partition_id
  source_set_manifest_id / rule_normalization_manifest_id
  processed_obligation_keys[]
  output_hash
```

The deterministic plan records expected partitions and obligation membership. Every representable obligation maps to typed Requirement candidates even when proposed N/A. Model applicability is advisory；Stage 1C emits only `ApplicabilityProofCandidate`。Stage 3 checks independent conflicts and Stage 4 finalizes `ApplicabilityJustification` only when APPLICABLE (all true) or NOT_APPLICABLE (stable false guard) remains determinate；otherwise it fails closed。

Final `ApplicabilityJustification` records normalized rule/obligation IDs、applicability predicate semantic keys/expected states、selected current bindings、material policy refs、input world snapshot and a stable proof key. Both APPLICABLE and acceptance-participating NOT_APPLICABLE are validity-bearing；mutable selected facts can stale the Decision in either direction。

```text
candidate_local_id
predicate_identity
proposition_display
expected_state
logical_form
child_predicate_semantic_keys[]
governing_obligation_key
governing_source_refs[]
applicability_summary
detected_logic_form
unsupported_logic_kind?
```

The independent coverage model receives no Stage-1 output and returns an applicability observation plus typed Requirement candidates for every representable governing obligation, regardless of proposed applicability. Refs must already exist in the validated manifest；`UNKNOWN_SOURCE_REQUIRED` is unrepresentable.

### `EvidenceBindingCandidate`

```text
binding_local_id
requirement_id
source_ref
semantic_role
entailment_target: NORMALIZED_OBLIGATION | REQUIREMENT_PREDICATE
entailment: ENTAILED_TRUE | ENTAILED_FALSE | INDETERMINATE
normalized_value?
counterfactual_summary
```

There is deliberately no model-authored `materiality` field. Normalized obligation validity、applicability predicate truth and business predicate truth are separate contracts. A policy requirement proves neither that it applies to this entity nor that the required state is satisfied.

### `ContradictionObservation`

```text
observation_local_id
partition_id
requirement_id
source_ref
entailment_target
entailment
normalized_value?
proposition_display
model_severity_advisory
```

The dedicated pass emits independent observations for a coverage-proven source partition. Model severity is advisory only.

## Deterministically validated objects

### `EvidenceBinding`

```text
candidate
authority_class
proof_eligibility: ELIGIBLE | INELIGIBLE
eligibility_finding_codes[]
selected_proof_role?
proof_role: SELECTED_PROOF | UNSELECTED_SUPPORT | ANALYSIS_ONLY
canonical_materiality: CRITICAL | SUPPORTING | NONE
```

Canonical materiality is derived after proof selection. A selected necessary proof is CRITICAL even if model prose called it supporting. `INDETERMINATE` cannot be selected.

### `Contradiction`

```text
candidate                         deterministic global join
resolution: LHS_PRECEDES | RHS_PRECEDES | UNRESOLVED
precedence_policy_ref
precedence_rule_key?
affected_root_requirement_ids[]
lhs_proof_eligibility
rhs_proof_eligibility
deterministic_impact: VALIDITY_CRITICAL | NON_BLOCKING
impact_finding_codes[]
```

Impact derives from requirement-to-root reachability、proof eligibility and authority state. Model severity cannot downgrade a blocking conflict.

### `ContradictionCoveragePlan` / `Receipt`

Records hard limits、every eligible source ref、deterministic partitions、input hashes and per-partition processed refs/output hashes. Global reduction cannot run as complete unless receipt union exactly covers the plan. Partial coverage is `RUN_BLOCKED`.

### `RequirementAssessment`

```text
requirement_id
status: SATISFIED | UNSATISFIED | CONTRADICTED | INSUFFICIENT_EVIDENCE
selected_proof_binding_ids[]
supporting_binding_ids[]
contradiction_ids[]
support_paths[][]
blocking_requirement_ids[]
finding_codes[]
assessment_summary
```

Deterministic completeness computes one assessment per **reconciled effective Requirement**. Missing required roles or only indeterminate evidence produce `INSUFFICIENT_EVIDENCE`. ALL_OF uses the fixed conjunction truth table.

### `UnsupportedLogicResult`

Contains exact governing ref、normalized rule key、unsupported logic kind、affected predicate keys and detector. Its disposition is `REJECTED_UNSUPPORTED_LOGIC`; canonical output is absent.

### `UnsupportedPredicateResult`

Contains the exact governing fragment、normalized rule/obligation key、frozen predicate catalog ref and unrepresentable semantic shape. Its disposition is `REJECTED_UNSUPPORTED_PREDICATE`；model code invention and compiler omission are forbidden.

## Result envelope

```text
ReplacementCompilationResult
  request_id / compilation_id
  run_status: IN_PROGRESS | COMPLETED | BLOCKED | FAILED
  disposition?
  compiler_policy_bundle
  source_universe_snapshot
  rule_normalization_manifest
  policy_usage_trace[]
  source_set_manifest
  requirement_proposals[]
  requirement_coverage_observations[] / receipts[]
  applicability_proof_candidates[]
  applicability_justifications[]
  coverage_candidates[]
  effective_requirements[]
  evidence_binding_candidates[]
  evidence_bindings[]
  contradiction_coverage_plan / receipts[]
  contradictions[]
  requirement_assessments[]
  unsupported_logic_findings[]
  unsupported_predicate_findings[]
  coverage_boundary / rule_set / contradiction_eligibility guards[]
  decision_justification?
  canonical_decision?
  canonical_claims[] / canonical_edges[]
  findings[] / executed_stages[]
  pipeline/compiler/schema versions
  compilation_hash?
  stage_model_metadata[]
```

`BLOCKED` and `FAILED` have no semantic disposition or canonical output. Non-accepted semantic results have no canonical graph. Only an accepted APPROVE/DENY contains a deterministic `DecisionJustification` and Runtime-eligible graph.

## Decision justification and canonical mapping

```text
DecisionJustification
  outcome_class
  selected_root_requirement_ids[]
  selected_requirement_ids[]
  selected_proof_binding_ids[]
  selected_policy_refs[]
  compiler_derived_artifact_ids[]
  applicability_justification_ids[]
  selective_coverage_dependency_keys[]
  derivation_binding_hash
  semantic_proof_key
  selection_rule
```

APPROVE selects all necessary root closures. DENY selects one failed proof by a stable tuple over predicate semantic key、selected source identities and normalized topology. Proposition display text、case/domain/local IDs and iteration order are excluded.

Selected evidence maps Source → DIRECT Claim；ALL_OF maps Claim → Claim；roots map Claim → Decision。Selected applicability facts map to applicability guard Claims；material policy and selective boundary/rule/eligibility guards map through `DecisionInterpretation`。Full manifests remain audit derivation, preventing unrelated inventory changes from staling every Decision。

## Determinism requirement

Given the same validated structured semantics、bindings、universe/normalization/selection chain、policy bundle and input snapshots, canonical applicability、ordering、proof selection、materiality、contradiction impact、disposition、graph、hash and trace must be identical. Paraphrasing `proposition_display` alone must change none of them.

No hidden chain-of-thought is persisted.
