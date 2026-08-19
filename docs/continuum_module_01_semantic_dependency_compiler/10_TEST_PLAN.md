# 10 — Test Plan

## Test pyramid

### Unit tests

Focus on deterministic code:

- source identity;
- fragment resolution;
- temporal validity;
- scope checks;
- Requirement schema, expected truth, DIRECT/DERIVED_ALL rules, and conjunction-DAG integrity;
- EvidenceBinding cross-links and CRITICAL/validity-impact consistency;
- Contradiction pair validation and deterministic precedence;
- deterministic RequirementAssessment truth table, support paths, blocking IDs, and one-assessment-per-requirement;
- deterministic same-truth proof-binding selection and opposite-truth conflict preservation;
- transitive Source → Claim → Claim → Decision reachability;
- deterministic `APPROVE | DENY | REVIEW` acceptance rules;
- deterministic minimal DecisionJustification selection independent of case/domain/local-ID order;
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
- duplicate proposal dependencies do not create duplicate canonical edges.

### Integration tests

Use fake model outputs but real compiler pipeline and persistence.

Cases:

- valid decision compiles;
- unknown ref rejected;
- stale revision rejected;
- cross-scope ref rejected;
- a Requirement without CRITICAL evidence reaches contradiction and completeness before gate rejection;
- equal-authority contradiction reaches a dedicated typed pass and forces review;
- a transitive Claim support path is accepted without redundant direct source edges;
- only requirement-DAG roots connect to Decision; intermediate Claim → Decision edges are not duplicated;
- reasoner-only and old-critic baselines cannot call Runtime acceptance;
- no v2 failure falls back to old critic;
- runtime revision changes after compile → accept fails.

### Live Gemini contract tests

Credential-gated and explicitly separate from unit CI.

Must test:

- structured output schema;
- only allowed refs cited;
- Requirement output contains propositions rather than refs;
- CRITICAL/SUPPORTING EvidenceBinding separation;
- multiple source fragments;
- missing evidence case;
- contradiction case;
- prompt-injected document case.

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

- supporting evidence is not promoted to CRITICAL;
- a v1 material omission becomes an explicit Requirement/Binding, enters the accepted canonical graph, and affects Runtime invalidation;
- genuinely absent evidence becomes `INSUFFICIENT_EVIDENCE` and blocks at the gate;
- contradiction missed by v1 is found and typed;
- equal-authority conflict cannot silently accept;
- a critical fragment mutation makes an accepted Decision stale;
- a counterevidence fragment mutation makes an accepted DENY Decision stale;
- an unselected failed/satisfied sibling fragment mutation leaves that DENY Decision valid;
- supporting/irrelevant fragment mutation leaves it valid;
- stale historical evidence cannot authorize acceptance;
- prompt injection cannot create an authority edge;
- semantic incompleteness cannot skip contradiction/completeness;
- existing transitive Claim/Decision dependency semantics satisfy completeness;
- three-arm ablation routing and metrics are isolated correctly;
- production packages cannot import DEV/HOLDOUT ground truth.

## Mutation tests

Artificially:

- remove one source dependency;
- flip materiality;
- change revision;
- inject unknown ref;
- duplicate a fragment;
- modify one unrelated policy clause.

Compiler must behave predictably.

## Performance tests

P0 targets are modest but measurable:

- deterministic validation/canonicalization < 100 ms for a 100-node proposal on laptop;
- source registry lookup does not scan all source text;
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

The redesign experiment sequence remains bounded: targeted Experiments 2–4, then integrated 30-case Experiment 5. Full 120 DEV, locked holdout, and live Gemini remain gated and are not run during architecture review.
