# 07 — Requirement Coverage, Contradiction, and Completeness

## Architecture decision

The old Completeness Critic remains rejected. Revision 2 replaces it with four disjoint contracts:

1. independent governing-obligation coverage proposes typed semantic Requirements omitted by decomposition;
2. deterministic reconciliation creates the effective Requirement set;
3. partitioned independent contradiction observation covers the complete source inventory;
4. deterministic proof selection/completeness derives materiality、contradiction impact and RequirementAssessments.

No pass emits `UNKNOWN_SOURCE_REQUIRED`, edits canonical state, or decides final disposition.

## Independent Requirement Coverage

### Question

> Given this request、decision class and the complete current governing-source universe, which material governing obligations apply?

### Independence boundary

The pass does not receive Stage-1 decomposition or proposed outcome. It cannot be biased toward confirming the initial requirement set. It sees every governing obligation declared by the validated SourceSetManifest plus normalized rule identity/logic metadata. Large inventories use deterministic disjoint partitions and complete receipt aggregation；partial coverage blocks rather than silently sampling.

### Output and reconciliation

It outputs one `RequirementCoverageObservation` per normalized governing obligation、a receipt covering the exact manifest inventory, and `RequirementCoverageCandidate[]` for APPLICABLE obligations. Observations use `APPLICABLE | NOT_APPLICABLE | INDETERMINATE`; INDETERMINATE cannot normally accept and incomplete receipts cannot masquerade as no omission.

Deterministic reconciliation compares Stage 1A and coverage by semantic key:

- match → origin `BOTH`;
- valid coverage-only omission → add to effective set as `COVERAGE_PASS` and run downstream binding/contradiction/completeness;
- incompatible expected states/topology → fail-closed coverage conflict;
- unsupported logic → typed `REJECTED_UNSUPPORTED_LOGIC`;
- unknown/fabricated ref → structural failure.

This catches a Stage-1 omission in production without asking a vague critic to find arbitrary problems.

## Independent Contradiction Pass

### Input

- reconciled effective Requirements;
- complete contradiction-eligible ref inventory from the manifest;
- deterministic coverage plan and hard limits;
- source content、authority/scope/time metadata and stable predicate contracts.

The pass is independent of Stage-2 bindings.

### Coverage-preserving map/reduce

Deterministic partitioning assigns every eligible ref exactly once. Each map call emits typed observations and a receipt. Reducer verifies every expected partition、input hash and processed-ref union before semantic reduction.

Determinate opposing observations are globally joined by stable predicate identity **and entailment target**, so sources in different partitions can conflict without mixing obligation applicability with factual state. `INDETERMINATE` is retained as ambiguity but does not form a false binary contradiction.

If hard limits、timeout、truncation、missing receipt or union mismatch prevent complete coverage, the result is `RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE`. It is never reported as a zero-contradiction success.

Observations are not binding candidates. An unbound precedence winner may make the conflict/omission visible but cannot be promoted to proof or Runtime provenance by the contradiction pass；without a matching validated Stage-2 binding, completeness remains insufficient.

### Deterministic precedence and impact

Only versioned policy may resolve authority. The model's severity and resolution recommendation are advisory.

Conflict impact is `VALIDITY_CRITICAL` iff:

1. the affected effective Requirement reaches a Decision root;
2. at least one side is eligible for a required proof role; and
3. authority/preference state is unresolved or changes the truth available to deterministic proof selection.

Otherwise it is `NON_BLOCKING`. Thus a model cannot downgrade a blocking conflict to SUPPORTING.

## Deterministic Proof Selection

The model never supplies canonical CRITICAL/SUPPORTING. For each contract-derived proof role, code filters bindings by ref/scope/time/authority/role/predicate eligibility and determinate entailment, applies precedence, then orders by versioned proof policy and stable source identity.

- selected necessary proof → `CRITICAL`;
- unselected explanatory candidate → `SUPPORTING`;
- indeterminate/ineligible/irrelevant candidate → analysis-only;
- absent determinate candidate for a required role → `INSUFFICIENT_EVIDENCE`.

An incorrect model label therefore cannot suppress invalidation on a proof actually selected by code.

## Deterministic Requirement Completeness

### DIRECT_ATOM

| Condition | Assessment |
|---|---|
| every applicability role is TRUE and every state role matches expected state | `SATISFIED` |
| every applicability role is TRUE and covered state evidence proves the opposite, no unresolved critical conflict | `UNSATISFIED` |
| unresolved validity-critical contradiction | `CONTRADICTED` |
| missing role or only indeterminate evidence | `INSUFFICIENT_EVIDENCE` |

Applicable governing evidence and factual state are not interchangeable. Governing applicability FALSE against an APPLICABLE reconciled obligation is a reconciliation conflict, not an ordinary business-condition DENY.

### ALL_OF

Priority is: any CONTRADICTED → CONTRADICTED; else any UNSATISFIED → UNSATISFIED; else all SATISFIED → SATISFIED; else INSUFFICIENT_EVIDENCE.

Every effective Requirement receives exactly one code-computed assessment. Coverage pass—not completeness—may introduce a missing semantic Requirement. Completeness itself cannot invent Requirements、refs、bindings or placeholder evidence.

## Reachability

Selected proof uses:

```text
Source → DIRECT Claim → zero or more ALL_OF Claims → Decision
```

A valid transitive path is sufficient. No duplicate Source → derived Claim or intermediate Claim → Decision edge is required. Policy/manifest provenance uses a parallel critical path through `DecisionInterpretation` Claim.

## Gate effects

- applicable unsupported logic → `REJECTED_UNSUPPORTED_LOGIC`;
- source/partition coverage incomplete → execution `RUN_BLOCKED`;
- unresolved requirement coverage conflict → `REJECTED_REQUIREMENT_COVERAGE`;
- insufficient determinate evidence → `REJECTED_INCOMPLETE_REQUIREMENTS` or `NEEDS_HUMAN_REVIEW`;
- unresolved validity-critical contradiction → `NEEDS_HUMAN_REVIEW`;
- outcome mismatch → `REJECTED_OUTCOME_CONSTRAINT` / `REJECTED_CONTRADICTION`;
- only fully compatible APPROVE/DENY can be `ACCEPTED`.

DENY proof selection uses stable predicate/source/topology identity; lexical proposition text is forbidden.

## Evaluation

Report separately:

- Stage-1 decomposition recall;
- coverage-only omission recovery and false-candidate rate;
- reconciled Requirement recall/precision;
- entailment confusion including INDETERMINATE;
- proof-selected CRITICAL recall/precision;
- contradiction pair and deterministic-impact recall;
- source/partition coverage completion;
- RequirementAssessment accuracy;
- disposition and accepted-case coverage;
- policy/manifest invalidation behavior.

Safe rejection over almost every case is not proof of compiler usefulness.
