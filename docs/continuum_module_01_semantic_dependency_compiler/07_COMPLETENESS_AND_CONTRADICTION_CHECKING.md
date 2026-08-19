# 07 — Independent Contradiction and Requirement Completeness

## Architecture decision

The former Completeness Critic is rejected. It mixed missing dependencies, unsupported claims, irrelevant refs, contradiction candidates, severity, and disposition; allowed `UNKNOWN_SOURCE_REQUIRED`; and often never ran because semantic conditions terminated validation first.

The replacement has two separate passes with disjoint write contracts:

1. Independent Contradiction Pass writes `Contradiction` proposals only.
2. Deterministic Requirement Completeness computes `RequirementAssessment` records only.

Neither pass edits Requirements, EvidenceBindings, the proposed outcome, or canonical state.

## Independent Contradiction Pass

### Question

> For each explicit Requirement, do two current, in-scope authoritative source propositions conflict in a way that can affect validity?

### Input

- explicit Requirements;
- validated EvidenceBindings;
- complete request-scoped bounded current/in-scope candidate fragments, including unbound refs;
- source values/claims, trust class, authority rank, scope, and temporal metadata.

### Output

Typed ref pairs, proposition/topic, contradiction type, severity, and non-authoritative model recommendation. Deterministic code validates the refs and computes precedence/resolution.

Each side also records truth relative to the Requirement proposition. A precedence winner may affect deterministic completeness only when it has a matching validated CRITICAL EvidenceBinding. The contradiction pass never promotes an unbound ref into canonical dependency state; an unbound winner leaves the compilation incomplete.

### Deterministic precedence

Only configured rules may resolve a conflict, such as current over historical revision, signed over draft approval, canonical record over cached snapshot, or an explicit mission override. Equal-authority unresolved CRITICAL conflict cannot silently accept.

The pass is executed even when Stage 2 produced incomplete evidence. Otherwise a missing binding can hide the very conflict needed to explain why approval is unsafe.

P0 passes the complete bounded candidate inventory to contradiction detection. It does not introduce an unevaluated semantic retrieval step whose omissions could recreate zero contradiction recall upstream.

## Deterministic Requirement Completeness

### Question

> Is each Stage 1 Requirement sufficiently evidenced by a direct or transitive validated path, after contradiction results are known?

### Input

- explicit Requirements with DIRECT/DERIVED_ALL proof mode and conjunction DAG;
- validated CRITICAL/SUPPORTING bindings;
- validated contradiction results;

### Output

Exactly one code-computed `RequirementAssessment` per explicit Requirement:

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

For DIRECT Requirements, the fixed truth table compares precedence-filtered CRITICAL bindings' `entailed_truth` with `expected_truth`; same-truth alternatives are ordered by authority rank/canonical ref to select one proof binding, while opposite truths remain a conflict. For DERIVED_ALL, all prerequisite assessments are conjoined. Joint evidence must be decomposed into DIRECT prerequisites rather than hidden in a multi-ref leaf. If evidence is insufficient, `missing_evidence_proposition` is deterministic text copied/formatted from the existing Requirement. Requirement omission quality is measured separately against frozen requirement ground truth.

## Reachability rule

For a DIRECT Requirement to count as evidenced, deterministic code must find current, authorized, validity-bearing CRITICAL support or counterevidence bindings after precedence. A DERIVED_ALL Requirement is evidenced only through all prerequisite assessments. Only DAG roots connect to the Decision; support paths therefore have the exact form Source → DIRECT assessment Claim → zero or more DERIVED_ALL assessment Claims → Decision.

`SUPPORTING`, `CONTEXTUAL`, `CONTRADICTED_BY`, stale, unauthorized, or rootless derived paths do not satisfy this rule. Conversely, a valid Source → Claim → Claim → Decision path is sufficient without a duplicate Source → derived Claim or intermediate Claim → Decision edge.

## Final gate effects

- missing/insufficient Requirement → `REJECTED_INCOMPLETE_REQUIREMENTS`;
- unresolved equal-authority CRITICAL contradiction → `NEEDS_HUMAN_REVIEW`;
- deterministically winning authority contradicts the proposed outcome → `REJECTED_CONTRADICTION`;
- semantic result inconsistent with trusted outcome class → `REJECTED_OUTCOME_CONSTRAINT`;
- only a fully compatible result can be `ACCEPTED` and canonicalized.

These are deterministic gate decisions over typed validated inputs, not direct model decisions.

For an accepted APPROVE, the gate selects every satisfied root closure. For an accepted DENY, it selects one failed root path by normalized canonical requirement key. Other analyzed siblings remain in the compiler record but do not become Runtime critical dependencies, preventing unrelated sibling mutations from invalidating the chosen denial rationale.

## Evaluation

Contradiction and completeness are scored separately:

- contradiction pair recall and critical-severity recall;
- requirement proposition recall;
- requirement assessment accuracy;
- critical dependency recall/precision;
- explicit stage-execution coverage;
- disposition and accepted-case coverage.

The benchmark must expose safe-by-rejection behavior. A zero stale-escape rate over one accepted case is not proof of compiler usefulness.
