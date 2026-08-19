# 04 — Intermediate Representation (IR)

## Design goal

The IR is the contract between probabilistic agent reasoning and deterministic runtime semantics.

## DecisionDraft

```json
{
  "request_id": "...",
  "decision_type": "SECURITY_REVIEW",
  "proposed_outcome": "APPROVED",
  "claims": [],
  "decision_dependencies": [],
  "unresolved_questions": [],
  "rationale_summary": "...",
  "model_metadata": {}
}
```

## ClaimDraft

```json
{
  "claim_local_id": "c1",
  "claim_type": "FACT|RULE|DERIVED_FACT|ASSESSMENT",
  "statement": "Vendor handles customer PII",
  "dependencies": [],
  "derived_from_claims": [],
  "materiality": "CRITICAL|SUPPORTING|CONTEXTUAL",
  "confidence": 0.0
}
```

`statement` is a concise auditable summary, not hidden chain-of-thought.

## DependencyRef

```json
{
  "source_ref": "vendor-profile@r7#$.handles_customer_pii",
  "relation": "SUPPORTED_BY",
  "materiality": "CRITICAL",
  "purpose": "Establishes that the policy clause applies"
}
```

Allowed relations P0:

- `SUPPORTED_BY`
- `GOVERNED_BY`
- `DERIVED_FROM`
- `REQUIRES`
- `AUTHORIZES`
- `CONTRADICTED_BY`

## Decision-level dependencies

Not every dependency needs an intermediate claim, but material policy and authorization dependencies should usually be explicit.

Example:

```json
{
  "source_ref": "security-policy@v13#section/7.3",
  "relation": "GOVERNED_BY",
  "materiality": "CRITICAL"
}
```

## UnresolvedQuestion

```json
{
  "question": "Is the penetration test newer than 12 months?",
  "required_source_type": "DOCUMENT",
  "blocking": true
}
```

If blocking unresolved questions exist, the result cannot compile to an accepted approval decision.

## CompilationResult

```json
{
  "compilation_id": "...",
  "status": "ACCEPTED",
  "decision_candidate": {},
  "canonical_claims": [],
  "canonical_edges": [],
  "validation_findings": [],
  "critic_findings": [],
  "contradictions": [],
  "compiler_version": "..."
}
```

## Canonical claim identity

P0 may assign generated UUIDs at commit time. Do not attempt semantic deduplication across unrelated decisions yet.

## Determinism requirement

Given the same:

- validated `DecisionDraft`;
- source registry snapshot;
- compiler version;

canonicalization must produce the same normalized edge set and status disposition.
