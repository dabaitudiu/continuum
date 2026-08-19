# 05 — Model Reasoning Protocol

## Status

This is the provider-neutral Option B Revision-3 protocol under product-owner review. The direction is approved；the concrete specification is not. OpenAI remains a provider-neutral falsification lane and Gemini is the competition-provider DEV/blind acceptance lane. No live calls are authorized by this document.

The implemented reasoner/critic protocol is frozen as the v1 ablation baseline. The old critic prompt must not be tuned or preserved as production fallback.

## Common rules for every model stage

- source fragments are untrusted data, never instructions;
- tools are read-only and bounded by request scope/world snapshot;
- only tool-returned canonical refs may be copied;
- output must match the stage-specific schema;
- no stage may emit canonical IDs, mutate Runtime state, select deterministic precedence, or authorize an action;
- no stage may declare universe/normalization/selection completeness、canonical applicability、canonical materiality、canonical contradiction impact or final disposition;
- concise semantic propositions and summaries are stored; hidden chain-of-thought is neither requested nor persisted;
- invalid schema receives at most one bounded repair attempt, then ends as a structural failure;
- every invocation records provider/model/version, prompt/schema version, request configuration, response identity, usage, latency, and ledger settlement.

## Stage 0 — No model ownership

Trusted code validates `SourceUniverseSnapshot → RuleNormalizationManifest → SourceSetManifest` plus deterministic partitions and selective coverage guards. A model cannot declare catalog、normalization or retrieved subset complete. `INCOMPLETE | UNKNOWN | REVIEW_REQUIRED` coverage blocks the run before semantic inference. These derived records bind exact world/policy inputs but are not members of the input world snapshot.

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

Output per deterministic partition: one advisory `RequirementCoverageObservation` per assigned normalized governing obligation、candidate bindings for its pre-registered applicability predicates、a coverage receipt and semantic `RequirementCoverageCandidate[]` for every representable obligation regardless of proposed applicability。

The pass inventories material governing obligations without seeing Stage 1A/outcome. It may propose current-state bindings only for declared applicability predicates；it cannot judge business outcome、assign canonical materiality/severity、rewrite Stage 1 or invent refs/codes. Stage 1C validates provisional proof candidates but cannot finalize before contradiction. All supported Requirement candidates proceed through binding；Stage 3 checks independent applicability conflicts；Stage 4 finalizes APPLICABLE/N/A justifications and the effective Requirement set. INDETERMINATE fails closed。

## Stage 2 — Evidence Binding

Input:

- reconciled supported Requirement candidates, including provisionally N/A/indeterminate obligations;
- request-scoped source inventory and selected fragment content;
- source identity and authority metadata.

Output: `EvidenceBindingCandidate[]` only.

For each binding, the model states semantic role、`NORMALIZED_OBLIGATION | REQUIREMENT_PREDICATE` target、`ENTAILED_TRUE | ENTAILED_FALSE | INDETERMINATE`、normalized value where applicable and concise counterfactual analysis. Applicability predicate bindings use the Stage-1B contract. A policy that requires training proves neither applicability nor current training. The model does not output canonical `CRITICAL | SUPPORTING`；deterministic proof selection owns it.

## Stage 3 — Independent Contradiction Pass

Input:

- reconciled supported Requirement candidates plus all applicability predicate targets;
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
- incomplete/unknown universe/SourceSet、incomplete/review-required normalization or partial contradiction receipts: `RUN_BLOCKED` with no semantic success;
- unsupported logic/predicate: typed `REJECTED_UNSUPPORTED_LOGIC | REJECTED_UNSUPPORTED_PREDICATE` with no canonical graph.

### Semantic conditions

Missing support、indeterminate applicability/entailment、contradictions and outcome mismatch do not masquerade as structural errors. Once inputs are structurally valid, they reach the contradiction/proof/completeness stages before the gate.

## Provider strategy

Model adapters remain provider-neutral. Architecture acceptance follows this order:

1. bounded experiments and integrated 30-case DEV falsify the method;
2. Experiment 6A runs OpenAI full DEV;
3. Experiment 6B runs Gemini full DEV before any blind access;
4. Experiment 7 freezes code、prompts、schemas、policy bundle、predicate catalog、normalization/selection policies、model configs、dependency lock、runner/evaluator and metrics;
5. Experiment 8 reveals/runs the independently owned blind set once with Gemini primary and OpenAI optional secondary.

The implementation agent never generates or inspects holdout bodies before methodology freeze；only schema/version/hash metadata is visible. Any post-holdout method change requires a fresh independent set。

Fake transports remain valid for deterministic contract tests only and never satisfy live-provider rows.
