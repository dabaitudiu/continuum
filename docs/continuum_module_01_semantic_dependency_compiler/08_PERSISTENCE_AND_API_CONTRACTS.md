# 08 — Persistence and API Contracts

## Status

The persistence/API replacement below is Revision-5 design-only and awaits product-owner review after Revision 4 was rejected. Existing v1 records remain readable and immutable. Any replacement uses an explicit `pipeline_version` and cannot silently reinterpret `CriticReview` as new stage outputs.

## Persistence entities

Source identity entities remain unchanged:

- `SourceArtifact`
- `SourceRevision`
- `ParsedRepresentation`
- `SourceFragment`

The replacement stores immutable records across enterprise-world、compiler-policy and compiler-derived namespaces, plus signed authoritative-registry and request-input envelopes. Proposal/entity inputs reference but are not members of their input world snapshot. Required records include：

- `DecisionProposalRecord` / `ProposalOutcomeBindingRecord` / `DecisionEntityContextRecord`
- `GovernedObservationRecord` / `GovernedObservationSetRecord` / `GovernedReadViewRecord`
- `UpstreamDecisionRequirementRecord` / `UpstreamDecisionBindingRecord`
- `CompilationRequest`
- `CompilationAttemptRecord` / retry-lineage records
- `CompilerPolicyBundleRecord`
- `PolicyUsageTraceRecord`
- `SourceUniverseSnapshotRecord`
- `RuleNormalizationManifestRecord` / per-fragment accounting receipt
- `SourceSetManifestRecord`
- `CoverageBoundaryGuardRecord` / `GoverningRuleSetGuardRecord` / `EvidenceEligibilityGuardRecord` / `ContradictionEligibilityGuardRecord`
- `RequirementTemplateResolutionRecord` / `RequirementInstantiationReceiptRecord`
- `RegisteredCrossPredicateConstraintRecord` / `ConstraintEvaluationReceiptRecord`
- `ApplicabilityJustificationRecord`
- `EffectiveRequirementSetRecord`
- `EvidenceCoveragePlanRecord` / `EvidenceCoverageReceiptRecord` / `FragmentEvidenceObservationRecord`
- `EvidenceBindingCandidateSetRecord`
- `ProofSelectedEvidenceBindingSetRecord`
- `SelectedProofVerificationRequestRecord` / `SelectedProofVerificationReceiptRecord`
- `ContradictionCoveragePlanRecord` / `ContradictionCoverageReceiptRecord` / `FragmentSemanticObservationRecord`
- `ContradictionSetRecord`
- `RequirementAssessmentSetRecord`
- `UnsupportedLogicFindingRecord`
- `UnsupportedPredicateFindingRecord`
- `TemporalValidityGuardRecord`
- `DecisionValidityEnvelopeRecord`
- `SemanticChangeSetRecord` / `ChangeSetRangeProofRecord` / `DecisionIrrelevanceCertificateRecord` / `AuthorizationReceiptRecord`（Runtime/Drift-owned interface records）
- `DecisionJustificationRecord` for accepted APPROVE/DENY only;
- `CompilerFindingRecord`
- `CompilationResultRecord`
- per-stage `ModelInvocationRecord` / ledger settlement linkage.

Every stage record includes request ID, pipeline/schema/prompt version, input hash, output hash, created time, execution status, and model metadata when applicable. No hidden chain-of-thought is stored.

```text
CompilationAttemptRecord
  attempt_id / request_id / attempt_number
  retry_of_attempt_id?
  started_at / ended_at
  run_status
  result_class
  failure_code? / retryability?
  model_invocation_ids[]
  ledger_reservation_ids[] / settlement_ids[]
  actual_input/output/cache_read/cache_write tokens
  settled_cost
  partial_output_refs[]                       # audit_only=true
  attempt_hash
```

A retry always creates a new attempt ID、fresh budget reservation and full stage execution from immutable trusted inputs. It cannot import partial semantic/model output from the failed attempt. Request-level business disposition remains null until one correctly executed semantic attempt completes；exhausted retries leave the request FAILED/BLOCKED, never DENY/REVIEW。

## Result and stage trace

`CompilationResultRecord` contains:

```text
run_status: IN_PROGRESS | COMPLETED | BLOCKED | FAILED
result_class: INPUT_REJECTION | EXECUTION_FAILURE | SEMANTIC_RESULT
business_disposition?
input_rejection_code? / execution_failure_code? / retryability?
pipeline_version
compiler_version
validation_policy_version
decision_proposal_ref / hash / producer_id / producer_version / unchanged outcome
proposal_outcome_binding_ref / hash / policy_ref
decision_entity_context_ref / hash
governed_observation_set_ref / hash / executable_read_view_hash
upstream_decision_bindings[] / exact upstream envelope hashes[]
compiler_policy_bundle_ref / hash
input_world_snapshot_id / source_universe_snapshot_id / compiler_policy_snapshot_id
rule_normalization_manifest_ref / hash / coverage_status
policy_usage_trace[]
source_set_manifest_ref / hash / coverage_status
executed_stages[]
requirement_templates[] / instantiation_receipts[]
constraint_evaluation_receipts[]
applicability_justifications[]
effective_requirements[]
evidence_coverage_plan / receipts[] / fragment_observations[]
evidence_binding_candidates[]
proof_selected_evidence_bindings[]
selected_proof_verification_requests[] / receipts[]
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
GOVERNED_OBSERVATIONS_VALIDATED
DECISION_PROPOSAL_AND_ENTITY_CONTEXT_VALIDATED
UPSTREAM_DECISIONS_BOUND
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
SELECTED_PROOFS_INDEPENDENTLY_VERIFIED
COMPLETENESS_COMPUTED
TEMPORAL_VALIDITY_ENVELOPE_COMPUTED
GATE_EVALUATED
CANONICALIZED
```

