# Module 01 stale-escape analysis

**Date:** 2026-08-19

**Historical metric:** 58/72 = 80.56%

**Finding:** evaluator conflates `NOT_ACCEPTED` with an accepted decision remaining non-stale

## Conclusion

None of the 58 historical “stale escapes” is an accepted Runtime decision that remained `VALID`.

All 58 compilations are blocked. `evaluate_runtime_mutation` returns `False` immediately for any non-`ACCEPTED` prediction, before it constructs a Runtime repository, accepts a decision, emits an artifact-change event, or reads `DecisionStatus`. `measure` then counts that `False` as a stale escape whenever the case ground truth expects staleness.

The actual chain for all 58 is:

```text
ground-truth material mutation
→ proposal union usually contains the mutated ref (57/58)
→ compilation is not ACCEPTED
→ canonical critical refs = ∅
→ Runtime edges = ∅
→ mutation event = NOT_EXECUTED
→ Runtime Decision = ABSENT
→ evaluator boolean = false
→ legacy metric records “stale escape”
```

Conditional Runtime behavior is correct on the persisted accepted records:

- 14/14 accepted expected-stale decisions become `STALE`;
- 6/6 accepted expected-unchanged decisions remain non-stale;
- an independent offline replay from persisted accepted refs reproduces all 20 booleans.

This does not make the product acceptable. It replaces one misleading aggregate with two honest failures/successes:

- acceptance coverage among expected-stale cases: `14/72 = 19.44%` — severe compiler usability failure;
- accepted-only stale escape: `0/14 = 0%` — no observed Runtime propagation failure, with a small accepted denominator.

The historical report remains immutable and must be preserved.

## Root-cause codes

| Code | Meaning |
|---|---|
| `E-BLOCK-AS-ESCAPE` | Evaluator returns `False` for a blocked compilation and metric counts it as an escape. Present in all 58. |
| `C-INCOMPLETE` | Compilation disposition is `REJECTED_INCOMPLETE_DEPENDENCIES`. |
| `C-INVALID-REF` | Compilation disposition is `REJECTED_INVALID_REFERENCE`. |
| `C-SCHEMA` | Compilation disposition is `REJECTED_SCHEMA`. |
| `C-STALE-REF` | Compilation disposition is `REJECTED_STALE_SOURCE`. |
| `D-EXTRACTION-MISS` | The exact mutated required ref is absent from proposal union. Present only in `vendor-onboarding-012`. |
| `O-STAGE-TRACE-MISSING` | Historical evidence cannot split reasoner refs from critic additions or show validator/critic findings and canonical relations. Present in all 58. |

Aggregate secondary causes:

| Disposition | Count | Mutated ref in proposal union |
|---|---:|---:|
| `REJECTED_INCOMPLETE_DEPENDENCIES` | 46 | 46/46 |
| `REJECTED_INVALID_REFERENCE` | 8 | 7/8 |
| `REJECTED_SCHEMA` | 2 | 2/2 |
| `REJECTED_STALE_SOURCE` | 2 | 2/2 |

## Evidence notation and observability limit

For readability, a case-local canonical source is shown as:

```text
artifact-role@revision#logical-path
```

For example, `primary@v13#$.clause` uniquely maps to the fully representation-qualified ref in that case's source inventory. `INVALID:...` is printed verbatim because it has no inventory mapping.

The historical JSON stores only `predicted_critical_refs`, which is the union of reasoner CRITICAL refs and valid CRITICAL critic missing-dependency candidates. It does not store the two inputs separately. Therefore every sampled row truthfully reports:

```text
reasoner refs: NOT_PERSISTED
critic additions: NOT_PERSISTED
proposal union: shown below
```

It also omits `accepted_dependency_edges`. For these 30 blocked cases that omission is not ambiguous: canonicalization never occurs, so canonical refs and Runtime edges are both empty.

## Stratified case trace — privileged access

All rows also carry `E-BLOCK-AS-ESCAPE` and `O-STAGE-TRACE-MISSING`.

