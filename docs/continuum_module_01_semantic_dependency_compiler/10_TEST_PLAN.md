# 10 — Test Plan

## Test pyramid

### Unit tests

Focus on deterministic code:

- source identity;
- fragment resolution;
- proposal producer/outcome immutability、entity-role binding and cross-entity rejection；
- temporal validity guard and exclusive authorization horizon;
- scope checks;
- separate enterprise-world/policy snapshots and exact derived-artifact envelope validation;
- PolicyUsageTrace completeness and `UNVERSIONED_POLICY_INPUT` rejection;
- SourceUniverse authority/namespace/enumeration/watermark/hash validation;
- RuleNormalizationManifest exact fragment accounting、parser/reviewer receipts and no silent omission;
- SourceSetManifest boundary、included/excluded rule inventory、retrieval version、coverage status/hash and selective guard derivation;
- stable PredicateIdentity and DIRECT_ATOM/ALL_OF normalization；P0 `NOT_EXISTS`、`EXISTS+FALSE` and retrieval absence rejection；
- trusted reusable template instantiation、per-obligation accounting、entity-bound IDs、APPLICABLE/NOT_APPLICABLE proof and INDETERMINATE;
- EvidenceCoveragePlan eligibility/no-top-K limits、one-wrapper-per-fragment receipts、actual-match caps and partial/dense blocking；
- EvidenceBinding cross-links、applicability-vs-state target separation、three-state entailment、proof eligibility and proof-selected materiality;
- scalable fragment contradiction partition/receipt union、actual-match output、cross-partition entity-aware join、precedence and impact;
- deterministic RequirementAssessment truth table, support paths, blocking IDs, and one-assessment-per-requirement;
- deterministic proof-role selection and opposite-truth conflict preservation;
- transitive Source → Claim → Claim → Decision reachability;
- deterministic `APPROVE | DENY | REVIEW` acceptance rules;
- proposal outcome mismatch rejects without replacement；
- `DecisionValidityEnvelope` epoch vector、irrelevance-certificate chain and authorization denial across uncovered changes；
- deterministic minimal DecisionJustification independent of proposition display、case/domain/local-ID order;
- unsupported-logic and unsupported-predicate typed fail-closed results;
- canonical edge normalization;
- duplicate edge handling;
- materiality rules;
- compilation hashing;
- schema rejection.

### Property tests

Useful invariants:

- canonicalization idempotence;
- edge ordering independence;
- adding unrelated source fragments cannot alter deterministic validation of existing refs;
- duplicate proposal dependencies do not create duplicate canonical edges;
- paraphrasing display text cannot change semantic IDs、proof selection or Runtime edges;
- adding an unselected candidate cannot override a higher-precedence stable proof;
- every complete partitioning of the same inventory reduces to the same contradiction set;
- incomplete receipt union can never have completed contradiction status.
- incomplete Evidence receipt union can never have completed discovery status；
- model match count/output grows with fragments + actual matches, not fragments × predicates；
- changing proposal outcome never lets compiler canonicalize a different outcome under the same proposal ID；
- time passage to exact exclusive horizon denies authorization without source mutation；
- any uncovered newer semantic epoch denies side-effect authorization；
- changing an irrelevant inventory artifact may change audit manifest hash but not selective Runtime guard/edge set;
- semantically relevant catalog/rule/selection changes alter only matching coverage guards.

### Integration tests

Use fake model outputs but real compiler pipeline and persistence.

Cases:

