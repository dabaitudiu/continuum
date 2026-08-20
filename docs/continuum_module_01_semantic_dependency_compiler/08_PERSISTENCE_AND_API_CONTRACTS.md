# 08 — Persistence and API Contracts

## Status

The persistence/API replacement below is Revision-7 design-only and awaits product-owner review. P0-1～P0-37 are architecturally accepted and frozen；Revision 7 changes only the P0-38 hash DAG and P0-39 Decision acyclicity boundary. Existing v1 records remain readable and immutable. Any replacement uses an explicit `pipeline_version` and cannot silently reinterpret `CriticReview` as new stage outputs.

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
- `DispositionCriticalVerificationRequestRecord` / `DispositionCriticalVerificationReceiptRecord` / `DispositionCriticalSemanticUncertaintyRecord`
- `ContradictionCoveragePlanRecord` / `ContradictionCoverageReceiptRecord` / `FragmentSemanticObservationRecord`
- `ContradictionSetRecord`
- `RequirementAssessmentSetRecord`
- `UnsupportedLogicFindingRecord`
- `UnsupportedPredicateFindingRecord`
- `TemporalValidityGuardRecord`
- `CompilationCoreRecord`
- `DecisionValidityEnvelopeRecord`
- `DecisionJustificationRecord` / `FinalCompilationRecord`
- `CanonicalDecisionCoreRecord` / `DecisionDependencyAcyclicityReceiptRecord` / `DecisionDependencyGraphHead`（Runtime-owned）
- `SemanticEpochRecord` / `SemanticChangeSetRecord` / `SemanticPublicationReceiptRecord` / `ChangeSetRangeProofRecord` / `DecisionIrrelevanceCertificateRecord` / `AuthorizationReceiptRecord`（Runtime/Drift-owned interface records）
- `SideEffectIntentCoreRecord` / append-only `SideEffectTransitionRecord` / `SideEffectLedgerHead` / external reconciliation records（Runtime Side Effect Ledger-owned）
- `CompilerFindingRecord`
- `CompilationResultRecord`
- per-stage `ModelInvocationRecord` / ledger settlement linkage.

Every stage record includes request ID, pipeline/schema/prompt version, input hash, output hash, created time, execution status, and model metadata when applicable. No hidden chain-of-thought is stored.

```text
CompilationAttemptRecord
  attempt_id: content-addressed ID
  request_id / attempt_number
  retry_of_attempt_id?
  started_at / ended_at
  run_status
  result_class
  failure_code? / retryability?
  model_invocation_ids[]
  ledger_reservation_ids[] / settlement_ids[]
  actual_input/output/cache_read/cache_write tokens
  settled_cost_usd_decimal                    # normalized fixed-scale string, never float
  partial_output_refs[]                       # audit_only=true
  final_record_id / final_record_hash?        # present only for a completed semantic result
  attempt_hash
```

A retry always creates a new attempt、fresh budget reservation and full stage execution from immutable trusted inputs. `CompilationAttemptRecord` is sealed exactly once after that attempt terminates；live progress is non-authoritative telemetry and is not a mutable hash preimage。It cannot import partial semantic/model output from the failed attempt. Request-level proposal-admission disposition remains null until one correctly executed semantic attempt completes；exhausted retries leave the request FAILED/BLOCKED, never admission rejection/review or business DENY/REVIEW。

```text
SideEffectIntentCoreRecord                  # immutable/content-addressed
  side_effect_intent_id
  owner_scope / mission_id / effect_type / normalized_request_hash
  idempotency_key
  authorizing_decision_id / decision_hash / decision_validity_envelope_hash
  intent_admission_receipt_hash
  admitted_semantic_sequence
  authorization_not_after
  created_at
  intent_core_hash

SideEffectTransitionRecord                 # immutable/append-only
  transition_id / intent_core_hash
  transition_sequence / previous_transition_hash
  from_status / to_status / transition_kind
  authorization_receipt_hash? / authorized_semantic_sequence?
  execution_attempt? / executor_fence_token?
  external_operation_ref? / result_hash? / failure_code?
  occurred_at / actor_id
  transition_hash

SideEffectLedgerHead                       # mutable CAS projection; not content-addressed
  intent_core_hash
  latest_transition_sequence / latest_transition_hash / current_status
  cas_version
```

Historical v1 `FAILED_RETRYABLE` records remain immutable and are exposed through a versioned reader mapping to Revision-7 `RETRYABLE_FAILURE`; no stored history is rewritten. A legacy mutable `record_hash` is never promoted to `intent_core_hash`；migration emits an explicit legacy envelope and a new transition chain only after deterministic validation。`CANCELLED_STALE_AUTHORIZATION` proves the external adapter was not invoked. Once an `EXECUTING` transition commits, later semantic changes do not rewrite the attempt；idempotency/reconciliation appends the external outcome。

