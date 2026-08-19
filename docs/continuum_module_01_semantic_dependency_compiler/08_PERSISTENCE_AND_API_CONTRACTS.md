# 08 — Persistence and API Contracts

## Status

The persistence/API replacement below is Revision-2 design-only and awaits product-owner review after the first concrete specification was rejected. Existing v1 records remain readable and immutable. V2 uses an explicit `pipeline_version` and cannot silently reinterpret `CriticReview` as the new stage outputs.

## Persistence entities

Source identity entities remain unchanged:

- `SourceArtifact`
- `SourceRevision`
- `ParsedRepresentation`
- `SourceFragment`

Compiler v2 adds immutable records:

- `CompilationRequest`
- `CompilerPolicyBundleRecord`
- `PolicyUsageTraceRecord`
- `SourceSetManifestRecord`
- `RequirementProposalSetRecord`
- `RequirementCoverageObservationSetRecord` / per-partition `RequirementCoverageReceiptRecord`
- `RequirementCoverageCandidateSetRecord`
- `RequirementReconciliationRecord`
- `EffectiveRequirementSetRecord`
- `EvidenceBindingCandidateSetRecord`
- `ProofSelectedEvidenceBindingSetRecord`
- `ContradictionCoveragePlanRecord` / `ContradictionCoverageReceiptRecord`
- `ContradictionSetRecord`
- `RequirementAssessmentSetRecord`
- `UnsupportedLogicFindingRecord`
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
policy_usage_trace[]
source_set_manifest_ref / hash / coverage_status
executed_stages[]
requirement_proposals[]
requirement_coverage_observations[] / receipts[]
requirement_coverage_candidates[]
effective_requirements[]
evidence_binding_candidates[]
proof_selected_evidence_bindings[]
contradiction_coverage_plan / receipts[]
contradictions[]
requirement_assessments[]
unsupported_logic_findings[]
decision_justification? only when ACCEPTED
findings[]
canonical graph fields only when ACCEPTED
compilation_hash only when ACCEPTED
```

Executed stages use the v2 vocabulary:

```text
POLICY_BUNDLE_VALIDATED
SOURCE_SET_COVERAGE_VALIDATED
REQUIREMENTS_DECOMPOSED
GOVERNING_OBLIGATIONS_INVENTORIED
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

Create a request bound to mission/work item、exact world snapshot、expected mission revision、decision type/risk class、outcome vocabulary、active CompilerPolicyBundle and source-coverage decision class. Domain outcome mapping is resolved from the versioned policy ref, not accepted as an unproven audit string.

### `POST /api/compiler/{request_id}/run`

Run the selected versioned pipeline. Product wiring may select only v2 after cutover. Benchmark tooling may explicitly select `reasoner-only` or `old-critic`; those modes cannot call Runtime acceptance.

### `GET /api/compiler/{request_id}`

Return immutable request、policy/manifest provenance、coverage/partition receipts、stage outputs/findings、exact trace、run status、semantic disposition and canonical output if accepted. Partial contradiction output must be visibly incomplete and can never appear under a completed coverage state.

### `POST /api/compiler/{request_id}/accept`

Runtime-only. Accept only an immutable v2 `ACCEPTED` result from the production pipeline; benchmark baseline modes are ineligible even if their historical disposition says accepted.

The current draft/compile routes may remain as versioned v1 readers during migration, but there is no v2-to-v1 fallback.

## Internal interfaces

```text
ContextAssembler.assemble(request)
PolicyBundleValidator.validate(bundle, world_snapshot)
SourceSetAssembler.assemble(request, policy_bundle) -> SourceSetManifest
SourceCoverageValidator.validate(manifest, world_snapshot)
RequirementDecomposer.decompose(context) -> DecisionAnalysisProposal
RequirementCoverageAnalyzer.inventory(context_without_decomposition)
RequirementReconciler.reconcile(proposal, coverage_candidates, contracts)
EvidenceBinder.bind(effective_requirements, context)
EvidenceBindingValidator.validate(candidates, requirements, context)
ContradictionPartitioner.plan(manifest, requirements, limits)
ContradictionObserver.observe(partition, requirements)
ContradictionReducer.validate_and_reduce(plan, receipts, observations)
DeterministicProofSelector.select(requirements, bindings, contradictions, policies)
DeterministicRequirementCompleteness.compute(requirements, selected_proofs, contradictions)
DeterministicAcceptanceGate.evaluate(...) -> disposition + DecisionJustification?
Canonicalizer.compile(...)
RuntimeAcceptanceService.accept(...)
```

RequirementDecomposer、RequirementCoverageAnalyzer、EvidenceBinder and partitioned ContradictionObserver are the only model interfaces. Coverage does not receive decomposition output. Validators/reducers return immutable objects; proof selector owns canonical materiality and contradiction impact; completeness owns assessments. Only the gate returns semantic disposition; only canonicalizer returns graph objects; only Runtime acceptance mutates canonical Runtime state.

## Transaction boundary

Compiler stage persistence and Runtime Decision commit remain separate transactions linked by immutable compilation ID/hash. A compilation may be semantically accepted yet fail Runtime acceptance because mission revision or world snapshot advanced.

Runtime acceptance revalidates:

- `pipeline_version` is the active v2 production pipeline;
- disposition is `ACCEPTED`;
- canonical graph/hash are present and immutable;
- expected mission revision、world snapshot、CompilerPolicyBundle and SourceSetManifest exactly match;
- source/partition coverage was complete and all selected policy/manifest refs exist as validity-bearing provenance;
- inbox/idempotency and atomic audit/outbox requirements hold.

## Events

Suggested versioned events:

```text
compiler.requested
compiler.source_set.validated
compiler.requirements.decomposed
compiler.requirement_coverage.proposed
compiler.requirements.reconciled
compiler.bindings.proposed
compiler.contradiction_partition.completed
compiler.contradictions.reduced
compiler.proofs.selected
compiler.completeness.assessed
compiler.unsupported_logic.detected
compiler.structural.failed
compiler.run.blocked
compiler.review.required
compiler.compilation.accepted
compiler.compilation.rejected
```

These are compiler events. Only successful Runtime acceptance emits final `decision.created` and graph mutation events.
