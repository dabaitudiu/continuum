# 10 — Test Plan

## Test pyramid

### Unit tests

Focus on deterministic code:

- source identity;
- fragment resolution;
- temporal validity;
- scope checks;
- CompilerPolicyBundle ref/hash/world-snapshot validation;
- PolicyUsageTrace completeness and `UNVERSIONED_POLICY_INPUT` rejection;
- SourceSetManifest boundary、included/excluded inventory、retrieval version、coverage status and hash validation;
- stable PredicateIdentity and DIRECT_ATOM/ALL_OF normalization;
- per-obligation requirement-coverage receipt、APPLICABLE/NOT_APPLICABLE/INDETERMINATE validation and deterministic reconciliation;
- EvidenceBinding cross-links、applicability-vs-state target separation、three-state entailment、proof eligibility and proof-selected materiality;
- contradiction partition/receipt union、cross-partition join、deterministic precedence and impact;
- deterministic RequirementAssessment truth table, support paths, blocking IDs, and one-assessment-per-requirement;
- deterministic proof-role selection and opposite-truth conflict preservation;
- transitive Source → Claim → Claim → Decision reachability;
- deterministic `APPROVE | DENY | REVIEW` acceptance rules;
- deterministic minimal DecisionJustification independent of proposition display、case/domain/local-ID order;
- unsupported-logic typed fail-closed results;
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

### Integration tests

Use fake model outputs but real compiler pipeline and persistence.

Cases:

- valid decision compiles;
- unknown ref rejected;
- stale revision rejected;
- cross-scope ref rejected;
- a Stage-1 omission is recovered by independent coverage and flows through downstream stages;
- a missing/duplicate obligation receipt cannot appear as complete coverage;
- INDETERMINATE obligation applicability prevents normal acceptance;
- a Requirement without determinate proof evidence reaches contradiction and completeness before gate rejection;
- INDETERMINATE evidence cannot satisfy a DIRECT_ATOM;
- governing authority cannot masquerade as factual state evidence;
- equal-authority contradiction reaches a dedicated typed pass and forces review;
- model SUPPORTING/severity advisory cannot suppress selected-proof materiality or blocking contradiction impact;
- cross-partition contradiction is joined, while missing partition blocks the run;
- incomplete/unknown SourceSet fails closed;
- applicable unsupported OR/threshold/exception logic cannot canonicalize;
- a transitive Claim support path is accepted without redundant direct source edges;
- interpretation policy or SourceSetManifest revision makes an accepted Decision stale;
- only requirement-DAG roots connect to Decision; intermediate Claim → Decision edges are not duplicated;
- reasoner-only and old-critic baselines cannot call Runtime acceptance;
- no v2 failure falls back to old critic;
- runtime revision changes after compile → accept fails.

### Live Gemini contract tests

Credential-gated and explicitly separate from unit CI.

Must test:

- structured output schema;
- only allowed refs cited;
- Requirement output contains stable semantic predicates rather than refs;
- independent coverage recovers governing-obligation omissions;
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

- a Stage-1 omission is independently recovered and cannot silently accept;
- selected proof becomes CRITICAL regardless of model advisory wording;
- unselected/contextual evidence remains SUPPORTING/analysis-only;
- genuinely absent evidence becomes `INSUFFICIENT_EVIDENCE` and blocks at the gate;
- ambiguous evidence remains INDETERMINATE and cannot satisfy a gate;
- contradiction missed by v1 is found and typed;
- equal-authority conflict cannot silently accept;
- model severity cannot downgrade validity-critical conflict;
- complete contradiction partition union detects cross-partition conflict;
- incomplete partition union returns RUN_BLOCKED rather than zero contradictions;
- a critical fragment mutation makes an accepted Decision stale;
- a counterevidence fragment mutation makes an accepted DENY Decision stale;
- an unselected failed/satisfied sibling fragment mutation leaves that DENY Decision valid;
- supporting/irrelevant fragment mutation leaves it valid;
- stale historical evidence cannot authorize acceptance;
- SourceSetManifest incomplete/unknown state cannot accept;
- every materially used interpretation-policy/manifest revision can stale a Decision;
- paraphrased equivalent Requirement selects identical Runtime proof;
- paired injection cannot suppress Requirements/evidence/contradictions or flip outcome/disposition/mutation quality;
- prompt injection cannot create an authority edge;
- unsupported OR/threshold/exception/quantified logic returns typed no-canonical result;
- semantic incompleteness cannot skip contradiction/completeness;
- existing transitive Claim/Decision dependency semantics satisfy completeness;
- three-arm ablation routing and metrics are isolated correctly;
- production packages cannot import DEV ground truth or access externally held blind-holdout bodies.

The synthetic normative P0-1…P0-11 counterexamples in `15_REPLACEMENT_ARCHITECTURE.md` are mandatory architecture fixtures. They verify contracts only and cannot be reported as live-model or benchmark evidence.

## Mutation tests

Artificially:

- remove one source dependency;
- flip model advisory materiality/severity text and verify canonical result is unchanged;
- change revision;
- inject unknown ref;
- duplicate a fragment;
- modify one unrelated policy clause;
- change an interpretation-policy revision;
- remove one contradiction partition receipt;
- paraphrase a Requirement display string without changing structured semantics;
- replace determinate evidence with ambiguous text.

Compiler must behave predictably.

## Performance tests

P0 targets are modest but measurable:

- deterministic validation/canonicalization < 100 ms for a 100-node proposal on laptop, excluding model calls and partition planning;
- source registry lookup does not scan all source text;
- contradiction partition planning obeys versioned hard limits and never silently truncates;
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

The redesign experiment sequence remains bounded: targeted Experiments 2A/2B–4, then integrated 30-case Experiment 5. Full 120 DEV、externally owned blind holdout and live Gemini remain gated and are not run during architecture review. CI contains no blind-holdout bodies.