| Case | Class | GT mutation | Required critical | Proposal union | Canonical critical | Runtime edge/event/final state | Secondary code |
|---|---|---|---|---|---|---|---|
| privileged-access-002 | clean negative | primary@r13#$.clause | primary@r13#$.clause | primary@r13#$.clause; support@r7#$.clause | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| privileged-access-003 | critical omission | primary@v13#$.clause | primary@v13#$.clause; support@r7#$.clause | same two refs | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| privileged-access-005 | obsolete revision | versioned-policy@v13#$.clause | same | same | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| privileged-access-009 | multiple dependencies | primary@v13#$.clause | primary; support; third-critical | same three refs | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| privileged-access-010 | narrow clause | wide-policy@v13#$.binding_clause | same | binding_clause; scope | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| privileged-access-011 | clean positive | primary@v13#$.clause | same | primary; support | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| privileged-access-012 | clean negative | primary@r13#$.clause | same | primary; support | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| privileged-access-013 | critical omission | primary@v13#$.clause | primary; support | same two refs | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| privileged-access-015 | obsolete revision | versioned-policy@v13#$.clause | same | same | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| privileged-access-020 | narrow clause | wide-policy@v13#$.binding_clause | same | binding_clause; scope | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |

Privileged aggregate: 19 legacy escapes; 19/19 blocked; mutated ref present in proposal union 19/19.

## Stratified case trace — production release

All rows also carry `E-BLOCK-AS-ESCAPE` and `O-STAGE-TRACE-MISSING`.

| Case | Class | GT mutation | Required critical | Proposal union | Canonical critical | Runtime edge/event/final state | Secondary code |
|---|---|---|---|---|---|---|---|
| production-release-001 | clean positive | primary@v13#$.clause | same | primary; support | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| production-release-002 | clean negative | primary@r13#$.clause | same | primary; support | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| production-release-005 | obsolete revision | versioned-policy@v13#$.clause | same | same | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| production-release-010 | narrow clause | wide-policy@v13#$.binding_clause | same | binding_clause; scope | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| production-release-012 | clean negative | primary@r13#$.clause | same | same | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| production-release-013 | critical omission | primary@v13#$.clause | primary; support | same two refs | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| production-release-015 | obsolete revision | versioned-policy@v13#$.clause | same | same | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-SCHEMA |
| production-release-020 | narrow clause | wide-policy@v13#$.binding_clause | same | appendix; binding_clause; scope | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| production-release-022 | clean negative | primary@r13#$.clause | same | primary; support | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| production-release-023 | critical omission | primary@v13#$.clause | primary; support | same two refs | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |

Release aggregate: 17 legacy escapes; 17/17 blocked; mutated ref present in proposal union 17/17.

## Stratified case trace — vendor onboarding

All rows also carry `E-BLOCK-AS-ESCAPE` and `O-STAGE-TRACE-MISSING`.

| Case | Class | GT mutation | Required critical | Proposal union | Canonical critical | Runtime edge/event/final state | Secondary code |
|---|---|---|---|---|---|---|---|
| vendor-onboarding-001 | clean positive | primary@v13#$.clause | same | primary; support | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| vendor-onboarding-002 | clean negative | primary@r13#$.clause | same | same | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| vendor-onboarding-003 | critical omission | primary@v13#$.clause | primary; support | same two refs | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| vendor-onboarding-005 | obsolete revision | versioned-policy@v13#$.clause | same | same | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-STALE-REF |
| vendor-onboarding-009 | multiple dependencies | primary@v13#$.clause | primary; support; third-critical | same three refs | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| vendor-onboarding-010 | narrow clause | wide-policy@v13#$.binding_clause | same | appendix; binding_clause; scope | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| vendor-onboarding-011 | clean positive | primary@v13#$.clause | same | malformed primary; primary; support | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INVALID-REF |
| vendor-onboarding-012 | clean negative | primary@r13#$.clause | same | malformed primary; support; exact mutation ref absent | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INVALID-REF + D-EXTRACTION-MISS |
| vendor-onboarding-013 | critical omission | primary@v13#$.clause | primary; support | same two refs | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |
| vendor-onboarding-015 | obsolete revision | versioned-policy@v13#$.clause | same | same | ∅ | ∅ / NOT_EXECUTED / ABSENT | C-INCOMPLETE |

