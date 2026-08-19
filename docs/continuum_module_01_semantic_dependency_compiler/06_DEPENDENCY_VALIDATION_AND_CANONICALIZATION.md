# 06 — Validation, Acceptance, and Canonicalization

## Fixed validator order

Validation follows the replacement pipeline, and each stage records its own trace. Structural integrity is checked immediately after the stage that introduces the data; semantic validity is accumulated until the final gate.

### S1 Requirement structure

Check schema, trimmed/bounded text, enum values, duplicate/unknown local IDs, outcome vocabulary, and acyclic `depends_on_requirement_ids`. Requirements cannot contain source refs.

### S2 Evidence binding integrity

Check canonical ref existence, request allowlist, owner scope, world-snapshot temporal validity, source type, authority-role legality, binding cross-links, and CRITICAL/materiality field consistency.

Unknown refs are fatal. Fuzzy repair is forbidden. A historical source may be read only when explicitly allowed and cannot become a current CRITICAL validity-bearing authority.

### S3 Contradiction integrity and precedence

Check both refs, optional binding/ref identity, requirement linkage, source classes, authority rank, and configured precedence. The model's claim that a conflict is resolvable never changes deterministic precedence.

### S4 Completeness cross-links and reachability

Check one assessment per explicit Requirement, referenced binding/contradiction IDs, and the claimed transitive requirement path. Compute support through validity-bearing CRITICAL paths; do not demand direct evidence on a derived Requirement if a valid leaf-to-decision path already exists.

### S5 Deterministic outcome/acceptance policy

Apply the exact `APPROVE | DENY | REVIEW` rules in [15_REPLACEMENT_ARCHITECTURE.md](15_REPLACEMENT_ARCHITECTURE.md). Semantic gaps and conflicts reach this stage; they are not pre-validator exits.

## Early terminal structural errors

- invalid stage schema after one repair;
- duplicate/unknown local IDs or a requirement cycle;
- fabricated, unauthorized, cross-scope, or stale source ref;
- illegal source role/relation/authority class;
- inconsistent cross-links between typed objects.

These return a structural disposition and an exact `executed_stages` trace. No canonical output is produced.

## Non-terminal semantic conditions

The following must not terminate before contradiction and completeness execute:

- a critical Requirement currently has no evidence binding;
- the Requirement set is empty or an APPROVE outcome has no applicable critical Requirement;
- a proposed high-risk outcome has no support path yet;
- an unresolved or blocking question exists;
- contradictory current authorities exist;
- model confidence is low or semantic evidence is ambiguous;
- proposed outcome appears inconsistent with evidence.

V1 codes such as `CRITICAL_CLAIM_UNSUPPORTED`, `HIGH_RISK_DECISION_UNSUPPORTED`, and `BLOCKING_QUESTION_UNRESOLVED` therefore move out of the early structural validator. Their v2 equivalents are RequirementAssessments and final-gate findings.

## Canonicalization

Canonicalization runs only after disposition `ACCEPTED`.

### Stable mapping

- each Requirement maps to one canonical Claim;
- validated EvidenceBindings map to SourceFragment → Claim edges;
- requirement DAG links map to Claim → Claim edges;
- applicable critical Claims map to Decision-requires-Claim edges;
- deterministic stable IDs derive from compilation inputs and versioned policy;
- identical edges deduplicate; ordering is stable.

### Materiality

Only `CRITICAL` edges are validity-bearing for later invalidation. `SUPPORTING` edges remain provenance-only. The canonicalizer cannot upgrade evidence based on relevance, model-read telemetry, or broad document membership.

### No silent semantic repair

The canonicalizer cannot:

- substitute a near-match ref;
- add a binding omitted by Stage 2;
- promote SUPPORTING to CRITICAL;
- resolve a contradiction by model preference;
- add redundant direct edges to satisfy a shallow completeness check;
- change the proposed outcome.

## Compilation hash

The v2 hash covers at least:

- normalized request and trusted outcome semantics;
- validated Requirements, EvidenceBindings, Contradictions, and RequirementAssessments;
- canonical refs and source/fragment hashes;
- world snapshot;
- pipeline/compiler/validation-policy versions;
- deterministic precedence-policy version;
- stage prompt/schema/model metadata required for provenance.

The same validated inputs and versions must produce an identical disposition, graph, trace, and hash.