- valid decision compiles;
- unknown ref rejected;
- stale revision rejected;
- cross-scope ref rejected;
- a domain-proposal/rationale omission is supplied by trusted template instantiation and flows downstream;
- a missing/duplicate template/obligation receipt cannot appear as complete accounting;
- Alice Requirement cannot use Bob evidence；Vendor-A cannot use Vendor-B evidence；
- Evidence/applicability fragment inventory has no silent top-K；missing/dense/partial receipt blocks；
- INDETERMINATE obligation applicability prevents normal acceptance;
- a Requirement without determinate proof evidence reaches contradiction and completeness before gate rejection;
- INDETERMINATE evidence cannot satisfy a DIRECT_ATOM;
- governing authority cannot masquerade as factual state evidence;
- equal-authority contradiction reaches a dedicated typed pass and forces review;
- model SUPPORTING/severity advisory cannot suppress selected-proof materiality or blocking contradiction impact;
- cross-partition contradiction is joined, while missing partition blocks the run;
- contradiction output emits one wrapper/ref plus actual matches and remains inside declared v4 call/token/output limits；
- incomplete/unknown SourceUniverse/SourceSet and incomplete/review-required normalization fail closed;
- applicable unsupported OR/threshold/exception logic cannot canonicalize;
- a transitive Claim support path is accepted without redundant direct source edges;
- selected applicability fact、material policy/rule/coverage guard revision makes affected Decision stale；unrelated whole-manifest change does not;
- only requirement-DAG roots connect to Decision; intermediate Claim → Decision edges are not duplicated;
- reasoner-only and old-critic baselines cannot call Runtime acceptance;
- no replacement failure falls back to old critic;
- runtime revision changes after compile → accept fails.
- source bytes unchanged but temporal horizon expires → authorization denied/Decision stale；
- enterprise、new-rule membership、policy、catalog/selector races across semantic epochs cannot authorize before stale/certification；
- material absence obligation produces `ABSENCE_PROOF_NOT_SUPPORTED_P0` with no canonical graph；
- proposal proof implies another outcome → supplied proposal rejected, no substitute Decision。

### Live Gemini contract tests

Credential-gated and explicitly separate from unit CI.

Must test:

- structured output schema;
- only allowed refs cited;
- model output cannot contain Requirement/outcome/entity-authoring fields；
- Evidence output returns exactly one wrapper per assigned fragment with only plan target keys；
- binding output uses three-state entailment and omits canonical materiality;
- deterministic proof selection derives CRITICAL/SUPPORTING;
- multiple source fragments;
- missing evidence case;
- contradiction case;
- paired clean/injected semantic-invariance case.

### Benchmark tests

Run Continuum Dependency Bench and publish metrics.

## Regression fixtures

Every discovered model failure becomes a fixture:

```text
bench/regressions/YYYY-MM-DD-case-name/
```

Include:

- source artifacts;
- expected critical refs;
- observed bad output;
- fixed prompt/compiler version.

New Option B regression fixtures must be method-level and must not branch on benchmark case IDs or known source refs. Required cases:

