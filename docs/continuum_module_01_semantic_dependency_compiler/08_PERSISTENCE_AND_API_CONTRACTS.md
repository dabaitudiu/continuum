# 08 — Persistence and API Contracts

## Status

The persistence/API replacement below is Revision-3 design-only and awaits product-owner review after Revision 2 was rejected. Existing v1 records remain readable and immutable. Any replacement uses an explicit `pipeline_version` and cannot silently reinterpret `CriticReview` as new stage outputs.

## Persistence entities

Source identity entities remain unchanged:

- `SourceArtifact`
- `SourceRevision`
- `ParsedRepresentation`
- `SourceFragment`

The replacement stores immutable records across enterprise-world、compiler-policy and compiler-derived namespaces, plus a signed authoritative-registry snapshot envelope. Required records include：

- `CompilationRequest`
- `CompilerPolicyBundleRecord`
- `PolicyUsageTraceRecord`
- `SourceUniverseSnapshotRecord`
- `RuleNormalizationManifestRecord` / per-fragment accounting receipt
- `SourceSetManifestRecord`
- `CoverageBoundaryGuardRecord` / `GoverningRuleSetGuardRecord` / `ContradictionEligibilityGuardRecord`
- `RequirementProposalSetRecord`
- `RequirementCoverageObservationSetRecord` / per-partition `RequirementCoverageReceiptRecord`
- `RequirementCoverageCandidateSetRecord`
- `ApplicabilityProofCandidateSetRecord`
- `ApplicabilityJustificationRecord`
- `RequirementReconciliationRecord`
- `EffectiveRequirementSetRecord`
- `EvidenceBindingCandidateSetRecord`
- `ProofSelectedEvidenceBindingSetRecord`
- `ContradictionCoveragePlanRecord` / `ContradictionCoverageReceiptRecord`
- `ContradictionSetRecord`
- `RequirementAssessmentSetRecord`
- `UnsupportedLogicFindingRecord`
- `UnsupportedPredicateFindingRecord`
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
compiler_policy_bundle_ref / hash
input_world_snapshot_id / source_universe_snapshot_id / compiler_policy_snapshot_id
rule_normalization_manifest_ref / hash / coverage_status
policy_usage_trace[]
source_set_manifest_ref / hash / coverage_status
executed_stages[]
requirement_proposals[]
requirement_coverage_observations[] / receipts[]
applicability_proof_candidates[]
applicability_justifications[]
requirement_coverage_candidates[]
effective_requirements[]
evidence_binding_candidates[]
proof_selected_evidence_bindings[]
contradiction_coverage_plan / receipts[]
contradictions[]
requirement_assessments[]
unsupported_logic_findings[]
unsupported_predicate_findings[]
selective_coverage_guard_keys[]
derivation_binding_hash
decision_justification? only when ACCEPTED
findings[]
canonical graph fields only when ACCEPTED
compilation_hash only when ACCEPTED
```

Executed stages use the replacement vocabulary:

```text
POLICY_BUNDLE_VALIDATED
SOURCE_UNIVERSE_VALIDATED
RULE_NORMALIZATION_VALIDATED
SOURCE_SET_COVERAGE_VALIDATED
REQUIREMENTS_DECOMPOSED
GOVERNING_OBLIGATIONS_INVENTORIED
APPLICABILITY_PROOFS_VALIDATED
REQUIREMENTS_RECONCILED
BINDINGS_VALIDATED
CONTRADICTION_PARTITIONS_COMPLETED
CONTRADICTION_COVERAGE_VALIDATED
CONTRADICTIONS_REDUCED
PROOFS_SELECTED
COMPLETENESS_COMPUTED
GATE_EVALUATED
CANONICALIZED
```

Each expected stage is surfaced as `DONE`, `SKIPPED_STRUCTURAL_TERMINATION`, `BLOCKED`, or `NOT_REACHED`. Consumers must not infer execution from a missing findings list.

## API boundary

The generic compiler surface remains internal and capability-protected. Runtime acceptance retains a distinct capability.

### `POST /api/compiler/requests`

Create a request bound to mission/work item、exact enterprise world snapshot、expected mission revision、decision type/risk class、outcome vocabulary、active policy snapshot/bundle and source-universe/coverage decision class. Domain outcome mapping is resolved from versioned policy, not an unproven audit string.

### `POST /api/compiler/{request_id}/run`

Run the selected versioned pipeline. Product wiring may select only the approved replacement after cutover. Benchmark tooling may explicitly select `reasoner-only` or `old-critic`；those modes cannot call Runtime acceptance.

### `GET /api/compiler/{request_id}`

Return immutable request、policy/manifest provenance、coverage/partition receipts、stage outputs/findings、exact trace、run status、semantic disposition and canonical output if accepted. Partial contradiction output must be visibly incomplete and can never appear under a completed coverage state.

### `POST /api/compiler/{request_id}/accept`

Runtime-only. Accept only an immutable `ACCEPTED` result from the approved production pipeline；benchmark baseline modes are ineligible even if their historical disposition says accepted.

The current draft/compile routes may remain as versioned v1 readers during migration, but there is no replacement-to-v1 fallback.

## Internal interfaces

```text
ContextAssembler.assemble(request)
PolicyBundleValidator.validate(bundle, policy_snapshot)
SourceUniverseValidator.validate(universe_snapshot, world_snapshot)
RuleNormalizer.account(universe_snapshot, policy_bundle) -> RuleNormalizationManifest
SourceSetAssembler.assemble(request, universe, normalization, policy_bundle)
SourceCoverageValidator.validate(manifests, exact_inputs)
RequirementDecomposer.decompose(context) -> DecisionAnalysisProposal
RequirementCoverageAnalyzer.inventory(context_without_decomposition)
ApplicabilityProofValidator.validate_provisional(observations, current_bindings, policies)
RequirementReconciler.reconcile(proposal, coverage_candidates, contracts)
EvidenceBinder.bind(effective_requirements, context)
EvidenceBindingValidator.validate(candidates, requirements, context)
ContradictionPartitioner.plan(manifest, requirements, limits)
ContradictionObserver.observe(partition, requirements)
ContradictionReducer.validate_and_reduce(plan, receipts, observations)
DeterministicProofSelector.finalize_applicability_and_select(requirements, provisional_applicability, bindings, contradictions, policies)
DeterministicRequirementCompleteness.compute(requirements, selected_proofs, contradictions)
DeterministicAcceptanceGate.evaluate(...) -> disposition + DecisionJustification?
Canonicalizer.compile(...)
RuntimeAcceptanceService.accept(...)
```

RequirementDecomposer、RequirementCoverageAnalyzer、EvidenceBinder and partitioned ContradictionObserver are the only model interfaces. Coverage does not receive decomposition output；trusted normalization is not an unreviewed model acceptance path. Validators/reducers return immutable objects；applicability/proof selectors own canonical applicability/materiality/impact；only Runtime acceptance mutates canonical state.

## Transaction boundary

Compiler stage persistence and Runtime Decision commit remain separate transactions linked by immutable compilation ID/hash. A compilation may be semantically accepted yet fail Runtime acceptance because mission revision or world snapshot advanced.

Runtime acceptance revalidates:

- `pipeline_version` is the approved active production pipeline;
- disposition is `ACCEPTED`;
- canonical graph/hash are present and immutable;
- expected mission revision、enterprise world/universe/policy snapshots and derived-artifact envelope exactly match;
- universe/normalization/selection/partition coverage was complete and all selected applicability/policy/coverage guards exist as validity-bearing provenance;
- inbox/idempotency and atomic audit/outbox requirements hold.

## Events

Suggested versioned events:

```text
compiler.requested
compiler.source_universe.validated
compiler.rule_normalization.validated
compiler.source_set.validated
compiler.requirements.decomposed
compiler.requirement_coverage.proposed
compiler.applicability.validated
compiler.requirements.reconciled
compiler.bindings.proposed
compiler.contradiction_partition.completed
compiler.contradictions.reduced
compiler.proofs.selected
compiler.completeness.assessed
compiler.unsupported_logic.detected
compiler.unsupported_predicate.detected
compiler.structural.failed
compiler.run.blocked
compiler.review.required
compiler.compilation.accepted
compiler.compilation.rejected
```

These are compiler events. Only successful Runtime acceptance emits final `decision.created` and graph mutation events.
