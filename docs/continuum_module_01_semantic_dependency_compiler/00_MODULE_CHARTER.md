# 00 — Module Charter

## Name

**Semantic Dependency Compiler (SDC)**

## Role inside Continuum

The SDC sits between agent reasoning and Continuum's canonical decision graph.

```text
Enterprise artifacts / tools
        ↓
Gemini bounded reasoning
        ↓
Decision Draft
        ↓
Semantic Dependency Compiler
        ↓
Compilation Result
        ↓
Continuum Runtime commits canonical Decision + Dependencies
```

## Problem boundary

The existing spike proves that a dependency graph can be invalidated deterministically **once the graph already exists**. This module solves the harder prior problem:

> How do we obtain a trustworthy dependency graph from real AI reasoning over messy enterprise inputs?

## P0 outcomes

The module must support:

1. Versioned source artifacts with stable identity.
2. Stable fragment/section references within artifacts.
3. Gemini-generated structured decision proposals.
4. Atomic claims rather than one free-text verdict.
5. Explicit material dependency references for claims and decisions.
6. Deterministic reference validation and temporal validation.
7. A second-pass completeness check for omitted material dependencies.
8. Contradiction detection across sources.
9. Canonical graph compilation with reproducible output.
10. A benchmark with ground-truth dependency sets and drift outcomes.
11. Live Gemini evaluation; mock-only validation is insufficient.

## Non-goals

This module does **not** own:

- mission scheduling;
- Pub/Sub wakeups;
- side-effect execution;
- Agent Runtime deployment;
- generic document search for arbitrary users;
- a full RAG platform;
- chain-of-thought capture;
- runtime stale propagation;
- compensation workflows.

## Hard invariants

1. Gemini can propose dependencies; it cannot create canonical source IDs.
2. Every dependency reference must resolve to an allowed, versioned source object.
3. Canonicalization must be deterministic for the same validated proposal.
4. The compiler must never persist hidden chain-of-thought. Store structured claims, concise rationale, citations, and validation evidence only.
5. An unsupported or unknown reference is a compilation error, not a warning.
6. Critical dependency omissions must be measurable through evaluation, not assumed away.
7. A decision cannot become canonically `VALID` merely because Gemini says “approved”.
8. Demo-specific IDs such as `D42`, `ACME`, `policy-v13`, and `PEN_TEST` must not appear in compiler logic.

## Why this module is competition-worthy

If successful, this module provides the non-trivial bridge between probabilistic model reasoning and deterministic long-running execution semantics. Without it, Continuum risks being a manually-authored DAG demo.
