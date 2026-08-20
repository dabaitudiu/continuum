# 06 — Decision Provenance and Invalidation

## Why this is the core

Continuum is not differentiated by persistence. It is differentiated by being able to answer:

> Which past AI decisions are no longer trustworthy after the world changed, and why?

## Decision creation contract

Each agent decision must return a structured proposal containing:

- `decision_type`
- `outcome`
- `reasoning_summary`
- `evidence_refs[]`
- `dependency_refs[]`
- `required_artifact_versions[]`
- `confidence` (informational, not runtime authority)

The control plane validates references before accepting the decision.

Compiler validation decides only whether to admit/canonicalize that immutable proposal. `REJECTED_* | NEEDS_HUMAN_REVIEW` are proposal-admission dispositions, not newly authored domain outcomes. If admitted, the canonical Decision outcome is the exact unchanged proposal outcome。

Content identity is constructed without fixed points：governed observations seal before their observation set；the set contains opaque request correlation but no proposal back-reference；the proposal then hashes the set。Compilation seals `CompilationCore → DecisionValidityEnvelope → DecisionJustification → FinalCompilationRecord`。The envelope contains only the core hash, never a final-record hash。

## Dependency extraction strategy

Prefer dependencies that correspond to concrete, versioned resources:

- policy document section/version;
- submitted evidence hash/revision;
- user/agent permission snapshot;
- previous explicit decision;
- vendor classification.

Avoid unbounded natural-language dependencies such as "market conditions" unless backed by a versioned evidence object.

## Direct invalidation

A Decision becomes `STALE` when a critical dependency is superseded and the dependency relation indicates that new versions may change validity.

Example:

`SecurityDecision D42 --GOVERNED_BY--> SecurityPolicy v12`

When v13 supersedes v12, D42 becomes stale.

## Propagation

For each newly stale node:

- traverse outgoing edges;
- for `downstream Decision --REQUIRES--> upstream Decision`, traverse the maintained reverse index from upstream to dependent downstream；
- if an edge's relation is validity-bearing (`REQUIRES`, `DERIVED_FROM`, `AUTHORIZES`), mark dependent decisions stale or actions blocked;
- do not automatically invalidate unrelated siblings.

D→D is always `REQUIRES`; D→Action/`SideEffectIntentCore` is `AUTHORIZES`。Before acceptance, Runtime requires every upstream exact Decision to already exist as immutable `ACCEPTED` and rejects cycles in both the exact-ID graph and supersession-lineage projection。Supersession never rewrites old proof edges。

## Selective revalidation plan

Output:

- stale decisions to recompute;
- missing evidence needed by new policy;
- blocked actions;
- unaffected decisions explicitly retained.

A judge should see both sides: **what changed** and **what did not need to rerun**.

## Supersession

Never overwrite D42. New security review creates D57:

- D57 `supersedes_decision_id = D42`
- D42 remains historical `STALE/SUPERSEDED`
- downstream new approval may reference D57.

## Critical prototype proof

Seed graph:

```text
Policy v12 -> D42 SecurityApproved -> D50 ProcurementApproved -> Action ActivateVendor
SOC2 A31 -> D42
FinancialReport F7 -> D43 FinancialApproved -> D50
```

Policy v13 supersedes v12.

Expected:

- D42 stale
- D50 stale
- ActivateVendor blocked
- D43 remains valid

This must be deterministic and covered by automated tests before agent integration.

Side-effect execution also checks provenance synchronously: before appending the ledger's `EXECUTING` transition, Runtime validates the immutable intent core and transition head plus authorizing Decision/upstream envelopes against every ChangeSet from each envelope's validated `semantic_sequence` through current. A relevant pre-execution change appends cancellation without issuing the external call；after `EXECUTING`, idempotency/reconciliation owns append-only external-outcome transitions。