Vendor aggregate: 22 legacy escapes; 22/22 blocked; mutated ref present in proposal union 21/22.

## Full-chain code audit

### Proposal union versus canonical refs

`ModelCompilerSubject` builds `critical_refs` from draft CRITICAL dependencies plus known CRITICAL critic missing candidates. The critic cannot edit the draft. A CRITICAL missing finding sets `REJECTED_INCOMPLETE_DEPENDENCIES`; canonicalization only runs when neither validation nor review blocks. Therefore critic recovery can raise proposal recall while simultaneously leaving canonical refs empty.

Observed separation:

```text
proposal-union refs: 252
accepted canonical critical refs: 45
accepted cases: 20
blocked cases: 100
```

### Relation types and accepted materiality

Runtime invalidation accepts `GOVERNED_BY`, `SUPPORTED_BY`, `DERIVED_FROM`, and `REQUIRES` as direct invalidation relations, and only traverses CRITICAL edges. `RuntimeAcceptanceService` preserves the canonical relation and maps `Materiality.CRITICAL` to `DependencyEdge.critical=true`.

The historical report does not persist accepted edge tuples, so exact relation-level inspection is impossible from evidence alone. Still, all 20 accepted mutation results replay correctly from persisted accepted refs using direct CRITICAL support edges. No accepted-record evidence points to relation propagation failure.

### Fragment-to-artifact and historical/current mapping

The evaluator creates current Runtime artifacts from current case sources, binds evidence by exact canonical `source_ref`, and sends both the logical artifact identity and `changed_source_ref`. Invalidation filters evidence by the same artifact and exact fragment ref. Accepted cases demonstrate this mapping works for the tested paths.

Blocked cases never reach this code. The two legacy `REJECTED_STALE_SOURCE` escapes therefore do not demonstrate a historical/current Runtime mapping failure.

### Mutation-ground-truth granularity

Expected-stale mutations point to a required critical fragment. Expected-unchanged mutations do not test the dominant false-positive class:

- 12 expected-unchanged cases are blocked contradictions;
- the remaining 36 mutate a forbidden distractor, near-match, or injection fragment;
- none mutates one of the 51 acceptable-supporting refs promoted to CRITICAL.

The benchmark should retain all existing mutations and add paired supporting-ref mutations. Otherwise unnecessary invalidation can stay zero while canonical precision remains poor.

## Required evaluator correction

Do not overwrite `module-01-dependency-compiler.json`. Introduce a versioned result for future experiments with:

```text
mutation_terminal = STALE | VALID | NOT_ACCEPTED | EVALUATION_ERROR
acceptance_coverage
accepted_only_stale_escape_rate
legacy_stale_escape_rate
accepted_only_unnecessary_invalidation_rate
reasoner_critical_refs
critic_added_refs
canonical_edges(source, target, relation, materiality)
runtime_event_id
final_decision_status
```

Low acceptance must remain a hard failure. Excluding `NOT_ACCEPTED` from accepted-only staleness is not permission to hide it; it must appear as a separate denominator and gate.

## Final root-cause allocation

For the 58 historical escapes:

| Candidate cause | Finding |
|---|---|
| dependency extraction failure | 1/58 exact mutated refs missing from proposal union; not primary |
| materiality classification failure | common elsewhere, but not the direct cause of these 58 because no graph is accepted |
| canonicalization failure | no; canonicalization is not executed for blocked cases |
| Runtime edge-semantics failure | no evidence; 20/20 accepted mutation directions are correct |
| benchmark/evaluation bug | **yes, 58/58** blocked cases are mislabeled as Runtime escapes |
| compiler acceptance failure | **yes, 58/58** expected-stale cases lack an accepted graph; 46 are labeled incomplete |

The honest diagnosis is a combination of evaluator semantics and poor compiler acceptance, not a Runtime invalidation failure.