## Result and stage trace

`CompilationResultRecord` contains:

```text
run_status: IN_PROGRESS | COMPLETED | BLOCKED | FAILED
result_class: INPUT_REJECTION | EXECUTION_FAILURE | SEMANTIC_RESULT
proposal_admission_disposition?
input_rejection_code? / execution_failure_code? / retryability?
pipeline_version
compiler_version
validation_policy_version
decision_proposal_ref / hash / producer_id / producer_version / unchanged outcome
proposal_outcome_binding_ref / hash / policy_ref
decision_entity_context_ref / hash
governed_observation_set_ref / hash / executable_read_view_hash / executable_semantic_sequence
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
disposition_critical_verification_requests[] / receipts[] / semantic_uncertainties[]
contradiction_coverage_plan / receipts[] / fragment_semantic_observations[]
contradictions[]
requirement_assessments[]
unsupported_logic_findings[]
unsupported_predicate_findings[]
selective_coverage_guard_keys[]
temporal_validity_guards[]
compilation_core_ref / compilation_core_hash
decision_validity_envelope?
derivation_binding_hash
decision_justification? only when ACCEPTED
findings[]
canonical graph fields only when ACCEPTED
final_record_ref / final_record_hash
```

The active hash stack is `CompilationCore → DecisionValidityEnvelope → DecisionJustification → FinalCompilationRecord`。`DecisionValidityEnvelope` contains `compilation_core_hash`, never `final_record_hash`。A read-only legacy adapter may label `final_record_hash` as `compilation_hash` only with an explicit alias-version field；that label cannot enter a v7 hash preimage。

Executed stages use the replacement vocabulary:

```text
CONTENT_HASH_DAG_VALIDATED
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
CONTRADICTIONS_PROVISIONALLY_REDUCED
PROOFS_SELECTED
DISPOSITION_CRITICAL_OBSERVATIONS_VERIFIED
PROOFS_AND_CONTRADICTIONS_RECOMPUTED
COMPLETENESS_COMPUTED
TEMPORAL_VALIDITY_ENVELOPE_COMPUTED
GATE_EVALUATED
CANONICALIZED
```

Each expected stage is surfaced as `DONE`, `SKIPPED_INPUT_REJECTION`, `FAILED_EXECUTION`, `BLOCKED`, or `NOT_REACHED`. Consumers must not infer execution、proposal admission or business outcome from a missing findings list。

## API boundary

The generic compiler surface remains internal and capability-protected. Runtime acceptance retains a distinct capability.

### `POST /api/compiler/requests`

Create a request referencing an already immutable/signed domain-agent `DecisionProposal` and `DecisionEntityContext`, bound to mission/work item、exact enterprise world snapshot/revision、active policy bundle and universe/coverage decision class. Domain outcome mapping is resolved/validated from versioned policy；the compiler endpoint cannot author or alter the proposal outcome/entities.

### `POST /api/compiler/{request_id}/run`

Run the selected versioned pipeline. Product wiring may select only the approved replacement after cutover. Benchmark tooling may explicitly select `reasoner-only` or `old-critic`；those modes cannot call Runtime acceptance.

### `GET /api/compiler/{request_id}`

