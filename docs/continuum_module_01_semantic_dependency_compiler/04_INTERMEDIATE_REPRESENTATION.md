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

Stage 1 returns a `DecisionAnalysisProposal` envelope containing the request/decision type, one `proposed_outcome` from the trusted request vocabulary, `Requirement[]`, and a concise rationale. The proposed outcome remains untrusted model output; the deterministic gate computes an expected `APPROVE | DENY | REVIEW` class from RequirementAssessments and compares it with the trusted outcome mapping.

### `Requirement`

```text
requirement_local_id
proposition
kind: FACT | RULE | AUTHORIZATION | EVIDENCE_PRESENCE | NEGATIVE_CONSTRAINT
expected_truth: TRUE | FALSE
proof_mode: DIRECT | DERIVED_ALL
depends_on_requirement_ids[]
rationale_summary
```

A Requirement is a semantic proposition and an APPROVE-validity prerequisite. Its schema contains no source ref and no CRITICAL/SUPPORTING escape hatch; materiality belongs to EvidenceBinding. `DIRECT` is proven by CRITICAL source binding; `DERIVED_ALL` is proven by the conjunction of all prerequisite Requirements.

### `EvidenceBinding`

```text
binding_local_id
requirement_local_id
source_ref
semantic_role: EVIDENCE | GOVERNING_AUTHORITY | SATISFACTION_RECORD
entailed_truth: TRUE | FALSE
materiality: CRITICAL | SUPPORTING
validity_impact: MAY_CHANGE_VALIDITY | EXPLANATION_ONLY
counterfactual_summary
```

`entailed_truth` is truth relative to the Requirement proposition, not the outcome. `CRITICAL` means the source can change requirement/decision validity; relevant explanatory evidence is `SUPPORTING` or omitted. A model proposes these semantic labels, deterministic code enforces ref/type/field consistency, and benchmark evidence measures correctness.

### `Contradiction`

```text
ContradictionCandidate                    # model output
  contradiction_local_id
  requirement_local_id
  lhs_ref / rhs_ref
  lhs_entailed_truth / rhs_entailed_truth
  proposition / contradiction_type / severity
  model_resolvable_by_precedence
  model_recommended_disposition

Contradiction                             # validated record
  candidate
  lhs_binding_id? / rhs_binding_id?
  deterministic_resolution
  precedence_rule_id?
  validation_finding_codes[]
```

The model outputs only `ContradictionCandidate`. Deterministic code creates `Contradiction` and owns source validation, binding/truth consistency, authority metadata, precedence, and effective resolution. A precedence winner without a matching validated CRITICAL EvidenceBinding cannot be promoted into canonical state and makes the result incomplete.

### `RequirementAssessment`

```text
requirement_local_id
status: SATISFIED | UNSATISFIED | CONTRADICTED | INSUFFICIENT_EVIDENCE
critical_binding_ids[]
supporting_binding_ids[]
proof_binding_id?
contradiction_ids[]
support_paths[][]
blocking_requirement_ids[]
missing_evidence_proposition?
finding_codes[]
assessment_summary
```

Deterministic completeness computes this object for explicit Requirements from entailed truth, precedence, and DAG reachability. A DIRECT assessment selects one proof binding by authority rank then canonical ref; joint evidence must be decomposed as DIRECT prerequisites under DERIVED_ALL. It cannot create Requirements, bindings, source refs, or `UNKNOWN_SOURCE_REQUIRED`; the model has no RequirementAssessment write contract.

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
  decision_justification?
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

For accepted results, deterministic `DecisionJustification` records the selected root Requirements, transitive proof-slice Requirements, CRITICAL bindings, and selection rule. APPROVE selects all satisfied root closures. DENY selects one failed root proof path using a normalized canonical requirement key, never case/domain/local-ID order. REVIEW has no justification or canonical graph.

## Canonical mapping

Each selected RequirementAssessment maps to one canonical validity-bearing Claim that records proposition, expected truth, and `SATISFIED`/`UNSATISFIED` status. DERIVED_ALL dependency paths in the deterministic proof slice map prerequisite Claim → derived Claim; winning selected EvidenceBindings map through `SUPPORTED_BY`/`GOVERNED_BY` to DIRECT assessment Claims; selected DAG-root assessment Claims map to Decision-requires-Claim edges.

This mapping applies to accepted APPROVE and DENY outcomes. A DENY supported by counterevidence must still depend on that source through a Runtime invalidation-bearing edge; `CONTRADICTED_BY` alone is insufficient and unresolved contradictions never produce accepted Runtime graph state.

The canonicalizer validates support through the transitive Source → Claim → Claim → Decision closure. It must not require or manufacture redundant direct Source → derived Claim/Decision edges.

## Determinism requirement

Given identical:

- validated v2 analysis objects;
- SourceRegistry/world snapshot;
- compiler and validation-policy versions;
- deterministic outcome semantics and precedence policy;

the final disposition, canonical ordering, IDs, edge set, compilation hash, and stage trace must be identical.

No hidden chain-of-thought is persisted. Only typed propositions, concise summaries, exact refs, deterministic findings, and model/usage provenance are retained.
