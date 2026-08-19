# 02 — Architecture

## Status

The product owner selected **Option B's direction** on 2026-08-19 and rejected the first concrete specification. The former `DecisionDraft → validator → vague critic → canonicalizer` architecture remains rejected after K3. This document is the compiler topology overview; [15_REPLACEMENT_ARCHITECTURE.md](15_REPLACEMENT_ARCHITECTURE.md) Revision 2 is normative for typed contracts, coverage, proof authority, terminal semantics, migration, and ablation.

Revision 2 is presented for product-owner review and is not approved or implemented. Module 01 remains `REDESIGN REQUIRED`.

## Component topology

```mermaid
flowchart TD
    A[Artifact Ingestion + normalized governing rules] --> B[SourceRegistry / world snapshot]
    B --> C[0. CompilerPolicyBundle + SourceSetManifest]
    C --> C1[Coverage / hash / hard-limit validation]
    C1 -->|incomplete or partial| RB[RUN_BLOCKED]
    C1 --> D[1A. Requirement Decomposition]
    C1 --> E[1B. Independent Obligation Coverage]
    D --> F[1C. Deterministic Reconciliation]
    E --> F
    F --> G[2. Evidence Binding Candidates]
    G --> G1[Deterministic eligibility validation]
    G1 --> H[3A. Partitioned Contradiction Observations]
    H --> H1[3B. Complete global reduce + precedence + impact]
    H1 --> I[4. Deterministic Proof Selection + Completeness]
    I --> J[5. Deterministic Acceptance Gate]
    J -->|ACCEPTED| K[Deterministic Canonicalizer]
    J -->|REJECT / REVIEW| L[Immutable non-accepted CompilationResult]
    K --> M[Immutable accepted CompilationResult]
    M --> N[RuntimeAcceptanceService]
    N --> O[Continuum canonical Runtime]
```

Structural errors may take an early terminal path. Unknown/incomplete source coverage or partial contradiction partitions are execution-blocking, not semantic success. Unsupported governing logic produces a typed fail-closed result. Missing evidence, contradictions, indeterminate entailment, and outcome mismatch reach their relevant semantic stages before deterministic disposition.

## Trust boundaries

### Trusted deterministic boundary

- artifact/revision/representation/fragment identity;
- `CompilerPolicyBundle` and complete `SourceSetManifest` identity;
- request-scoped source inventory, coverage declaration, retrieval provenance, partitions, and access scope;
- schema and local-ID integrity;
- stable `PredicateIdentity` and normalized DIRECT_ATOM/ALL_OF topology;
- source-ref existence and canonical resolution;
- temporal validity and historical-read restrictions;
- source-type and authority relation rules;
- authority metadata and configured precedence;
- requirement reconciliation and binding/contradiction cross-link integrity;
- evidence proof eligibility, proof selection, and canonical materiality;
- contradiction inventory completion and validity impact;
- support-path reachability over the typed DAG;
- outcome-class rules and final compilation disposition;
- canonical IDs, ordering, deduplication, hashes, and compiler state transitions;
- validity-bearing provenance for all interpretation policies and the source manifest;
- immutable Runtime acceptance under exact mission revision/world snapshot.

### Probabilistic boundary

- semantic requirement decomposition;
- independent governing-obligation discovery;
- proposition-to-evidence role and entailment proposals;
- partitioned semantic contradiction observations;
- advisory counterfactual and contradiction severity text.

Model output is immutable analysis IR only. It cannot set canonical `CRITICAL | SUPPORTING`, canonical contradiction impact, deterministic precedence, source completeness, final disposition, Runtime mutations, Decision staleness, or side-effect authority.

## Compiler stages

### Stage 0 — Source and policy coverage

Resolve a versioned `CompilerPolicyBundle`; build and validate a complete, auditable `SourceSetManifest`; identify governing/contradiction-eligible refs; and construct a coverage-preserving partition plan. Incomplete/unknown coverage fails closed.

### Stage 1A — Requirement Decomposition

Produce one untrusted outcome proposal plus atomic stable predicates and an `ALL_OF` DAG. Display propositions are non-authoritative; structured predicate identity drives IDs and normalization.

### Stage 1B/1C — Independent Coverage and Reconciliation

An outcome-blind pass inventories material governing obligations without seeing Stage-1A output. Deterministic reconciliation merges candidates by semantic key and adds valid coverage-only omissions to the effective Requirement set. It never invents placeholder refs.

### Stage 2 — Evidence Binding

Propose canonical refs, semantic roles, and `ENTAILED_TRUE | ENTAILED_FALSE | INDETERMINATE`. The model does not assign canonical materiality. Deterministic proof selection later makes selected proof bindings CRITICAL.

### Stage 3 — Independent Contradiction Pass

