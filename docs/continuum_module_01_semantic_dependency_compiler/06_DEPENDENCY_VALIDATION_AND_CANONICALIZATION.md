# 06 — Validation, Acceptance, and Canonicalization

## Fixed validator order

Validation follows the replacement pipeline, and each stage records its own trace. Structural integrity is checked immediately after the stage that introduces the data; semantic validity is accumulated until the final gate.

### S1 Requirement structure

Check schema, trimmed/bounded text, enum values, expected truth, proof mode, duplicate/unknown local IDs, and acyclic `depends_on_requirement_ids`. `DIRECT` has no prerequisites; `DERIVED_ALL` has at least one and the DAG is conjunction-only. Requirements cannot contain source refs or CRITICAL/SUPPORTING materiality; every Requirement is an APPROVE-validity prerequisite.

### S2 Evidence binding integrity

Check canonical ref existence, request allowlist, owner scope, world-snapshot temporal validity, source type, authority-role legality, binding cross-links, entailed-truth vocabulary, and CRITICAL/materiality field consistency. CRITICAL bindings may target only DIRECT Requirements.

Unknown refs are fatal. Fuzzy repair is forbidden. A historical source may be read only when explicitly allowed and cannot become a current CRITICAL validity-bearing authority.

### S3 Contradiction integrity and precedence

Check both refs, each side's entailed truth, optional binding/ref/truth identity, requirement linkage, source classes, authority rank, and configured precedence. The model's claim that a conflict is resolvable never changes deterministic precedence. A resolved winner without a matching validated CRITICAL binding remains incomplete and cannot be canonicalized.

### S4 Deterministic completeness and reachability

Compute one assessment per explicit Requirement from a fixed truth table. DIRECT Requirements compare precedence-filtered CRITICAL `entailed_truth` with `expected_truth` and select one same-truth proof binding by authority rank/canonical ref; opposite truths still conflict. DERIVED_ALL Requirements conjoin prerequisite assessments. Code emits support paths, blocking IDs, missing-proposition text, and finding codes. Do not demand direct evidence on a derived Requirement if a valid leaf-to-root path already exists.

### S5 Deterministic outcome/acceptance policy

Compute expected `APPROVE | DENY | REVIEW` from root assessments, compare it with the model proposal through the trusted outcome mapping, and apply the exact rules in [15_REPLACEMENT_ARCHITECTURE.md](15_REPLACEMENT_ARCHITECTURE.md). For accepted APPROVE/DENY, emit a deterministic minimal `DecisionJustification`; semantic gaps and conflicts are not pre-validator exits.

## Early terminal structural errors

- invalid stage schema after one repair;
- duplicate/unknown local IDs or a requirement cycle;
- fabricated, unauthorized, cross-scope, or stale source ref;
- illegal source role/relation/authority class;
- inconsistent cross-links between typed objects.

These return a structural disposition and an exact `executed_stages` trace. No canonical output is produced.

## Non-terminal semantic conditions

The following must not terminate before contradiction and completeness execute:

- a Requirement currently has no CRITICAL evidence/counterevidence binding;
- the Requirement set is empty;
- a proposed high-risk outcome has no support path yet;
- an unresolved or blocking question exists;
- contradictory current authorities exist;
- model confidence is low or semantic evidence is ambiguous;
- proposed outcome appears inconsistent with evidence.

V1 codes such as `CRITICAL_CLAIM_UNSUPPORTED`, `HIGH_RISK_DECISION_UNSUPPORTED`, and `BLOCKING_QUESTION_UNRESOLVED` therefore move out of the early structural validator. Their v2 equivalents are RequirementAssessments and final-gate findings.

## Canonicalization

Canonicalization runs only after disposition `ACCEPTED`.

### Stable mapping

- each RequirementAssessment selected by `DecisionJustification` maps to one canonical Claim recording proposition, expected truth, and assessment status;
- selected winning EvidenceBindings map to SourceFragment → assessment Claim edges through Runtime invalidation-bearing `SUPPORTED_BY` / `GOVERNED_BY`, including counterevidence that justifies an accepted DENY;
- selected DERIVED_ALL links map prerequisite Claim → derived Claim edges;
- selected requirement-DAG root assessment Claims map to validity-bearing Decision-requires-Claim edges;
- deterministic stable IDs derive from compilation inputs and versioned policy;
- identical edges deduplicate; ordering is stable.

### Materiality

Only `CRITICAL` edges are validity-bearing for later invalidation. `SUPPORTING` edges remain provenance-only. The canonicalizer cannot upgrade evidence based on relevance, model-read telemetry, or broad document membership.

`CONTRADICTED_BY` is not a direct invalidation relation in the current Runtime kernel. It cannot be the sole provenance for an accepted DENY; unresolved contradictions produce no accepted canonical graph, while a precedence-resolved winner is mapped through the validity-bearing assessment edge above.

### No silent semantic repair

The canonicalizer cannot:

- substitute a near-match ref;
- add a binding omitted by Stage 2;
- promote SUPPORTING to CRITICAL;
- resolve a contradiction by model preference;
- add redundant direct edges to satisfy a shallow completeness check;
- change the proposed outcome.

The canonicalizer also cannot include unselected sibling Requirements “for completeness”. APPROVE includes all required root closures; DENY includes only the deterministic failed-root proof slice. Full analysis remains in the compiler record without becoming Runtime critical state.

## Compilation hash

The v2 hash covers at least:

- normalized request and trusted outcome semantics;
- validated Requirements, EvidenceBindings, Contradictions, and RequirementAssessments;
- deterministic outcome class and DecisionJustification;
- canonical refs and source/fragment hashes;
- world snapshot;
- pipeline/compiler/validation-policy versions;
- deterministic precedence-policy version;
- stage prompt/schema/model metadata required for provenance.

The same validated inputs and versions must produce an identical disposition, graph, trace, and hash.
