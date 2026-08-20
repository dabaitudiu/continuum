# 07 — Requirement Coverage, Contradiction, and Completeness

## Architecture decision

The old Completeness Critic remains rejected. The Revision-6 completeness/verification design is frozen within P0-1～P0-37. Revision 7 does not change its semantics；it only adds the P0-38/P0-39 deterministic identity and Decision-acceptance guards around it:

1. governed observations prove proposal/compiler reads came from one executable world/epoch；
2. authoritative universe + fragment-complete normalization prove the obligation input inventory;
3. approved reusable templates plus trusted entity roles deterministically instantiate every semantic Requirement/applicability/upstream target；
4. exact `UpstreamDecisionBinding`s preserve first-class acyclic `downstream Decision --REQUIRES--> upstream Decision` proof；
5. no-top-K `EvidenceCoveragePlan` and fragment receipts cover Evidence/applicability discovery；
6. scalable independent fragment contradiction observation guarantees direct same-predicate conflicts only；
7. narrow independent disposition-critical verification covers selected proof/applicability and both material sides of critical direct conflicts；
8. deterministic applicability/proof/completeness derives materiality、impact and RequirementAssessments；
9. temporal guards plus contiguous semantic-sequence ChangeSet/per-envelope authorization define lifetime without fleet-wide writes；
10. deterministic proposal Gate decides proposal admission without authoring a business outcome；
11. Side Effect Ledger final reauthorization atomically linearizes `INTENDED→EXECUTING`, then uses external idempotency/reconciliation outside the transaction.

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
- unsupported logic/predicate/cross-predicate relation → typed `REJECTED_UNSUPPORTED_LOGIC | REJECTED_UNSUPPORTED_PREDICATE`;
- `NOT_EXISTS`/retrieval-derived absence → typed `ABSENCE_PROOF_NOT_SUPPORTED_P0`;
- model-invented target/entity/ref → compiler/model execution failure with no proposal-admission disposition.

This catches a domain-proposal/rationale omission by construction without making the compiler a second Decision Maker or a vague critic。

## Complete Evidence and Applicability Discovery

`EvidenceCoveragePlan` contains all instantiated Requirement/applicability targets and every fragment certified eligible by versioned entity/source-role/namespace rules. It has no top-K field. Deterministic partitions yield one observation/ref；empty means processed/no match reported. Best-effort retrieval or preflight capacity is `RUN_BLOCKED`；post-call partial/malformed coverage is `RUN_FAILED` with no proposal-admission disposition；complete no-match is insufficient evidence, never absence proof。

## Independent Contradiction Pass

### Input

- template-instantiated Requirement candidates plus every applicability predicate/guard;
- complete contradiction-eligible ref inventory from the manifest;
- deterministic coverage plan and hard limits;
- source content、authority/scope/time metadata and stable predicate contracts.

The pass is independent of Stage-2 bindings.

### Coverage-preserving map/reduce

Deterministic partitioning assigns every eligible ref exactly once. Each map call emits one `FragmentSemanticObservation` per ref with actual `matched_predicates[]` and a receipt. Reducer verifies every expected partition、target/input hash、wrapper and processed-ref union before semantic reduction.

Determinate opposing matches are globally joined by the same stable predicate **plus entity、entailment target and overlapping normalized scope/time**, so sources in different partitions can conflict without mixing entities/applicability/business state. `INDETERMINATE` is retained as ambiguity but does not form a false binary contradiction. Output complexity is O(fragments+actual matches), not a negative cross-product。

Cross-predicate logical relations are outside this contradiction guarantee. They must be represented by a versioned decision-class/RequirementTemplate evaluator that emits a normalized constraint predicate；otherwise `UNSUPPORTED_CROSS_PREDICATE_RELATION_P0` fails closed. Benchmark reports direct contradictions、registered constraints and unsupported relations separately。

If preflight hard limits cannot represent complete coverage, the result is `RUN_BLOCKED`. Timeout、truncation、malformed/missing receipt or union mismatch after invocation is `RUN_FAILED` with no proposal-admission disposition. Neither may be reported as a zero-contradiction success。

Observations are not binding candidates. An unbound precedence winner may make the conflict/omission visible but cannot be promoted to proof or Runtime provenance by the contradiction pass；without a matching validated Stage-2 binding, completeness remains insufficient.

### Deterministic precedence and impact

Only versioned policy may resolve authority. The Revision-6 model schema has no severity/resolution authority.

Conflict impact is `VALIDITY_CRITICAL` iff:

1. the affected applicability guard/effective Requirement reaches a Decision root;
2. at least one side is eligible for a required proof role/guard; and
3. authority/preference state is unresolved or changes the truth available to deterministic proof selection.

Otherwise it is `NON_BLOCKING`. Thus a model cannot downgrade a blocking conflict to SUPPORTING.

## Deterministic Proof Selection and Disposition-Critical Verification

The model never supplies canonical CRITICAL/SUPPORTING. For each contract-derived enterprise proof role, code filters and orders candidates deterministically. A separate verifier then receives only the exact selected fragment、target/entity、claimed entailment/value and normalized semantics。

- verifier `CONFIRMED` selected necessary proof → `CRITICAL`;
- verifier `REFUTED | INDETERMINATE` → analysis-only and deterministic next-candidate selection；
- verifier protocol/transport failure → `RUN_FAILED`, never semantic refutation；
- unselected explanatory candidate → `SUPPORTING`;
- indeterminate/ineligible/irrelevant candidate → analysis-only;
- absent confirmed candidate for a required role → `INSUFFICIENT_EVIDENCE`;
- exact accepted/current/VALID upstream Decision → `UPSTREAM_DECISION` proof and first-class downstream-to-upstream `REQUIRES` critical edge；stale/superseded/invalid never satisfies and a successor is never auto-bound。Runtime rejects exact-ID/lineage cycles before acceptance。