Observe all current/in-scope contradiction-eligible fragments in deterministic partitions. Receipts prove full inventory coverage; a global reduce finds cross-partition conflicts, applies precedence, and derives validity impact from reachability/proof eligibility rather than model severity.

### Stage 4 — Deterministic Proof Selection and Requirement Completeness

Select one stable proof per required role, derive canonical materiality, and compute every effective RequirementAssessment from determinate entailment, precedence, and DIRECT_ATOM/ALL_OF reachability. This stage has no model call.

### Stage 5 — Deterministic Acceptance Gate

Compute expected outcome class, validate the model proposal through versioned trusted semantics, and select a minimal justification by stable predicate/source/topology identity—never lexical proposition text. Only `ACCEPTED` invokes the canonicalizer.

## Execution state

```mermaid
stateDiagram-v2
    [*] --> RECEIVED
    RECEIVED --> CONTEXT_COVERAGE_VALIDATED
    CONTEXT_COVERAGE_VALIDATED --> REQUIREMENT_PASSES_RUNNING
    REQUIREMENT_PASSES_RUNNING --> REQUIREMENT_PASSES_COMPLETE: 1A + independent 1B both complete
    REQUIREMENT_PASSES_COMPLETE --> REQUIREMENTS_RECONCILED
    REQUIREMENTS_RECONCILED --> BINDINGS_VALIDATED
    BINDINGS_VALIDATED --> CONTRADICTIONS_VALIDATED
    CONTRADICTIONS_VALIDATED --> PROOFS_AND_COMPLETENESS_COMPUTED
    PROOFS_AND_COMPLETENESS_COMPUTED --> GATE_EVALUATED
    GATE_EVALUATED --> CANONICALIZED: ACCEPTED
    GATE_EVALUATED --> COMPLETED_NOT_ACCEPTED: REJECT / REVIEW
    CANONICALIZED --> COMPLETED_ACCEPTED

    RECEIVED --> RUN_BLOCKED: source coverage unknown / auth
    REQUIREMENT_PASSES_RUNNING --> RUN_BLOCKED: provider / budget
    REQUIREMENTS_RECONCILED --> RUN_BLOCKED: provider / budget
    BINDINGS_VALIDATED --> RUN_BLOCKED: partial contradiction partitions
    CONTEXT_COVERAGE_VALIDATED --> COMPLETED_UNSUPPORTED_LOGIC
    CONTEXT_COVERAGE_VALIDATED --> TERMINAL_STRUCTURAL_ERROR
    REQUIREMENTS_RECONCILED --> TERMINAL_STRUCTURAL_ERROR
    BINDINGS_VALIDATED --> TERMINAL_STRUCTURAL_ERROR
    RECEIVED --> RUN_FAILED: internal / persistence invariant
    CONTEXT_COVERAGE_VALIDATED --> RUN_FAILED: internal / persistence invariant
    REQUIREMENTS_RECONCILED --> RUN_FAILED: internal / persistence invariant
    BINDINGS_VALIDATED --> RUN_FAILED: internal / persistence invariant
    CONTRADICTIONS_VALIDATED --> RUN_FAILED: internal / persistence invariant
    PROOFS_AND_COMPLETENESS_COMPUTED --> RUN_FAILED: internal / persistence invariant
```

Execution status and semantic disposition are separate. A blocked provider call does not become a semantic rejection, and a semantic rejection cannot expose canonical graph state.

## Canonical graph shape

```text
SourceFragment
  --SUPPORTED_BY / GOVERNED_BY[CRITICAL]-->
Claim(requirement assessment)
  --DERIVED_FROM / REQUIRES[CRITICAL]-->
Claim(derived requirement)
  --REQUIRES[CRITICAL]-->
Decision

CompilerPolicyArtifact / SourceSetManifestArtifact
  --GOVERNED_BY[CRITICAL]-->
Claim(decision interpretation)
  --REQUIRES[CRITICAL]-->
Decision
```

Support and later invalidation use graph reachability. Existing Source → Claim → Claim → Decision semantics remain valid. Canonical state contains only Stage-4 selected proof bindings plus every materially participating interpretation-policy/manifest ref. APPROVE uses all root closures; DENY uses one stable failed path selected without proposition text. No redundant direct edge is required.

## Integration boundary

The compiler produces an immutable `CompilationResult`. `RuntimeAcceptanceService` alone may translate an accepted canonical result into Runtime graph mutations, after checking the exact mission revision, world snapshot, policy bundle, and source manifest. Runtime still owns Decision lifecycle, stale propagation, action blocking, and side-effect authorization.

The old critic and reasoner-only routes remain only as explicit benchmark baselines during migration. Neither is a production fallback for the replacement pipeline.