Return immutable proposal/request、governed observation/upstream bindings、policy/manifest provenance、Evidence/contradiction/disposition-critical verification receipts、semantic uncertainties、temporal sequence/epoch envelope、exact trace、run status、result class、proposal-admission disposition if any，and canonical output only if admitted. UI/API must show immutable `proposed_outcome` independently and never render input/execution failure or proposal non-admission as a newly authored business DENY。

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
ContradictionReducer.validate_and_provisionally_reduce(plan, receipts, fragment_observations)
DeterministicProofSelector.provisionally_select(requirements, bindings, upstream_bindings, contradictions, policies)
DispositionCriticalVerifier.verify(exact_preselected_fragment_target_entity_claim)
DispositionCriticalReducer.remove_reselect_rereduce(verification_receipts)
DeterministicRequirementCompleteness.compute(requirements, selected_proofs, contradictions)
TemporalValidityCompiler.compile(selected_proofs, applicability, policies, trusted_clock)
DeterministicProposalGate.evaluate(proposal, ...) -> proposal_admission_disposition + DecisionJustification? + DecisionValidityEnvelope?
Canonicalizer.compile(...)
RuntimeAcceptanceService.accept(...)
SemanticEpochPublisher.publish(change_set, successor_snapshots, read_fence)
SemanticEpochAuthorizationBarrier.authorize(decision, envelope, intervening_change_sets, upstream_decisions, trusted_clock)
SideEffectLedger.authorize_intent(...)
SideEffectLedger.reauthorize_for_execution(intent, envelope, ordered_change_sets, upstream_decisions, trusted_clock)
SideEffectLedger.reconcile(intent, idempotency_key, external_observation)
```

`FragmentEvidenceInterpreter`、independent `FragmentContradictionObserver` and narrow `DispositionCriticalVerifier` are the only replacement model interfaces. The verifier receives one isolated exact preselected proof/guard/contradiction-side tuple and returns only a three-valued verdict. Validators/reducers return immutable objects；deterministic selectors/Gate own upstream binding、applicability/materiality/impact/admission disposition；only Runtime acceptance/sequence barrier/Side Effect Ledger mutates or authorizes canonical state.

## Transaction boundary

Compiler stage persistence and Runtime Decision commit remain separate transactions linked by immutable final-record ID/hash. A compilation may be semantically accepted yet fail Runtime acceptance because mission revision or world snapshot advanced、its hash DAG is invalid or its proposed D→D edges are cyclic.

Runtime acceptance revalidates:

- `pipeline_version` is the approved active production pipeline;
- proposal-admission disposition is `ACCEPTED` and canonical outcome exactly equals immutable `DecisionProposal.proposed_outcome`;
- canonical graph/hash are present and immutable;
- proposal/producer/outcome/entity/observation context、exact upstream Decision envelopes、expected mission revision、governed enterprise world/universe/policy snapshots and derived envelope exactly match;
- universe/normalization/selection/Evidence/contradiction coverage was complete and all selected applicability/policy/coverage guards exist as validity-bearing provenance;
- trusted time is before exclusive `authorization_not_after`; upstream Decisions remain current/VALID；every intervening executable semantic sequence/ChangeSet is contiguous、hash-chain complete and non-intersecting；
- executable sequence pointer/upstream hashes remain unchanged through Runtime Decision acceptance. This transaction does not contain an external side effect。

Before those checks can mutate canonical state, Runtime validates every v7 digest against the closed `continuum-hash-v1` registry and the order `SourceUniverseSnapshot → GovernedReadView → GovernedObservationSet → DecisionProposal` plus `CompilationCore → Envelope → Justification → FinalRecord`。Under one owner-scope `DecisionDependencyGraphHead` transaction it computes the candidate Decision ID/acceptance sequence, requires exact already-existing accepted immutable upstream Decisions, checks exact-ID and lineage `REQUIRES` reachability, rejects D→D `AUTHORIZES`, then atomically appends the Decision、reverse invalidation index and acyclicity receipt。Any self/two-node/lineage cycle、future ref、missing adjacency or graph-root CAS conflict writes no canonical mutation。

`PublishEpochTxn` is a separate serializable transaction: verify predecessor/current sequence、assign exactly `s+1`、seal/publish one complete ChangeSet、advance one owner-scope executable pointer and expose one governed read fence. It requires **zero Decision-row writes**. Decision status/index/certificate records are lazy projections。

Side-effect intent admission seals an immutable core plus transition `0: NONE→INTENDED`；status is never hashed into that core。`ReauthorizeForExecutionTxn` performs the final sequence/range/upstream/clock/policy and transition-chain check, then atomically writes an execution-start receipt plus the next append-only `INTENDED | RETRYABLE_FAILURE → EXECUTING` transition under unchanged semantic/ledger pointers and hashes. Stale authorization appends `CANCELLED_STALE_AUTHORIZATION` with no network call. The external adapter is invoked only after that transaction with the persisted idempotency key；crash/unknown outcome appends `RECONCILIATION_REQUIRED`, never mutates history or claims cross-system atomicity。

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
compiler.contradictions.provisionally_reduced
compiler.proofs.selected
compiler.disposition_critical_observations.verified
compiler.proofs_and_contradictions.recomputed
compiler.semantic_uncertainty.recorded
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
runtime.semantic_sequence.reserved
runtime.semantic_changeset.sealed
runtime.semantic_sequence.published
runtime.decision.irrelevance_certified
runtime.decision.authorization_denied_upstream
runtime.decision.authorization_denied_relevant_change
runtime.decision.authorization_denied_expired
runtime.decision.authorization_denied_sequence_gap
runtime.side_effect.intent_authorized
runtime.side_effect.execution_reauthorized
runtime.side_effect.cancelled_stale_authorization
runtime.side_effect.reconciliation_required
```

These are compiler events. Only successful Runtime acceptance emits final `decision.created` and graph mutation events.