- a proposal/rationale omission is deterministically recovered from trusted templates and cannot silently accept;
- selected proof becomes CRITICAL regardless of model advisory wording;
- unselected/contextual evidence remains SUPPORTING/analysis-only;
- genuinely absent evidence becomes `INSUFFICIENT_EVIDENCE` and blocks at the gate;
- ambiguous evidence remains INDETERMINATE and cannot satisfy a gate;
- contradiction missed by v1 is found and typed;
- equal-authority conflict cannot silently accept;
- model severity cannot downgrade validity-critical conflict;
- complete contradiction partition union detects cross-partition conflict;
- incomplete partition union returns RUN_BLOCKED rather than zero contradictions;
- complete Evidence fragment union finds applicability/state candidates without top-K；partial/dense union blocks；
- contradiction map output is O(fragments+actual matches), not a negative cross-product；
- wrong-entity evidence never satisfies/canonicalizes a Requirement；invented entity/target is invalid structure；
- a critical fragment mutation makes an accepted Decision stale;
- a counterevidence fragment mutation makes an accepted DENY Decision stale;
- an unselected failed/satisfied sibling fragment mutation leaves that DENY Decision valid;
- supporting/irrelevant fragment mutation leaves it valid;
- stale historical evidence cannot authorize acceptance;
- SourceSet cannot declare complete without authoritative complete SourceUniverse root;
- every fragment has exactly one normalization accounting outcome；silent parser omission cannot accept;
- APPLICABLE all-true and NOT_APPLICABLE stable-false proof；unsupported N/A becomes INDETERMINATE;
- applicability true→false and false→true both stale prior accepted Decisions;
- relevant new governing source/selector/catalog/rule/eligibility change stales affected Decision;
- unrelated inventory/supporting content change does not stale merely because manifest hash changed;
- derived records never join their input world snapshot and future events reach guards without historical mutation;
- material unregistered predicate yields `REJECTED_UNSUPPORTED_PREDICATE`;
- `NOT_EXISTS`/empty-retrieval absence yields `ABSENCE_PROOF_NOT_SUPPORTED_P0`；
- time-sensitive proof missing horizon is insufficient；exact expiry denies authorization without source revision；
- valid proposal whose proof supports another class is rejected without outcome substitution；
- uncovered semantic-epoch races for enterprise/new-rule/policy/catalog changes deny authorization；
- K6 fixtures contain zero case-specific predicates/rules/dependency templates and new in-scope cases reuse frozen schemas；
- paraphrased equivalent Requirement selects identical Runtime proof;
- paired injection cannot suppress Requirements/evidence/contradictions or flip outcome/disposition/mutation quality;
- prompt injection cannot create an authority edge;
- unsupported OR/threshold/exception/quantified logic returns typed no-canonical result;
- semantic incompleteness cannot skip contradiction/completeness;
- existing transitive Claim/Decision dependency semantics satisfy completeness;
- three-arm ablation routing and metrics are isolated correctly;
- method-blind DEV annotation is frozen before replacement output、versioned/hashed/append-only and unavailable to production;
- experiment order is OpenAI DEV → Gemini DEV → freeze → Gemini-primary blind；production/agents cannot access blind bodies.

The synthetic normative P0-1…P0-27 counterexamples in `15_REPLACEMENT_ARCHITECTURE.md` are mandatory architecture fixtures. They verify contracts only and cannot be reported as live-model or benchmark evidence.

## Mutation tests

Artificially:

- remove one source dependency;
- flip model advisory materiality/severity text and verify canonical result is unchanged;
- change revision;
- inject unknown ref;
- duplicate a fragment;
- modify one unrelated policy clause;
- change an interpretation-policy revision;
- transition an applicability fact in both directions;
- advance trusted time to immediately before、exactly at and after `valid_until`；
- bind Alice's target to Bob's evidence and swap Vendor A/B；
- attempt compiler outcome substitution under the same proposal ID；
- advance enterprise/universe/policy/catalog semantic epochs with and without valid irrelevance certificates；
- add one relevant governing source and one irrelevant inventory artifact;
- change normalization/selection/catalog semantics independently;
- remove one Evidence or contradiction partition receipt；force dense-match limit；
- paraphrase a Requirement display string without changing structured semantics;
- replace determinate evidence with ambiguous text.

Compiler must behave predictably.

## Performance tests

P0 targets are modest but measurable:

- deterministic validation/canonicalization < 100 ms for a 100-node template-instantiated graph on laptop, excluding model calls and partition planning;
- source registry lookup does not scan all source text;
- Evidence/contradiction partition planning obeys versioned v4 hard limits and never silently truncates；zero fragment-map repairs keep the actual worst case ≤128 calls、2,024,288 input and 1,245,184 output tokens combined;
- live Gemini latency recorded separately.

## CI split

### Required on every commit

- unit;
- integration;
- type checks;
- deterministic benchmark subset.

### Scheduled/manual credential job

- live Gemini benchmark;
- variance suite;
- adversarial model cases.

Mock tests can never turn a live-Gemini acceptance row green.

The redesign sequence remains bounded: Experiments 2A/2B–4、integrated 30-case Experiment 5、6A OpenAI full DEV、6B Gemini full DEV、7 freeze、8 Gemini-primary blind. None of the paid/full/blind stages runs during architecture review；CI contains no blind bodies。
