# 08 — Persistence and API Contracts

## Persistence entities

### SourceArtifact

Logical identity across revisions.

### SourceRevision

Immutable revision metadata and hash.

### ParsedRepresentation

Immutable parser output identity, parser version/config hash, and owning source revision.

### SourceFragment

Stable fragment identity, path, hash, parent relationship.

### CompilationRequest

```text
request_id
mission_id
work_item_id
agent_id
world_snapshot_id
decision_type
risk_class
created_at
```

### DecisionDraftRecord

Raw structured model output + model metadata. Store no hidden chain-of-thought.

### CompilerFinding

Validation, completeness, contradiction, security findings.

### CompilationResultRecord

Canonical normalized result, compiler version, compilation hash, disposition.

## Proposed API

The generic surface is internal-only. If `CONTINUUM_COMPILER_API_CAPABILITY` is absent it returns no usable endpoint; configured internal callers must provide `X-Continuum-Compiler-Capability`. Public product traffic uses only the fixed `/api/demo/compiler` scenario routes. Runtime acceptance has a second, separate capability.

### POST `/api/compiler/requests`

Create a compilation request bound to mission/work/world snapshot.

### POST `/api/compiler/{request_id}/draft`

Submit a structured DecisionDraft from the agent gateway.

### POST `/api/compiler/{request_id}/compile`

Run deterministic validation + critic/contradiction stages according to policy.

### GET `/api/compiler/{request_id}`

Return request, draft, findings, and result.

### POST `/api/compiler/{request_id}/accept`

Runtime-only endpoint: accept an `ACCEPTED` result and translate it into runtime graph mutations.

Human UI should not call this directly.

## Internal service interfaces

```text
SourceRegistry.resolve(ref, world_snapshot_id, allow_historical=False)
SourceRegistry.allowed_refs(scope, world_snapshot_id)
DraftValidator.validate(draft, context)
CompletenessCritic.review(...)
ContradictionDetector.check(...)
Canonicalizer.compile(...)
```

## Transaction boundary

Compiler persistence and runtime decision commit should be separate transactions linked by immutable `compilation_id`.

Reason: compilation is an auditable artifact; runtime acceptance may fail because the mission revision has advanced.

## Optimistic concurrency

Runtime acceptance includes expected mission revision/world snapshot. If the world changed after compilation, the runtime rejects acceptance and requires recompilation or revalidation.

The world snapshot binds both the current business revision per artifact and the active parsed representation per current revision. Canonical compilation provenance remains fully representation-qualified; snapshot-relative shorthand is never persisted.

## Outbox events

Suggested events:

```text
compiler.requested
compiler.draft.received
compiler.validation.failed
compiler.review.required
compiler.accepted
compiler.rejected
```

These are compiler events, distinct from final `decision.created` runtime events.

Runtime outbox publication is retried independently by `app.events.outbox_worker` (deployed as a Cloud Run Job). A command replay is not required to recover a pending projection.
