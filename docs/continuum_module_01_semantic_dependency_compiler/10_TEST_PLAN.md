# 10 — Test Plan

## Test pyramid

### Unit tests

Focus on deterministic code:

- source identity;
- fragment resolution;
- temporal validity;
- scope checks;
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
- critical claim without support rejected;
- critic omission blocks acceptance;
- contradiction forces review;
- runtime revision changes after compile → accept fails.

### Live Gemini contract tests

Credential-gated and explicitly separate from unit CI.

Must test:

- structured output schema;
- only allowed refs cited;
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
