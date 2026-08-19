# 00 — Module Charter

## Name

**Semantic Dependency Compiler (SDC)**

## Role inside Continuum

The SDC sits between agent reasoning and Continuum's canonical decision graph.

```text
Enterprise artifacts / tools
        ↓
Domain agent emits immutable DecisionProposal + DecisionEntityContext
        ↓
Trusted Requirement templates + bounded Evidence/contradiction interpretation
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

P0 answers this only for gate-shaped approval decision classes with pre-registered versioned predicate catalogs and trusted reusable normalized governing-rule schemas, representable as atomic predicates plus conjunction. Arbitrary OR、threshold、exception、quantified、absence/`NOT_EXISTS` or otherwise unsupported semantics fail closed；a material obligation outside the catalog yields `REJECTED_UNSUPPORTED_PREDICATE` rather than invention/omission.

## P0 outcomes

The module must support:

1. Versioned source artifacts with stable identity.
2. Stable fragment/section references within artifacts.
3. Immutable domain-agent `DecisionProposal` ownership；compiler validates and never substitutes a business outcome.
4. Trusted `DecisionEntityContext` and reusable template→entity deterministic atomic Requirements rather than model-authored gates.
5. Complete template/obligation accounting so proposal-rationale omission is not a production single point of failure.
6. Three-state evidence binding with deterministic proof-selected CRITICAL/SUPPORTING materiality.
7. Fragment-complete no-top-K Evidence/applicability plans/receipts with explicit process-vs-semantic coverage distinction.
8. Deterministic reference/entity、temporal、authoritative universe、normalization and policy validation.
9. Deterministic completeness over template-instantiated `DIRECT_ATOM | ALL_OF` Requirements.
10. Scalable O(fragments+actual matches) independent contradiction detection with deterministic impact.
11. Canonical graph compilation with stable semantic identity and reproducible output.
12. Fail-closed behavior for unsupported logic/predicate/absence.
13. Validity-bearing applicability and finite temporal proofs.
14. Selective invalidation plus semantic-epoch authorization envelope without async stale window.
15. Method-blind annotations、K6 generality metrics、paired adversarial/mutation outcomes and external blind set.
16. Live Gemini DEV before blind reveal and Gemini-primary blind evaluation；mock-only validation is insufficient.

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

1. Domain agent owns the proposed business outcome；compiler/model cannot replace it.
2. Models interpret bounded Evidence/contradictions only；they cannot author Requirement、predicate/entity IDs or canonical source IDs.
3. Every dependency reference must resolve to an allowed, versioned source object.
4. Canonicalization must be deterministic for the same validated proposal/entity/snapshots/clock/epoch.
5. The compiler must never persist hidden chain-of-thought. Store structured claims, concise rationale, citations, and validation evidence only.
6. Unsupported/unknown ref/entity/semantic shape is a compilation error, not a warning.
7. Critical dependency omissions must be measurable through method-blind evaluation, not assumed away from receipts.
8. A decision cannot become canonically `VALID` merely because a model/domain agent says “approved”.
9. Demo-specific IDs such as `D42`, `ACME`, `policy-v13`, and `PEN_TEST` must not appear in compiler logic/templates.
10. Canonical materiality and contradiction impact are deterministic results, never model authority.
11. Accepted Decisions depend on selected proofs/applicability/temporal/epoch guards and materially used selective semantics, not the whole inventory as one coarse dependency.
12. Incomplete universe/normalization/selection/Evidence/contradiction coverage and unsupported logic/predicate/absence fail closed.
13. Compiler-derived records never join their input snapshot；Runtime denies at expiry or across uncovered newer semantic epochs.

## Why this module is competition-worthy

If successful, this module provides the non-trivial bridge between probabilistic model reasoning and deterministic long-running execution semantics. Without it, Continuum risks being a manually-authored DAG demo.
