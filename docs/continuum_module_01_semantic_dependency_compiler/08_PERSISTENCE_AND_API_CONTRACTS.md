# 08 — Persistence and API Contracts

## Status

The persistence/API replacement below is Revision-4 design-only and awaits product-owner review after Revision 3 was rejected. Existing v1 records remain readable and immutable. Any replacement uses an explicit `pipeline_version` and cannot silently reinterpret `CriticReview` as new stage outputs.

## Persistence entities

Source identity entities remain unchanged:

- `SourceArtifact`
- `SourceRevision`
- `ParsedRepresentation`
- `SourceFragment`

The replacement stores immutable records across enterprise-world、compiler-policy and compiler-derived namespaces, plus signed authoritative-registry and request-input envelopes. Proposal/entity inputs reference but are not members of their input world snapshot. Required records include：

- `DecisionProposalRecord` / `ProposalOutcomeBindingRecord` / `DecisionEntityContextRecord`
- `CompilationRequest`
- `CompilerPolicyBundleRecord`
- `PolicyUsageTraceRecord`
- `SourceUniverseSnapshotRecord`
- `RuleNormalizationManifestRecord` / per-fragment accounting receipt
- `SourceSetManifestRecord`
- `CoverageBoundaryGuardRecord` / `GoverningRuleSetGuardRecord` / `EvidenceEligibilityGuardRecord` / `ContradictionEligibilityGuardRecord`
- `RequirementTemplateResolutionRecord` / `RequirementInstantiationReceiptRecord`
- `ApplicabilityJustificationRecord`
- `EffectiveRequirementSetRecord`
- `EvidenceCoveragePlanRecord` / `EvidenceCoverageReceiptRecord` / `FragmentEvidenceObservationRecord`
- `EvidenceBindingCandidateSetRecord`
- `ProofSelectedEvidenceBindingSetRecord`
- `ContradictionCoveragePlanRecord` / `ContradictionCoverageReceiptRecord` / `FragmentSemanticObservationRecord`
- `ContradictionSetRecord`
- `RequirementAssessmentSetRecord`
- `UnsupportedLogicFindingRecord`
- `UnsupportedPredicateFindingRecord`
- `TemporalValidityGuardRecord`
- `DecisionValidityEnvelopeRecord`
- `SemanticChangeSetRecord` / `DecisionIrrelevanceCertificateRecord`（Runtime/Drift-owned interface records）
- `DecisionJustificationRecord` for accepted APPROVE/DENY only;
- `CompilerFindingRecord`
- `CompilationResultRecord`
- per-stage `ModelInvocationRecord` / ledger settlement linkage.

Every stage record includes request ID, pipeline/schema/prompt version, input hash, output hash, created time, execution status, and model metadata when applicable. No hidden chain-of-thought is stored.

## Result and stage trace

`CompilationResultRecord` contains:

```text
run_status: IN_PROGRESS | COMPLETED | BLOCKED | FAILED
disposition?
pipeline_version
compiler_version
validation_policy_version
decision_proposal_ref / hash / producer_id / producer_version / unchanged outcome
proposal_outcome_binding_ref / hash / policy_ref
decision_entity_context_ref / hash
compiler_policy_bundle_ref / hash
input_world_snapshot_id / source_universe_snapshot_id / compiler_policy_snapshot_id
rule_normalization_manifest_ref / hash / coverage_status
policy_usage_trace[]
source_set_manifest_ref / hash / coverage_status
executed_stages[]
requirement_templates[] / instantiation_receipts[]
applicability_justifications[]
effective_requirements[]
evidence_coverage_plan / receipts[] / fragment_observations[]
evidence_binding_candidates[]
proof_selected_evidence_bindings[]
contradiction_coverage_plan / receipts[] / fragment_semantic_observations[]
contradictions[]
requirement_assessments[]
unsupported_logic_findings[]
unsupported_predicate_findings[]
selective_coverage_guard_keys[]
temporal_validity_guards[]
decision_validity_envelope?
derivation_binding_hash
decision_justification? only when ACCEPTED
findings[]
canonical graph fields only when ACCEPTED
compilation_hash only when ACCEPTED
```

Executed stages use the replacement vocabulary:

```text
POLICY_BUNDLE_VALIDATED
DECISION_PROPOSAL_AND_ENTITY_CONTEXT_VALIDATED
SOURCE_UNIVERSE_VALIDATED
RULE_NORMALIZATION_VALIDATED
SOURCE_SET_COVERAGE_VALIDATED
REQUIREMENTS_INSTANTIATED
REQUIREMENT_TEMPLATES_ACCOUNTED
EVIDENCE_PARTITIONS_COMPLETED
EVIDENCE_COVERAGE_VALIDATED
BINDINGS_VALIDATED
CONTRADICTION_PARTITIONS_COMPLETED
CONTRADICTION_COVERAGE_VALIDATED
CONTRADICTIONS_REDUCED
PROOFS_SELECTED
COMPLETENESS_COMPUTED
TEMPORAL_VALIDITY_ENVELOPE_COMPUTED
GATE_EVALUATED
CANONICALIZED
```

Each expected stage is surfaced as `DONE`, `SKIPPED_STRUCTURAL_TERMINATION`, `BLOCKED`, or `NOT_REACHED`. Consumers must not infer execution from a missing findings list.

## API boundary

The generic compiler surface remains internal and capability-protected. Runtime acceptance retains a distinct capability.

