# 04 — Intermediate Representation (IR)

## Status and versioning

The product owner approved Option B's direction but rejected concrete specifications through Revision 3. These Revision-4 contracts are **design contracts under review, not implemented contracts**. Their normative definitions are in [15_REPLACEMENT_ARCHITECTURE.md](15_REPLACEMENT_ARCHITECTURE.md).

Implemented `DecisionDraft`、`ClaimDraft`、`DependencyRef`、`CriticProposal` and `CriticReview` remain immutable v1 legacy types for persisted evidence and ablation replay. They are not production fallbacks and cannot be silently reinterpreted as Revision-4 objects.

## Design goal

The IR separates twelve questions:

1. Which authoritative source universe was attested and completely enumerated?
2. Did normalization account for every source fragment without silent omission?
3. Which immutable domain-agent proposal/entity bindings are being validated?
4. Which subset/rule/Evidence/contradiction boundaries were selected?
5. Which trusted reusable templates deterministically instantiate the stable semantic gates?
6. Did template/obligation accounting cover them exactly once?
7. Did Evidence/applicability discovery process every eligible fragment without top-K omission?
8. Which determinate bindings prove APPLICABLE or NOT_APPLICABLE?
9. Which propositions conflict across the independent complete inventory?
10. Which validated bindings/guards become canonical CRITICAL dependencies and when do they expire?
11. Does deterministic proposal-validation logic permit canonicalization without outcome substitution?
12. Which semantic epoch makes that Decision safe to authorize?

## Trusted context objects

### `CompilerPolicyBundle`

Contains refs into a separate `CompilerPolicySnapshot` for universe/selection、normalization/review、authority/outcome mapping、decision class、predicate/entity catalog、Evidence/contradiction coverage、proof、temporal validity、semantic epoch and supported logic. All materially used refs become Runtime validity provenance.

Every deterministic semantics component emits a `PolicyUsageTrace` containing the exact policy ref and rule keys it read. An unregistered config read is `UNVERSIONED_POLICY_INPUT` and prevents canonicalization.

### `SourceUniverseSnapshot` / `RuleNormalizationManifest` / `SourceSetManifest`

The authoritative registry snapshot envelope enumerates owner scope、namespaces、artifact revisions and watermarks；it is a trusted input root, not a member of the world it enumerates. Normalization and selection are compiler-derived artifacts that bind exact input snapshot/policy IDs and never join that input world。Only a complete validated chain may proceed。

### `DecisionProposal` / `DecisionEntityContext`

The immutable proposal records producing agent ID/version、decision type、unchanged proposed outcome、entity context、world snapshot、time and hash. A deterministic `ProposalOutcomeBinding` maps that exact outcome through versioned policy into the gate vocabulary；the source value is never rewritten. `DecisionEntityContext` maps contract roles such as REQUESTER/RESOURCE/VENDOR to stable typed entities. Models receive already-instantiated predicate keys and cannot supply entity IDs。

### `PredicateIdentity`

```text
predicate_catalog_id              resolved from the policy bundle; not a SourceRef
predicate_code
subject: entity_type + stable entity_id
comparator: IS | EQUALS | EXISTS
typed_object
scope_qualifiers
temporal_qualifiers
```

Canonical semantic identity is derived from these structured fields. Human-readable proposition text is excluded from hashes and ordering.

P0 does not support `NOT_EXISTS` or any `EXISTS + expected_state=FALSE` Requirement. A material absence obligation yields typed `ABSENCE_PROOF_NOT_SUPPORTED_P0`；explicit signed boolean state remains supported。

## Requirement authority and analysis objects

### `RequirementTemplate`

Approved normalized rules and decision-class contracts are the only Requirement authorities. A reusable template declares stable predicate catalog key、subject/object roles、typed context bindings、expected state、DIRECT/ALL_OF topology、applicability templates and required proof roles. It cannot contain case ID、fixture/source revision or benchmark outcome。

### `Requirement`

```text
requirement_id                 deterministic after validation
requirement_template_id
predicate_identity?            DIRECT_ATOM only
proposition_display            non-authoritative
kind
expected_state: TRUE | FALSE
logical_form: DIRECT_ATOM | ALL_OF
child_requirement_ids[]
required_proof_roles[]          contract-derived
authority_kind / authority_ref
governing_obligation_keys[]
entity_context_id
instantiation_receipt_hash
```

Requirements are necessary semantic propositions, never refs. Stage 1 deterministically instantiates them from trusted templates/entity roles；there is no Requirement-invention model. Nested ALL_OF is flattened、deduped and sorted by semantic identity. Unsupported OR/threshold/exception/quantified forms cannot enter the effective set.

### `RequirementInstantiationReceipt` / `ApplicabilityJustification`

```text
RequirementInstantiationReceipt
  governing_obligation_key
  normalized_rule_id
  requirement_template_ids[] / instantiated_requirement_ids[]
  applicability_predicate_semantic_keys[]
  entity_context_id / context_hash
  accounting_status
  receipt_hash
```

Every trusted template/obligation is accounted exactly once, including applicability targets for obligations that may later prove N/A. Stage 3 checks independent conflicts and Stage 4 finalizes `ApplicabilityJustification` only when APPLICABLE（all true）or NOT_APPLICABLE（stable determinate false guard）remains proved；otherwise it fails closed。

Final `ApplicabilityJustification` records normalized rule/obligation IDs、applicability predicate semantic keys/expected states、selected current bindings、material policy refs、input world snapshot and a stable proof key. Both APPLICABLE and acceptance-participating NOT_APPLICABLE are validity-bearing；mutable selected facts can stale the Decision in either direction。

### `EvidenceCoveragePlan` / `FragmentEvidenceObservation` / `Receipt`

