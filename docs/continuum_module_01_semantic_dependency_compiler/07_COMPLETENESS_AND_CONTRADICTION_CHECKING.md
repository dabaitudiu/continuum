# 07 — Requirement Coverage, Contradiction, and Completeness

## Architecture decision

The old Completeness Critic remains rejected. Revision 4 replaces it with seven disjoint contracts:

1. authoritative universe + fragment-complete normalization prove the obligation input inventory;
2. approved reusable templates plus trusted entity roles deterministically instantiate every semantic Requirement/applicability target；
3. no-top-K `EvidenceCoveragePlan` and fragment receipts cover Evidence/applicability discovery；
4. scalable independent fragment contradiction observation covers the same target semantics without ref×predicate negative output；
5. deterministic applicability/proof/completeness derives materiality、impact and RequirementAssessments；
6. temporal guards and epoch-bound validity envelope define authorization lifetime；
7. deterministic proposal Gate and selective provenance mapping decide Runtime eligibility without outcome substitution.

No pass emits `UNKNOWN_SOURCE_REQUIRED`, edits canonical state, or decides final disposition.

## Trusted Requirement Authority and Complete Accounting

### Question

> Given this immutable proposal/entity context and the universe-rooted、normalization-complete governing inventory, did every approved reusable Requirement/applicability template instantiate exactly once?

### Authority boundary

`RuleNormalizationManifest.requirement_templates[]` and decision-class proposal-validity templates are the only authorities. Deterministic Stage 1 binds their subject/object roles through signed `DecisionEntityContext`. Domain-agent rationale and model output cannot add、replace or suppress Requirements；templates cannot contain case IDs、exact benchmark graphs/outcomes or concrete source revisions.

### Output and accounting

Each obligation/template gets one `RequirementInstantiationReceipt` containing instantiated Requirements、applicability target keys、entity context and status. Every candidate remains until Stage 4 finalizes APPLICABLE from all true conditions or NOT_APPLICABLE from a stable determinate false guard after contradiction；otherwise INDETERMINATE fails closed.

Accounting rules：

- every normalized obligation and decision-class template appears exactly once;
- reusable template + entity role binding deterministically defines semantic ID/topology;
- incompatible/duplicate/missing template or entity role → fail-closed coverage conflict;
- unsupported logic/predicate → typed `REJECTED_UNSUPPORTED_LOGIC | REJECTED_UNSUPPORTED_PREDICATE`;
- `NOT_EXISTS`/retrieval-derived absence → typed `ABSENCE_PROOF_NOT_SUPPORTED_P0`;
- invented target/entity/ref → structural failure.

This catches a domain-proposal/rationale omission by construction without making the compiler a second Decision Maker or a vague critic。

## Complete Evidence and Applicability Discovery

`EvidenceCoveragePlan` contains all instantiated Requirement/applicability targets and every fragment certified eligible by versioned entity/source-role/namespace rules. It has no top-K field. Deterministic partitions yield one `FragmentEvidenceObservation` per ref with only actual matches；empty means processed/no match reported. Exact receipts prove processing coverage, while method-blind annotations measure semantic recall/precision. Partial、dense、over-limit or best-effort retrieval coverage is `RUN_BLOCKED`；complete no-match becomes insufficient evidence, never absence proof。

## Independent Contradiction Pass

### Input

- template-instantiated Requirement candidates plus every applicability predicate/guard;
- complete contradiction-eligible ref inventory from the manifest;
- deterministic coverage plan and hard limits;
- source content、authority/scope/time metadata and stable predicate contracts.

The pass is independent of Stage-2 bindings.

### Coverage-preserving map/reduce

Deterministic partitioning assigns every eligible ref exactly once. Each map call emits one `FragmentSemanticObservation` per ref with actual `matched_predicates[]` and a receipt. Reducer verifies every expected partition、target/input hash、wrapper and processed-ref union before semantic reduction.

Determinate opposing matches are globally joined by stable predicate **plus entity and entailment target**, so sources in different partitions can conflict without mixing entities/applicability/business state. `INDETERMINATE` is retained as ambiguity but does not form a false binary contradiction. Output complexity is O(fragments+actual matches), not a negative cross-product。

If executable hard limits、dense output、timeout、truncation、missing receipt or union mismatch prevent complete coverage, the result is `RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE`. It is never reported as a zero-contradiction success.

Observations are not binding candidates. An unbound precedence winner may make the conflict/omission visible but cannot be promoted to proof or Runtime provenance by the contradiction pass；without a matching validated Stage-2 binding, completeness remains insufficient.

### Deterministic precedence and impact

Only versioned policy may resolve authority. The Revision-4 model schema has no severity/resolution authority.

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

Every effective Requirement receives exactly one code-computed assessment. Trusted template instantiation—not completeness—defines Requirements. Completeness itself cannot invent Requirements、refs、bindings or placeholder evidence.

## Reachability

Selected proof uses:

```text
Source → DIRECT Claim → zero or more ALL_OF Claims → Decision
```

A valid transitive path is sufficient. No duplicate Source → derived Claim or intermediate Claim → Decision edge is required. Applicability facts and selective policy/coverage guards use parallel critical paths；full manifests/receipts remain audit derivation。

## Gate effects

- applicable unsupported logic → `REJECTED_UNSUPPORTED_LOGIC`;
- applicable unsupported predicate → `REJECTED_UNSUPPORTED_PREDICATE`;
- universe/normalization/source/Evidence/contradiction coverage incomplete → execution `RUN_BLOCKED`;
- unresolved template/accounting conflict → `REJECTED_REQUIREMENT_COVERAGE`;
- insufficient determinate evidence → `REJECTED_INCOMPLETE_REQUIREMENTS` or `NEEDS_HUMAN_REVIEW`;
- unresolved validity-critical contradiction → `NEEDS_HUMAN_REVIEW`;
- supplied proposal outcome mismatch → `REJECTED_OUTCOME_CONSTRAINT` / `REJECTED_CONTRADICTION`，with no replacement Decision;
- only fully compatible APPROVE/DENY can be `ACCEPTED`.

DENY proof selection uses stable predicate/source/topology identity; lexical proposition text is forbidden.

## Evaluation

Report separately:

- template/obligation accounting、Requirement recall/precision and K6 case-specific/general reuse metrics;
- proposal validation accuracy and outcome-substitution rate（target 0）；
- entity-binding/cross-entity canonicalization errors（target 0）；
- Evidence/applicability receipt completion、semantic match recall/precision and no-match false-negative rate；
- entailment confusion including INDETERMINATE;
- proof-selected CRITICAL recall/precision;
- contradiction pair and deterministic-impact recall;
- universe/normalization/source/Evidence/contradiction coverage completion and hard-limit usage;
- APPLICABLE/N/A proof completeness and transition stale recall;
- RequirementAssessment accuracy;
- disposition and accepted-case coverage;
- selective policy/rule/coverage invalidation and `coverage_induced_unnecessary_invalidation_rate`.
- temporal-expiry and semantic-epoch authorization escape rates（both target 0）。

Safe rejection over almost every case is not proof of compiler usefulness.
