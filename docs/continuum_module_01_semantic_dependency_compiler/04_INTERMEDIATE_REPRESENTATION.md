# 04 — Intermediate Representation (IR)

## Status and versioning

The product owner approved a requirement-centred v2 IR and rejected the current vague critic architecture. The contracts below are **design contracts, not yet implemented**. Their normative field-level definition is in [15_REPLACEMENT_ARCHITECTURE.md](15_REPLACEMENT_ARCHITECTURE.md).

The implemented `DecisionDraft`, `ClaimDraft`, `DependencyRef`, `CriticProposal`, and `CriticReview` are v1 legacy types during migration. They remain readable for persisted evidence and the reasoner-only/old-critic ablation arms, but they are not the final architecture and must not be silently reinterpreted as v2.

## Design goal

The IR separates four semantic questions that v1 mixed together:

1. What propositions must hold for the Decision?
2. Which exact source fragments bear on each proposition, and with what materiality?
3. Which authoritative propositions conflict?
4. Is each explicit requirement sufficiently and consistently evidenced?

Only after all four outputs are structurally validated may deterministic code decide a compilation disposition and construct canonical graph state.

## V2 analysis objects

### `Requirement`

```text
requirement_local_id
proposition
kind: FACT | RULE | AUTHORIZATION | EVIDENCE_PRESENCE | NEGATIVE_CONSTRAINT
necessity: CRITICAL | SUPPORTING
polarity: MUST_HOLD | MUST_NOT_HOLD
depends_on_requirement_ids[]
applies_to_outcomes[]
rationale_summary
```

A Requirement is a semantic proposition. Its schema contains no source ref.

### `EvidenceBinding`

```text
binding_local_id
requirement_local_id
source_ref
semantic_role: EVIDENCE | GOVERNING_AUTHORITY | SATISFACTION_RECORD | COUNTEREVIDENCE
stance: SUPPORTS | OPPOSES
materiality: CRITICAL | SUPPORTING
validity_impact: MAY_CHANGE_VALIDITY | EXPLANATION_ONLY
counterfactual_summary
```

`CRITICAL` means the source can change requirement/decision validity; relevant explanatory evidence is `SUPPORTING` or omitted. A model proposes this classification, deterministic code enforces ref/type/field consistency, and benchmark evidence measures semantic correctness.

### `Contradiction`

```text
contradiction_local_id
requirement_local_id
lhs_ref
rhs_ref
lhs_binding_id?
rhs_binding_id?
proposition
contradiction_type
severity
model_resolvable_by_precedence
model_recommended_disposition
deterministic_resolution
precedence_rule_id?
```

The model proposes the semantic conflict. Deterministic code owns source validation, authority metadata, precedence, and effective resolution.

### `RequirementAssessment`

```text
requirement_local_id
status: SATISFIED | UNSATISFIED | CONTRADICTED | INSUFFICIENT_EVIDENCE
critical_binding_ids[]
supporting_binding_ids[]
contradiction_ids[]
support_path_requirement_ids[]
missing_evidence_proposition?
assessment_summary
```

Completeness assesses only explicit Requirements. It cannot create Requirements, bindings, source refs, or `UNKNOWN_SOURCE_REQUIRED`.

## V2 result envelope

```text
CompilationResultV2
  request_id
  compilation_id
  run_status: IN_PROGRESS | COMPLETED | BLOCKED | FAILED
  disposition?
  requirements[]
  evidence_bindings[]
  contradictions[]
  requirement_assessments[]
  canonical_decision?
  canonical_claims[]
  canonical_edges[]
  findings[]
  executed_stages[]
  pipeline_version
  compiler_version
  validation_policy_version
  compilation_hash?
  stage_model_metadata[]
```

`BLOCKED` and `FAILED` have no semantic disposition or canonical output. Non-accepted semantic results have no canonical Decision/Claim/Edge. Only an accepted result contains a compilation hash and Runtime-eligible canonical graph.

## Canonical mapping

Each Requirement maps to one canonical Claim. Requirement dependency paths map to Claim → Claim edges; EvidenceBindings map to SourceFragment → Claim edges; applicable critical Claims map to Decision-requires-Claim edges.

The canonicalizer validates support through the transitive Source → Claim → Claim → Decision closure. It must not require or manufacture redundant direct Source → derived Claim/Decision edges.

## Determinism requirement

Given identical:

- validated v2 analysis objects;
- SourceRegistry/world snapshot;
- compiler and validation-policy versions;
- deterministic outcome semantics and precedence policy;

the final disposition, canonical ordering, IDs, edge set, compilation hash, and stage trace must be identical.

No hidden chain-of-thought is persisted. Only typed propositions, concise summaries, exact refs, deterministic findings, and model/usage provenance are retained.