For a provisional `VALIDITY_CRITICAL` direct conflict, code also verifies both exact model-interpreted observations. Both `CONFIRMED` receipts are required before the conflict is a confirmed blocking `Contradiction`. `REFUTED` removes/recomputes；`INDETERMINATE` becomes typed semantic uncertainty and admission review, not a confirmed contradiction. The verifier never discovers conflicts or chooses impact/disposition。

An incorrect model label therefore cannot suppress invalidation on a proof actually selected by code, and one hallucinated contradiction observation cannot masquerade as a confirmed conflict。

## Deterministic Requirement Completeness

### DIRECT_ATOM

| Condition | Assessment |
|---|---|
| every applicable obligation has a verified APPLICABLE justification、every enterprise proof is CONFIRMED、every state role matches expected state and required upstream Decisions are VALID | `SATISFIED` |
| applicability is proved and covered state evidence proves the opposite, no unresolved critical conflict | `UNSATISFIED` |
| unresolved validity-critical contradiction with both material sides CONFIRMED | `CONTRADICTED` |
| otherwise-critical contradiction side is INDETERMINATE | `SEMANTIC_UNCERTAINTY`；not confirmed contradiction |
| missing/unverified role、only indeterminate evidence or invalid upstream Decision | `INSUFFICIENT_EVIDENCE` |

Normalized obligation、applicability evidence and factual state are not interchangeable. A conflict with a selected APPLICABLE/NOT_APPLICABLE guard is validity-critical, not an ordinary business-condition DENY。

### ALL_OF

Priority is: any CONTRADICTED → CONTRADICTED; else any SEMANTIC_UNCERTAINTY → SEMANTIC_UNCERTAINTY; else any UNSATISFIED → UNSATISFIED; else all SATISFIED → SATISFIED; else INSUFFICIENT_EVIDENCE.

Every effective Requirement receives exactly one code-computed assessment. Trusted template instantiation—not completeness—defines Requirements. Completeness itself cannot invent Requirements、refs、bindings or placeholder evidence.

## Reachability

Selected proof uses:

```text
Source → DIRECT Claim → zero or more ALL_OF Claims → Decision
Upstream Decision → Downstream Decision
```

A valid transitive source/claim path is sufficient；no redundant direct source edge is required. A contract-required upstream Decision is not a source and keeps its separate `downstream --REQUIRES--> upstream` critical edge；invalidation follows the reverse index. Applicability facts and selective policy/coverage guards use parallel critical paths；full manifests/receipts remain audit derivation。

## Gate effects

- applicable unsupported logic → `REJECTED_UNSUPPORTED_LOGIC`;
- applicable unsupported predicate → `REJECTED_UNSUPPORTED_PREDICATE`;
- universe/normalization/source capacity unavailable before calls → execution `RUN_BLOCKED`；post-call model/protocol/receipt failure → `RUN_FAILED`，both without proposal-admission disposition;
- unresolved template/accounting conflict → `REJECTED_REQUIREMENT_COVERAGE`;
- insufficient determinate evidence → `REJECTED_INCOMPLETE_REQUIREMENTS` or `NEEDS_HUMAN_REVIEW`;
- confirmed unresolved validity-critical contradiction or typed critical semantic uncertainty → `NEEDS_HUMAN_REVIEW`；the latter is not counted as confirmed contradiction;
- supplied proposal outcome mismatch → `REJECTED_OUTCOME_CONSTRAINT` / `REJECTED_CONTRADICTION`，with no replacement Decision;
- only fully compatible APPROVE/DENY can be `ACCEPTED`.

These are proposal-admission dispositions. For example, immutable business proposal `APPROVED` plus insufficient evidence means `REJECTED_INCOMPLETE_REQUIREMENTS`/not admitted, never a Continuum-authored business `DENIED`。

DENY proof selection uses stable predicate/source/topology identity; lexical proposition text is forbidden.

## Evaluation

Report separately:

- template/obligation accounting、Requirement recall/precision and K6 case-specific/general reuse metrics;
- proposal validation accuracy and outcome-substitution rate（target 0）；
- entity-binding/cross-entity canonicalization errors（target 0）；
- Evidence/applicability receipt completion、semantic match recall/precision and no-match false-negative rate；
- entailment confusion including INDETERMINATE;
- proof-selected CRITICAL recall/precision;
- same-predicate contradiction pair and deterministic-impact recall；registered/unsupported cross-predicate categories separately;
- N0/N1 disposition-critical verification precision、false-proof acceptance、false contradiction block、confirmed contradiction precision、human-review false positives、reselection/re-reduction and calls/cost/latency delta;
- governed-read isolation、upstream Decision binding/transitive stale and result-class confusion;
- universe/normalization/source/Evidence/contradiction coverage completion and hard-limit usage;
- APPLICABLE/N/A proof completeness and transition stale recall;
- RequirementAssessment accuracy;
- disposition and accepted-case coverage;
- selective policy/rule/coverage invalidation and `coverage_induced_unnecessary_invalidation_rate`.
- temporal-expiry、semantic-sequence and authorization-to-`EXECUTING` escape rates（all target 0）；sequence replay/range continuity、Side Effect Ledger cancellation/reconciliation and publication required Decision-row writes target 0；
- per-domain/class operational success/context-block and median/p95 calls、tokens、latency、settled cost。

Safe rejection over almost every case is not proof of compiler usefulness.