The deterministic no-top-K plan records all Requirement/applicability targets、all certified eligible fragments、catalog eligibility matrix、bounded partitions and hashes. Each assigned ref yields exactly one `FragmentEvidenceObservation` with actual `matched_predicates[]`; an empty array means processed/no match reported. Receipts prove exact fragment processing, not model semantic correctness. Over-limit、dense、truncated or partial coverage is `RUN_BLOCKED`。

### `EvidenceBindingCandidate`

```text
binding_local_id
requirement_id? / normalized_obligation_key?
target_predicate_semantic_key
source_ref
semantic_role
entailment_target: REQUIREMENT_PREDICATE | APPLICABILITY_PREDICATE
entailment: ENTAILED_TRUE | ENTAILED_FALSE | INDETERMINATE
normalized_subject / normalized_object
normalized_value?
asserted_valid_from / asserted_valid_until
```

There is deliberately no model-authored `materiality` field. Governing authority is deterministically bound from the approved rule/template；applicability and business state remain separate model-interpreted targets. Target/entity/ref/time/role validation precedes proof eligibility；model timestamps do not directly create temporal guards。

### `FragmentSemanticObservation`

```text
partition_id
source_ref
matched_predicates[]            empty = processed/no relevant proposition reported
  match_local_id
  target_predicate_semantic_key
  requirement_id? / normalized_obligation_key?
  entailment_target
  entailment / normalized_subject / normalized_object / normalized_value
  asserted_valid_from / asserted_valid_until
```

The dedicated pass emits one fragment wrapper with only actual matches. Complete receipts plus global join discover cross-partition conflicts in O(fragments+actual matches) output；the schema has no model severity field。

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

Records executable hard limits、every eligible ref、target/entity descriptors、deterministic eligibility matrix/partitions、input hashes and per-partition fragment wrappers/actual-match counts. Global reduction cannot run as complete unless receipt union exactly covers the plan. Partial/dense/over-limit coverage is `RUN_BLOCKED`.

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

Deterministic completeness computes one assessment per **template-instantiated effective Requirement**. Missing required roles or only indeterminate evidence produce `INSUFFICIENT_EVIDENCE`. ALL_OF uses the fixed conjunction truth table.

### `TemporalValidityGuard` / `DecisionValidityEnvelope`

A finite guard binds each time-sensitive selected proof/applicability result to trusted clock policy、`evaluated_at`、`[valid_from, valid_until)` and expiry semantics. The validity envelope binds proposal/entity/compilation hashes、semantic epoch vector、minimum exclusive `authorization_not_after` and every selective dependency key. Runtime denies authorization at expiry or across an uncovered newer epoch；a scheduler is not the safety barrier。

### `UnsupportedLogicResult`

Contains exact governing ref、normalized rule key、unsupported logic kind、affected predicate keys and detector. Its disposition is `REJECTED_UNSUPPORTED_LOGIC`; canonical output is absent.

### `UnsupportedPredicateResult`

Contains the exact governing fragment、normalized rule/obligation key、frozen predicate catalog ref and unrepresentable semantic shape. Its disposition is `REJECTED_UNSUPPORTED_PREDICATE`；model code invention and compiler omission are forbidden.

## Result envelope

```text
ReplacementCompilationResult
  proposal / entity_context / compilation_id
  proposal_outcome_binding
  run_status: IN_PROGRESS | COMPLETED | BLOCKED | FAILED
  disposition?
  compiler_policy_bundle
  source_universe_snapshot
  rule_normalization_manifest
  policy_usage_trace[]
  source_set_manifest
  requirement_templates[] / requirement_instantiation_receipts[]
  applicability_justifications[]
  effective_requirements[]
  evidence_coverage_plan / receipts[] / fragment_observations[]
  evidence_binding_candidates[]
  evidence_bindings[]
  contradiction_coverage_plan / receipts[] / fragment_semantic_observations[]
  contradictions[]
  requirement_assessments[]
  unsupported_logic_findings[]
  unsupported_predicate_findings[]
  coverage_boundary / rule_set / evidence_eligibility /
    contradiction_eligibility guards[]
  temporal_validity_guards[]
  decision_validity_envelope?
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
  proposal_id / proposal_hash / producing_agent_id / version
  proposal_outcome_binding_hash
  entity_context_id / context_hash
  outcome_class
  selected_root_requirement_ids[]
  selected_requirement_ids[]
  selected_proof_binding_ids[]
  selected_policy_refs[]
  compiler_derived_artifact_ids[]
  applicability_justification_ids[]
  selective_coverage_dependency_keys[]
  temporal_validity_guard_ids[]
  decision_validity_envelope_id
  derivation_binding_hash
  semantic_proof_key
  selection_rule
```

APPROVE selects all necessary root closures. DENY selects one failed proof by a stable tuple over predicate semantic key、selected source identities and normalized topology. Proposition display text、case/domain/local IDs and iteration order are excluded.

Selected evidence maps Source → DIRECT Claim；ALL_OF maps Claim → Claim；roots map Claim → Decision。Proposal/entity context validate the exact Decision；selected applicability facts map to applicability guard Claims；material policy and selective boundary/rule/Evidence/contradiction eligibility guards map through `DecisionInterpretation`；temporal/envelope guards authorize only while current. Full manifests remain audit derivation, preventing unrelated inventory changes from staling every Decision。

## Determinism requirement

Given the same proposal/entity context、validated structured semantics、bindings、universe/normalization/selection chain、policy bundle、clock instant/epoch and input snapshots, canonical applicability、ordering、proof selection、materiality、contradiction impact、disposition、graph、hash and trace must be identical. Paraphrasing display/rationale text alone must change none of them.

No hidden chain-of-thought is persisted.
