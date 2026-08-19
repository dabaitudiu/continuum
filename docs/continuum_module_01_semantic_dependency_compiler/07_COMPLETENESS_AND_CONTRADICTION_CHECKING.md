# 07 — Requirement Coverage, Contradiction, and Completeness

## Architecture decision

The old Completeness Critic remains rejected. Revision 3 replaces it with six disjoint contracts:

1. authoritative universe + fragment-complete normalization prove the obligation input inventory;
2. independent governing-obligation coverage proposes typed semantic Requirements/applicability bindings;
3. deterministic applicability proof and reconciliation create justified exclusions/effective Requirements;
4. partitioned independent contradiction observation covers applicability and requirement predicates;
5. deterministic proof selection/completeness derives materiality、contradiction impact and RequirementAssessments;
6. deterministic gate and selective provenance mapping decide Runtime eligibility.

No pass emits `UNKNOWN_SOURCE_REQUIRED`, edits canonical state, or decides final disposition.

## Independent Requirement Coverage

### Question

> Given this request、decision class and the universe-rooted、normalization-complete governing inventory, which material obligations may apply and what current facts support their applicability?

### Independence boundary

The pass does not receive Stage-1 decomposition or proposed outcome. It sees every obligation from the validated `RuleNormalizationManifest + SourceSetManifest` chain, including pre-registered applicability predicates. Large inventories use deterministic disjoint partitions and complete receipts；partial coverage blocks rather than silently sampling.

### Output and reconciliation

It outputs one advisory observation、candidate applicability bindings and Requirement candidates for every representable normalized obligation. Stage 1C validates only provisional proof；Stage 3 independently covers applicability conflicts；Stage 4 finalizes APPLICABLE only when all conditions remain true and NOT_APPLICABLE only from a stable determinate false guard. Both persist `ApplicabilityJustification`；otherwise INDETERMINATE fails closed. A model N/A label cannot suppress a Requirement before those passes。

Deterministic reconciliation compares Stage 1A and coverage by semantic key:

- match → origin `BOTH`;
- valid coverage-only omission → retain as conditional `COVERAGE_PASS` candidate and run downstream binding/contradiction/completeness；Stage 4 applicability decides effective membership;
- incompatible expected states/topology → fail-closed coverage conflict;
- unsupported logic/predicate → typed `REJECTED_UNSUPPORTED_LOGIC | REJECTED_UNSUPPORTED_PREDICATE`;
- unknown/fabricated ref → structural failure.

This catches a Stage-1 omission in production without asking a vague critic to find arbitrary problems.

## Independent Contradiction Pass

### Input

- reconciled supported Requirement candidates plus every applicability predicate/guard;
- complete contradiction-eligible ref inventory from the manifest;
- deterministic coverage plan and hard limits;
- source content、authority/scope/time metadata and stable predicate contracts.

The pass is independent of Stage-2 bindings.

### Coverage-preserving map/reduce

Deterministic partitioning assigns every eligible ref exactly once. Each map call emits typed observations and a receipt. Reducer verifies every expected partition、input hash and processed-ref union before semantic reduction.

Determinate opposing observations are globally joined by stable predicate identity **and entailment target**, so sources in different partitions can conflict without mixing applicability with business state. `INDETERMINATE` is retained as ambiguity but does not form a false binary contradiction。

If hard limits、timeout、truncation、missing receipt or union mismatch prevent complete coverage, the result is `RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE`. It is never reported as a zero-contradiction success.

Observations are not binding candidates. An unbound precedence winner may make the conflict/omission visible but cannot be promoted to proof or Runtime provenance by the contradiction pass；without a matching validated Stage-2 binding, completeness remains insufficient.

### Deterministic precedence and impact

Only versioned policy may resolve authority. The model's severity and resolution recommendation are advisory.

Conflict impact is `VALIDITY_CRITICAL` iff:

1. the affected applicability guard/effective Requirement reaches a Decision root;
2. at least one side is eligible for a required proof role/guard; and
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
| every applicable obligation has a validated APPLICABLE justification and every state role matches expected state | `SATISFIED` |
| applicability is proved and covered state evidence proves the opposite, no unresolved critical conflict | `UNSATISFIED` |
| unresolved validity-critical contradiction | `CONTRADICTED` |
| missing role or only indeterminate evidence | `INSUFFICIENT_EVIDENCE` |

Normalized obligation、applicability evidence and factual state are not interchangeable. A conflict with a selected APPLICABLE/NOT_APPLICABLE guard is validity-critical, not an ordinary business-condition DENY。

### ALL_OF

Priority is: any CONTRADICTED → CONTRADICTED; else any UNSATISFIED → UNSATISFIED; else all SATISFIED → SATISFIED; else INSUFFICIENT_EVIDENCE.

Every effective Requirement receives exactly one code-computed assessment. Coverage pass—not completeness—may introduce a missing semantic Requirement. Completeness itself cannot invent Requirements、refs、bindings or placeholder evidence.

## Reachability

Selected proof uses:

```text
Source → DIRECT Claim → zero or more ALL_OF Claims → Decision
```

A valid transitive path is sufficient. No duplicate Source → derived Claim or intermediate Claim → Decision edge is required. Applicability facts and selective policy/coverage guards use parallel critical paths；full manifests/receipts remain audit derivation。

## Gate effects

- applicable unsupported logic → `REJECTED_UNSUPPORTED_LOGIC`;
- applicable unsupported predicate → `REJECTED_UNSUPPORTED_PREDICATE`;
- universe/normalization/source/partition coverage incomplete → execution `RUN_BLOCKED`;
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
- universe/normalization/source/partition coverage completion;
- APPLICABLE/N/A proof completeness and transition stale recall;
- RequirementAssessment accuracy;
- disposition and accepted-case coverage;
- selective policy/rule/coverage invalidation and `coverage_induced_unnecessary_invalidation_rate`.

Safe rejection over almost every case is not proof of compiler usefulness.
