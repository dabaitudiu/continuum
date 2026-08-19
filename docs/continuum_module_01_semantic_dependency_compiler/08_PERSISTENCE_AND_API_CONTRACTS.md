# 08 — Persistence and API Contracts

## Status

The persistence/API replacement below is design-only. Existing v1 records remain readable and immutable. V2 uses an explicit `pipeline_version` and cannot silently reinterpret `CriticReview` as the new stage outputs.

## Persistence entities

Source identity entities remain unchanged:

- `SourceArtifact`
- `SourceRevision`
- `ParsedRepresentation`
- `SourceFragment`

Compiler v2 adds immutable records:

- `CompilationRequest`
- `RequirementSetRecord`
- `EvidenceBindingSetRecord`
- `ContradictionSetRecord`
- `RequirementAssessmentSetRecord`
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
precedence_policy_version
executed_stages[]
requirements[]
evidence_bindings[]
contradictions[]
requirement_assessments[]
findings[]
canonical graph fields only when ACCEPTED
compilation_hash only when ACCEPTED
```

Executed stages use the v2 vocabulary:

```text
CONTEXT_ASSEMBLED
REQUIREMENTS_VALIDATED
BINDINGS_VALIDATED
CONTRADICTIONS_VALIDATED
COMPLETENESS_VALIDATED
GATE_EVALUATED
CANONICALIZED
```

Each expected stage is surfaced as `DONE`, `SKIPPED_STRUCTURAL_TERMINATION`, `BLOCKED`, or `NOT_REACHED`. Consumers must not infer execution from a missing findings list.

## API boundary

The generic compiler surface remains internal and capability-protected. Runtime acceptance retains a distinct capability.

### `POST /api/compiler/requests`

Create a request bound to mission/work item, exact world snapshot, expected mission revision, decision type, risk class, outcome vocabulary, and trusted `APPROVE | DENY | REVIEW` mapping.

### `POST /api/compiler/{request_id}/run`

Run the selected versioned pipeline. Product wiring may select only v2 after cutover. Benchmark tooling may explicitly select `reasoner-only` or `old-critic`; those modes cannot call Runtime acceptance.

### `GET /api/compiler/{request_id}`

Return immutable request, stage outputs/findings, exact stage trace, run status, semantic disposition, provenance, and canonical output if accepted.

### `POST /api/compiler/{request_id}/accept`

Runtime-only. Accept only an immutable v2 `ACCEPTED` result from the production pipeline; benchmark baseline modes are ineligible even if their historical disposition says accepted.

The current draft/compile routes may remain as versioned v1 readers during migration, but there is no v2-to-v1 fallback.

## Internal interfaces

```text
ContextAssembler.assemble(request)
RequirementDecomposer.decompose(context)
RequirementStructureValidator.validate(requirements, request)
EvidenceBinder.bind(requirements, context)
EvidenceBindingValidator.validate(bindings, requirements, context)
ContradictionDetector.detect(requirements, bindings, context)
ContradictionValidator.resolve(contradictions, requirements, bindings, context)
RequirementCompletenessAssessor.assess(requirements, bindings, contradictions)
RequirementAssessmentValidator.validate_and_trace(...)
DeterministicAcceptanceGate.evaluate(...)
Canonicalizer.compile(...)
RuntimeAcceptanceService.accept(...)
```

Each model interface returns a typed proposal. Each validator returns immutable validated objects/findings. Only the gate returns a semantic disposition; only the canonicalizer returns canonical graph objects; only Runtime acceptance mutates canonical Runtime state.

## Transaction boundary

Compiler stage persistence and Runtime Decision commit remain separate transactions linked by immutable compilation ID/hash. A compilation may be semantically accepted yet fail Runtime acceptance because mission revision or world snapshot advanced.

Runtime acceptance revalidates:

- `pipeline_version` is the active v2 production pipeline;
- disposition is `ACCEPTED`;
- canonical graph/hash are present and immutable;
- expected mission revision and world snapshot exactly match;
- inbox/idempotency and atomic audit/outbox requirements hold.

## Events

Suggested versioned events:

```text
compiler.requested
compiler.requirements.proposed
compiler.bindings.proposed
compiler.contradictions.proposed
compiler.completeness.assessed
compiler.structural.failed
compiler.run.blocked
compiler.review.required
compiler.compilation.accepted
compiler.compilation.rejected
```

These are compiler events. Only successful Runtime acceptance emits final `decision.created` and graph mutation events.
