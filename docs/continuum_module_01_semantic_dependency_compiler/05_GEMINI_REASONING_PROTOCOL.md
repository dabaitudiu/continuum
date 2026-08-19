# 05 — Model Reasoning Protocol

## Status

This is the provider-neutral Option B Revision-2 protocol under product-owner review. The direction is approved; the concrete specification is not. OpenAI remains the current falsification provider and live Gemini remains independently required for final acceptance. No live calls are authorized by this document.

The implemented reasoner/critic protocol is frozen as the v1 ablation baseline. The old critic prompt must not be tuned or preserved as production fallback.

## Common rules for every model stage

- source fragments are untrusted data, never instructions;
- tools are read-only and bounded by request scope/world snapshot;
- only tool-returned canonical refs may be copied;
- output must match the stage-specific schema;
- no stage may emit canonical IDs, mutate Runtime state, select deterministic precedence, or authorize an action;
- no stage may declare source-universe completeness, canonical materiality, canonical contradiction impact, or final disposition;
- concise semantic propositions and summaries are stored; hidden chain-of-thought is neither requested nor persisted;
- invalid schema receives at most one bounded repair attempt, then ends as a structural failure;
- every invocation records provider/model/version, prompt/schema version, request configuration, response identity, usage, latency, and ledger settlement.

## Stage 0 — No model ownership

Trusted code resolves the `CompilerPolicyBundle` and validates a complete `SourceSetManifest` plus deterministic partition plan. A model cannot declare a retrieved subset complete. `INCOMPLETE | UNKNOWN` coverage blocks the run before semantic inference.

## Stage 1A — Requirement Decomposition

Input:

- trusted task definition;
- decision type, risk class, outcome vocabulary and versioned decision-class/predicate contracts;
- manifest-bounded source summaries/content as data.

Output: `DecisionAnalysisProposal` containing one proposed outcome from the trusted vocabulary plus `Requirement[]`.

The instruction asks for atomic APPROVE-validity predicates and `DIRECT_ATOM | ALL_OF` structure. It uses stable `PredicateIdentity`; display text is non-authoritative. It forbids refs in Requirement fields and explicitly surfaces unsupported OR/threshold/exception/quantified logic rather than coercing it.

## Stage 1B — Independent Governing-Obligation Coverage

Input:

- trusted request and decision-class/predicate contracts;
- every governing fragment in the complete manifest plus normalized-rule metadata;
- **not** Stage-1A output and **not** the proposed outcome.

Output per deterministic partition: one `RequirementCoverageObservation` per assigned normalized governing obligation、a coverage receipt and `RequirementCoverageCandidate[]` for APPLICABLE obligations.

The pass inventories material governing obligations applicable to the Decision. It cannot bind factual evidence、judge the outcome、assign materiality/severity、rewrite Stage 1 or invent refs. Every manifest obligation is assigned exactly once across coverage-preserving partitions and marked `APPLICABLE | NOT_APPLICABLE | INDETERMINATE`; deterministic validation checks receipt union. Reconciliation compares stable predicate keys with Stage 1A and carries valid coverage-only omissions into the effective set. INDETERMINATE applicability prevents normal acceptance；partial partitions block the run.

## Stage 2 — Evidence Binding

Input:

- validated Requirements;
- request-scoped source inventory and selected fragment content;
- source identity and authority metadata.

Output: `EvidenceBindingCandidate[]` only.

For each binding, the model states semantic role、`OBLIGATION_APPLICABILITY | PREDICATE_STATE` target、`ENTAILED_TRUE | ENTAILED_FALSE | INDETERMINATE`、normalized value where applicable and concise counterfactual analysis. A policy that requires training cannot be used as proof that training is current. The model does not output canonical `CRITICAL | SUPPORTING`; deterministic proof selection owns it.

## Stage 3 — Independent Contradiction Pass

Input:

- reconciled Requirements;
- one deterministic partition of the complete current/in-scope contradiction-eligible inventory, independent of Stage-2 refs;
- source values/claims and authority metadata.

Output: `ContradictionObservation[]` plus a coverage receipt.

This prompt does not ask for omissions、dependency repair、outcome rewrite or final disposition. Each partition maps source propositions to stable Requirement predicates. Deterministic code verifies receipt coverage, globally joins observations across partitions, applies precedence, and derives validity impact. Model severity is advisory only. Timeout、truncation or partial union blocks the run rather than reporting an empty contradiction set.

## Stage 4 — Deterministic Proof Selection and Requirement Completeness

This stage has no model invocation.

Input:

- reconciled Requirements、validated binding candidates、globally reduced contradictions and policy bundle;
- DIRECT_ATOM/ALL_OF requirement DAG.

Output: proof-selected `EvidenceBinding[]` plus exactly one deterministic `RequirementAssessment` per effective Requirement.

For each required proof role, code selects eligible determinate evidence by versioned authority/proof policy. Selected bindings become canonical CRITICAL dependencies. Missing roles or only INDETERMINATE evidence produce `INSUFFICIENT_EVIDENCE`. ALL_OF uses a fixed conjunction table. This stage cannot add a Requirement、ref or semantic observation; `UNKNOWN_SOURCE_REQUIRED` is unrepresentable.

## Failure handling

### Structural failures

- schema/enum/local-ID/cross-link failure after one repair: structural terminal;
- unknown, unauthorized, stale, or illegal source ref: deterministic structural terminal;
- provider/auth/transport/budget unavailable: execution `BLOCKED`, not semantic rejection.
- incomplete/unknown SourceSet or partial contradiction receipts: `RUN_BLOCKED: CONTEXT_COVERAGE_INCOMPLETE`;
- applicable unsupported logic: typed `REJECTED_UNSUPPORTED_LOGIC` with no canonical graph.

### Semantic conditions

Missing support、indeterminate entailment、contradictions and outcome mismatch do not masquerade as structural errors. Once the effective Requirement set is representable, they reach the contradiction/proof/completeness stages before the gate.

## Provider strategy

Model adapters remain provider-neutral. Architecture acceptance follows this order:

1. OpenAI bounded DEV experiments falsify the method;
2. integrated DEV PASS permits full 120 DEV;
3. full DEV PASS and a complete method hash freeze permit one externally owned blind-holdout reveal/run;
4. DEV + blind holdout PASS permits live Gemini acceptance.

The implementation agent never generates or inspects holdout bodies before methodology freeze; only schema/version/hash metadata is visible.

Fake transports remain valid for deterministic contract tests only and never satisfy live-provider rows.