Each expected stage is surfaced as `DONE`, `SKIPPED_INPUT_REJECTION`, `FAILED_EXECUTION`, `BLOCKED`, or `NOT_REACHED`. Consumers must not infer execution or business disposition from a missing findings list。

## API boundary

The generic compiler surface remains internal and capability-protected. Runtime acceptance retains a distinct capability.

### `POST /api/compiler/requests`

Create a request referencing an already immutable/signed domain-agent `DecisionProposal` and `DecisionEntityContext`, bound to mission/work item、exact enterprise world snapshot/revision、active policy bundle and universe/coverage decision class. Domain outcome mapping is resolved/validated from versioned policy；the compiler endpoint cannot author or alter the proposal outcome/entities.

### `POST /api/compiler/{request_id}/run`

Run the selected versioned pipeline. Product wiring may select only the approved replacement after cutover. Benchmark tooling may explicitly select `reasoner-only` or `old-critic`；those modes cannot call Runtime acceptance.

### `GET /api/compiler/{request_id}`

Return immutable proposal/request、governed observation/upstream bindings、policy/manifest provenance、Evidence/contradiction/selected-proof verification receipts、stage outputs/findings、temporal/epoch envelope、exact trace、run status、result class、business disposition if any，and canonical output only if accepted. UI/API must never render input rejection/execution failure as business DENY。

### `POST /api/compiler/{request_id}/accept`

Runtime-only. Accept only an immutable `ACCEPTED` result from the approved production pipeline；benchmark baseline modes are ineligible even if their historical disposition says accepted.

The current draft/compile routes may remain as versioned v1 readers during migration, but there is no replacement-to-v1 fallback.

## Internal interfaces

```text
GovernedObservationValidator.validate(set, executable_read_view)
DecisionProposalValidator.validate(proposal, entity_context, observations, world, policies)
UpstreamDecisionBinder.bind(proposal, decision_class_contract, current_runtime_view)
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
DeterministicProofSelector.provisionally_select(requirements, bindings, upstream_bindings, contradictions, policies)
SelectedProofVerifier.verify(exact_selected_fragment_target_entity_claim)
DeterministicProofSelector.reselect_and_finalize(verification_receipts)
DeterministicRequirementCompleteness.compute(requirements, selected_proofs, contradictions)
TemporalValidityCompiler.compile(selected_proofs, applicability, policies, trusted_clock)
DeterministicProposalGate.evaluate(proposal, ...) -> disposition + DecisionJustification? + DecisionValidityEnvelope?
Canonicalizer.compile(...)
RuntimeAcceptanceService.accept(...)
SemanticEpochPublisher.publish(change_set, successor_snapshots, read_fence)
SemanticEpochAuthorizationBarrier.authorize(decision, envelope, intervening_change_sets, upstream_decisions, trusted_clock)
```

`FragmentEvidenceInterpreter`、independent `FragmentContradictionObserver` and narrow `SelectedProofVerifier` are the only replacement model interfaces. The verifier receives one isolated exact selected proof tuple and returns only a three-valued verdict. Validators/reducers return immutable objects；deterministic selectors/Gate own upstream binding、applicability/materiality/impact/disposition；only Runtime acceptance/barrier mutates or authorizes canonical state.

## Transaction boundary

Compiler stage persistence and Runtime Decision commit remain separate transactions linked by immutable compilation ID/hash. A compilation may be semantically accepted yet fail Runtime acceptance because mission revision or world snapshot advanced.

Runtime acceptance revalidates:

- `pipeline_version` is the approved active production pipeline;
- disposition is `ACCEPTED`;
- canonical graph/hash are present and immutable;
- proposal/producer/outcome/entity/observation context、exact upstream Decision envelopes、expected mission revision、governed enterprise world/universe/policy snapshots and derived envelope exactly match;
- universe/normalization/selection/Evidence/contradiction coverage was complete and all selected applicability/policy/coverage guards exist as validity-bearing provenance;
- trusted time is before exclusive `authorization_not_after`; upstream Decisions remain current/VALID；every intervening executable ChangeSet is hash-chain complete and non-intersecting；
- executable epoch pointer/upstream hashes remain unchanged through the same conditional commit as inbox/idempotency、business side effect and audit/outbox。

`PublishEpochTxn` is a separate serializable transaction: verify predecessor、seal/publish one complete ChangeSet、advance one owner-scope executable pointer and expose one governed read fence. It requires **zero Decision-row writes**. Decision status/index/certificate records are lazy projections. `AuthorizeSideEffectTxn` reads/checks the exact envelope and ChangeSet range；relevant intersection or a concurrent pointer change denies/retries before side-effect commit。

## Events

Suggested versioned events:

```text
compiler.requested
compiler.governed_observations.validated
compiler.decision_proposal.validated
compiler.upstream_decisions.bound
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
compiler.selected_proofs.verified
compiler.completeness.assessed
compiler.temporal_validity.compiled
compiler.unsupported_logic.detected
compiler.unsupported_predicate.detected
compiler.model_protocol.failed
compiler.input.rejected
compiler.execution.failed
compiler.run.blocked
compiler.review.required
compiler.compilation.accepted
compiler.compilation.rejected
runtime.semantic_epoch.reserved
runtime.semantic_changeset.sealed
runtime.semantic_epoch.published
runtime.decision.irrelevance_certified
runtime.decision.authorization_denied_upstream
runtime.decision.authorization_denied_relevant_change
runtime.decision.authorization_denied_expired
runtime.decision.authorization_denied_epoch_gap
```

These are compiler events. Only successful Runtime acceptance emits final `decision.created` and graph mutation events.
