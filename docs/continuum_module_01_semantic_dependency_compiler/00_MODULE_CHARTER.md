# 00 — Module Charter

## Name

**Semantic Dependency Compiler (SDC)**

## Role inside Continuum

The SDC sits between agent reasoning and Continuum's canonical decision graph.

```text
Enterprise artifacts / tools
        ↓
Bounded model reasoning
        ↓
DecisionAnalysisProposal
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

P0 answers this only for gate-shaped approval decisions representable as atomic predicates plus conjunction. Arbitrary OR、threshold、exception、quantified or otherwise unsupported enterprise logic fails closed rather than being approximated.

## P0 outcomes

The module must support:

1. Versioned source artifacts with stable identity.
2. Stable fragment/section references within artifacts.
3. Gemini-generated structured decision proposals.
4. Atomic semantic Requirements rather than one free-text verdict.
5. Independent governing-obligation coverage so Stage-1 omission is not a production single point of failure.
6. Three-state evidence binding with deterministic proof-selected CRITICAL/SUPPORTING materiality.
7. Deterministic reference、temporal、source-universe and interpretation-policy validation.
8. Deterministic completeness over reconciled `DIRECT_ATOM | ALL_OF` Requirements.
9. Coverage-preserving independent contradiction detection with deterministic validity impact.
10. Canonical graph compilation with stable semantic identity and reproducible output.
11. Fail-closed behavior for unsupported logical forms.
12. A benchmark with DEV ground truth、paired adversarial/mutation outcomes and an externally held blind generalization set.
13. Live Gemini evaluation; mock-only validation is insufficient.

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
9. Canonical materiality and contradiction impact are deterministic results, never model authority.
10. Accepted Decisions depend on the exact source manifest and interpretation-policy revisions used to justify them.
11. Incomplete source/partition coverage and unsupported logic fail closed.

## Why this module is competition-worthy

If successful, this module provides the non-trivial bridge between probabilistic model reasoning and deterministic long-running execution semantics. Without it, Continuum risks being a manually-authored DAG demo.