### `POST /api/compiler/requests`

Create a request referencing an already immutable/signed domain-agent `DecisionProposal` and `DecisionEntityContext`, bound to mission/work item、exact enterprise world snapshot/revision、active policy bundle and universe/coverage decision class. Domain outcome mapping is resolved/validated from versioned policy；the compiler endpoint cannot author or alter the proposal outcome/entities.

### `POST /api/compiler/{request_id}/run`

Run the selected versioned pipeline. Product wiring may select only the approved replacement after cutover. Benchmark tooling may explicitly select `reasoner-only` or `old-critic`；those modes cannot call Runtime acceptance.

### `GET /api/compiler/{request_id}`

Return immutable proposal/request、policy/manifest provenance、Evidence/contradiction coverage receipts、stage outputs/findings、temporal/epoch envelope、exact trace、run status、semantic disposition and canonical output if accepted. Partial output must be visibly incomplete and can never appear under a completed coverage state.

### `POST /api/compiler/{request_id}/accept`

Runtime-only. Accept only an immutable `ACCEPTED` result from the approved production pipeline；benchmark baseline modes are ineligible even if their historical disposition says accepted.

The current draft/compile routes may remain as versioned v1 readers during migration, but there is no replacement-to-v1 fallback.

## Internal interfaces

```text
DecisionProposalValidator.validate(proposal, entity_context, world, policies)
ContextAssembler.assemble(proposal, entity_context, request)
PolicyBundleValidator.validate(bundle, policy_snapshot)
SourceUniverseValidator.validate(universe_snapshot, world_snapshot)
RuleNormalizer.account(universe_snapshot, policy_bundle) -> RuleNormalizationManifest
SourceSetAssembler.assemble(request, universe, normalization, policy_bundle)
SourceCoverageValidator.validate(manifests, exact_inputs)
RequirementTemplateResolver.resolve(normalization, decision_class_contract)
RequirementInstantiator.instantiate(templates, entity_context)
RequirementAccountingValidator.validate(manifests, templates, receipts)
EvidenceCoveragePlanner.plan(manifest, requirements, applicability_targets, limits)
FragmentEvidenceInterpreter.observe(partition, target_descriptors)
EvidenceCoverageReducer.validate_and_bind(plan, receipts, fragment_observations)
ContradictionCoveragePlanner.plan(manifest, target_descriptors, limits)
FragmentContradictionObserver.observe(partition, target_descriptors)
ContradictionReducer.validate_and_reduce(plan, receipts, fragment_observations)
DeterministicProofSelector.finalize_applicability_and_select(requirements, bindings, contradictions, policies)
DeterministicRequirementCompleteness.compute(requirements, selected_proofs, contradictions)
TemporalValidityCompiler.compile(selected_proofs, applicability, policies, trusted_clock)
DeterministicProposalGate.evaluate(proposal, ...) -> disposition + DecisionJustification? + DecisionValidityEnvelope?
Canonicalizer.compile(...)
RuntimeAcceptanceService.accept(...)
SemanticEpochAuthorizationBarrier.authorize(decision, envelope, current_epoch, certificates, trusted_clock)
```

`FragmentEvidenceInterpreter` and independent `FragmentContradictionObserver` are the only replacement model interfaces. They receive pre-instantiated target/entity keys and complete bounded partitions, not outcome/Requirement-authoring authority. Validators/reducers return immutable objects；deterministic selectors/Gate own applicability/materiality/impact/disposition；only Runtime acceptance/barrier mutates or authorizes canonical state.

## Transaction boundary

Compiler stage persistence and Runtime Decision commit remain separate transactions linked by immutable compilation ID/hash. A compilation may be semantically accepted yet fail Runtime acceptance because mission revision or world snapshot advanced.

Runtime acceptance revalidates:

- `pipeline_version` is the approved active production pipeline;
- disposition is `ACCEPTED`;
- canonical graph/hash are present and immutable;
- proposal/producer/outcome/entity context、expected mission revision、enterprise world/universe/policy snapshots and derived envelope exactly match;
- universe/normalization/selection/Evidence/contradiction coverage was complete and all selected applicability/policy/coverage guards exist as validity-bearing provenance;
- trusted time is before exclusive `authorization_not_after` and semantic epoch is equal or fully covered by deterministic irrelevance certificates；
- inbox/idempotency and atomic audit/outbox requirements hold.

## Events

Suggested versioned events:

```text
compiler.requested
compiler.decision_proposal.validated
compiler.source_universe.validated
compiler.rule_normalization.validated
compiler.source_set.validated
compiler.requirements.instantiated
compiler.requirement_templates.accounted
compiler.evidence_partition.completed
compiler.evidence_coverage.validated
compiler.bindings.validated
compiler.contradiction_partition.completed
compiler.contradictions.reduced
compiler.proofs.selected
compiler.completeness.assessed
compiler.temporal_validity.compiled
compiler.unsupported_logic.detected
compiler.unsupported_predicate.detected
compiler.structural.failed
compiler.run.blocked
compiler.review.required
compiler.compilation.accepted
compiler.compilation.rejected
runtime.semantic_epoch.reserved
runtime.decision.irrelevance_certified
runtime.semantic_epoch.published
runtime.decision.authorization_denied_expired
runtime.decision.authorization_denied_epoch_gap
```

These are compiler events. Only successful Runtime acceptance emits final `decision.created` and graph mutation events.
