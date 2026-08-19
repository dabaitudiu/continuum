# 04 — Intermediate Representation (IR)

## Status and versioning

The product owner approved Option B's direction but rejected the first concrete v2 specification. These Revision-2 contracts are **design contracts under review, not implemented contracts**. Their normative definitions are in [15_REPLACEMENT_ARCHITECTURE.md](15_REPLACEMENT_ARCHITECTURE.md).

Implemented `DecisionDraft`、`ClaimDraft`、`DependencyRef`、`CriticProposal` and `CriticReview` remain immutable v1 legacy types for persisted evidence and ablation replay. They are not production fallbacks and cannot be silently reinterpreted as Revision-2 objects.

## Design goal

The IR separates seven questions:

1. Which source/policy universe was completely considered?
2. Which stable semantic gates does Stage 1 propose?
3. Which material governing obligations does an independent coverage pass find?
4. Which exact source fragments entail, refute, or leave each gate indeterminate?
5. Which source propositions conflict across the complete inventory?
6. Which validated bindings are selected as proof and therefore canonical CRITICAL dependencies?
7. Does deterministic outcome/disposition logic permit canonicalization?

## Trusted context objects

### `CompilerPolicyBundle`

Contains canonical versioned refs for authority precedence/classification、outcome semantics、source selection、decision-class contract、predicate catalog、proof selection、partitioning、supported logic and any additional configuration that can change `DecisionJustification`. All materially used refs become Runtime validity provenance.

Every deterministic semantics component emits a `PolicyUsageTrace` containing the exact policy ref and rule keys it read. An unregistered config read is `UNVERSIONED_POLICY_INPUT` and prevents canonicalization.

### `SourceSetManifest`

Content-addressed manifest of the world snapshot、coverage boundary、included/excluded artifacts、retrieval versions、governing/contradiction-eligible refs、coverage status、explicit `declared_complete_for_decision_class` and partition-plan hash. Only a trusted, validated complete declaration may proceed to normal compilation.

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
  governing_source_refs[]
  applicability: APPLICABLE | NOT_APPLICABLE | INDETERMINATE
  applicability_summary
  candidate_local_id?          required iff APPLICABLE

RequirementCoverageReceipt
  partition_id
  manifest_hash
  processed_obligation_keys[]
  output_hash
```

The deterministic plan records expected partitions and obligation membership. Across receipts, every normalized governing obligation in the manifest must be accounted exactly once. Missing/duplicate/unexpected coverage is not an empty successful result；INDETERMINATE applicability cannot normally accept.

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

The independent coverage model receives no Stage-1 output and returns an applicability observation per governing obligation plus typed candidates for APPLICABLE obligations. Refs must already exist in the validated manifest; `UNKNOWN_SOURCE_REQUIRED` is unrepresentable.

### `EvidenceBindingCandidate`

```text
binding_local_id
requirement_id
source_ref
semantic_role
entailment_target: OBLIGATION_APPLICABILITY | PREDICATE_STATE
entailment: ENTAILED_TRUE | ENTAILED_FALSE | INDETERMINATE
normalized_value?
counterfactual_summary
```

There is deliberately no model-authored `materiality` field. Governing authority entails whether an obligation applies；state/authorization/satisfaction evidence entails the business predicate. A policy requirement is not factual proof that the condition is satisfied.

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

## Result envelope

```text
CompilationResultV2
  request_id / compilation_id
  run_status: IN_PROGRESS | COMPLETED | BLOCKED | FAILED
  disposition?
  compiler_policy_bundle
  policy_usage_trace[]
  source_set_manifest
  requirement_proposals[]
  requirement_coverage_observations[] / receipts[]
  coverage_candidates[]
  effective_requirements[]
  evidence_binding_candidates[]
  evidence_bindings[]
  contradiction_coverage_plan / receipts[]
  contradictions[]
  requirement_assessments[]
  unsupported_logic_findings[]
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
  source_set_manifest_ref
  semantic_proof_key
  selection_rule
```

APPROVE selects all necessary root closures. DENY selects one failed proof by a stable tuple over predicate semantic key、selected source identities and normalized topology. Proposition display text、case/domain/local IDs and iteration order are excluded.

Selected evidence maps Source → DIRECT Claim; ALL_OF maps Claim → Claim; roots map Claim → Decision. Selected policy and manifest artifacts map through a validity-bearing `DecisionInterpretation` Claim to the Decision. This preserves transitive support and lets revisions of enterprise evidence **or deterministic interpretation policies** stale the old Decision.

## Determinism requirement

Given the same validated structured semantics、bindings、complete source manifest、policy bundle and world snapshot, canonical ordering、proof selection、materiality、contradiction impact、disposition、graph、hash and trace must be identical. Paraphrasing `proposition_display` alone must change none of them.

No hidden chain-of-thought is persisted.
