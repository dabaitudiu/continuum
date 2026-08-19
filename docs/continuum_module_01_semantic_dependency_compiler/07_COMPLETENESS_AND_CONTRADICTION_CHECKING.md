# 07 — Independent Contradiction and Requirement Completeness

## Architecture decision

The former Completeness Critic is rejected. It mixed missing dependencies, unsupported claims, irrelevant refs, contradiction candidates, severity, and disposition; allowed `UNKNOWN_SOURCE_REQUIRED`; and often never ran because semantic conditions terminated validation first.

The replacement has two separate passes with disjoint write contracts:

1. Independent Contradiction Pass writes `Contradiction` proposals only.
2. Requirement Completeness writes `RequirementAssessment` proposals only.

Neither pass edits Requirements, EvidenceBindings, the proposed outcome, or canonical state.

## Independent Contradiction Pass

### Question

> For each explicit Requirement, do two current, in-scope authoritative source propositions conflict in a way that can affect validity?

### Input

- explicit Requirements;
- validated EvidenceBindings;
- bounded relevant authoritative fragments, including relevant unbound refs;
- source values/claims, trust class, authority rank, scope, and temporal metadata.

### Output

Typed ref pairs, proposition/topic, contradiction type, severity, and non-authoritative model recommendation. Deterministic code validates the refs and computes precedence/resolution.

### Deterministic precedence

Only configured rules may resolve a conflict, such as current over historical revision, signed over draft approval, canonical record over cached snapshot, or an explicit mission override. Equal-authority unresolved CRITICAL conflict cannot silently accept.

The pass is executed even when Stage 2 produced incomplete evidence. Otherwise a missing binding can hide the very conflict needed to explain why approval is unsafe.

## Requirement Completeness

### Question

> Is each Stage 1 Requirement sufficiently evidenced by a direct or transitive validated path, after contradiction results are known?

### Input

- explicit Requirements and requirement DAG;
- validated CRITICAL/SUPPORTING bindings;
- validated contradiction results;
- deterministic direct/transitive support-path summaries.

### Output

Exactly one `RequirementAssessment` per explicit Requirement:

- `SATISFIED`
- `UNSATISFIED`
- `CONTRADICTED`
- `INSUFFICIENT_EVIDENCE`

### Hard boundaries

Completeness cannot:

- invent a requirement omitted by Stage 1;
- invent or suggest a canonical source ref;
- emit `UNKNOWN_SOURCE_REQUIRED`;
- add or rewrite a binding;
- require a redundant direct source edge when transitive support exists;
- decide final disposition.

If evidence is insufficient, it records a semantic `missing_evidence_proposition`. Requirement omission quality is measured separately against frozen requirement ground truth.

## Reachability rule

For a critical Requirement to count as evidenced, deterministic code must find at least one current, authorized, validity-bearing CRITICAL path from a SourceFragment through zero or more prerequisite/derived Claims to that Requirement and onward to the Decision.

`SUPPORTING`, `CONTEXTUAL`, `CONTRADICTED_BY`, stale, unauthorized, or rootless derived paths do not satisfy this rule. Conversely, a valid Source → Claim → Claim → Decision path is sufficient without a duplicate Source → derived Claim/Decision edge.

## Final gate effects

- missing/insufficient applicable critical Requirement → `REJECTED_INCOMPLETE_REQUIREMENTS`;
- unresolved equal-authority CRITICAL contradiction → `NEEDS_HUMAN_REVIEW`;
- deterministically winning authority contradicts the proposed outcome → `REJECTED_CONTRADICTION`;
- semantic result inconsistent with trusted outcome class → `REJECTED_OUTCOME_CONSTRAINT`;
- only a fully compatible result can be `ACCEPTED` and canonicalized.

These are deterministic gate decisions over typed validated inputs, not direct model decisions.

## Evaluation

Contradiction and completeness are scored separately:

- contradiction pair recall and critical-severity recall;
- requirement proposition recall;
- requirement assessment accuracy;
- critical dependency recall/precision;
- explicit stage-execution coverage;
- disposition and accepted-case coverage.

The benchmark must expose safe-by-rejection behavior. A zero stale-escape rate over one accepted case is not proof of compiler usefulness.
