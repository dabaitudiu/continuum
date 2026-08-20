# 05 — Runtime Semantics

## Mission lifecycle

```text
CREATED
  -> RUNNING
  -> WAITING
  -> RUNNING
  -> REVALIDATING
  -> RUNNING
  -> COMPLETED
```

Alternative terminal states: `FAILED`, `CANCELLED`, `BLOCKED`.

## Wait semantics

An agent does not "sleep" in process memory.

When waiting:

1. persist all canonical state;
2. create a Commitment;
3. mark relevant WorkItem `WAITING`;
4. mission can become `WAITING` if no runnable work remains;
5. terminate/return worker execution normally.

## Wake semantics

When an event arrives:

1. persist event with unique event id;
2. query open commitments by trigger type;
3. evaluate deterministic match predicate;
4. atomically mark exactly one matching commitment `SATISFIED` per mission/commitment;
5. enqueue resume work;
6. mark mission `RUNNING` or `REVALIDATING`.

## Crash recovery

Canonical state lives outside the agent process. Recovery must not depend on reconstructing a chat transcript alone.

A recovered worker obtains:

- mission state;
- active work item;
- relevant decisions/evidence;
- open commitments;
- side-effect ledger;
- current policy/identity context.

## Semantic Resume algorithm

A resume operation is:

1. load checkpoint/domain state;
2. refresh world-artifact versions relevant to runnable work;
3. detect version drift;
4. mark directly affected decisions stale;
5. propagate invalidation over dependency graph;
6. compute minimal revalidation set;
7. prohibit actions downstream of stale authorization;
8. dispatch only revalidation/runnable work;
9. continue normal execution after new valid decisions exist.

## Epochs

Use mission `epoch` to make major world-state changes explicit.

- Epoch N: old policy snapshot.
- Drift event increments to N+1.
- Historical decisions preserve the epoch in which they were made.

Epoch is explanatory metadata; dependency edges, not epoch alone, determine invalidation.

Module 01 Revision 6 added a distinct owner-scope `semantic_sequence:uint64` for executable semantic publication. Revision 7 freezes that contract and adds only constructible content identity plus acyclic Decision proof acceptance。The sequence remains a strict total order over hash-chained ChangeSets；world/universe/policy/catalog component epochs describe which domains changed. Authorization/recovery must verify the exact contiguous sequence range, while dependency-key intersection still determines relevance。

Before an external side effect begins, `ReauthorizeForExecutionTxn` atomically checks the immutable `SideEffectIntentCore`、append-only transition head、current sequence、Decision/upstream envelopes and clock/policy, then appends `EXECUTING` or `CANCELLED_STALE_AUTHORIZATION`. Status/receipts/results never mutate `intent_core_hash`。The network call is not part of this transaction. Once `EXECUTING` persists, crash/unknown outcomes append reconciliation transitions using the stable idempotency key rather than pretending the effect never started。

Accepted Decision proof is also deterministic：`downstream Decision --REQUIRES--> upstream Decision` and `Decision --AUTHORIZES--> Action/SideEffect`。Runtime rejects self、exact-ID、two-node and supersession-lineage cycles before canonical acceptance；staleness propagates from upstream through the reverse `REQUIRES` index。

## Deterministic vs agentic responsibility

Deterministic runtime:

- status transitions;
- idempotency;
- dependency traversal;
- stale propagation;
- commitment matching;
- authorization blocking.

Gemini/agents:

- interpret documents;
- propose decisions;
- propose structured dependencies;
- explain impact;
- decide what evidence is missing within bounded task contracts.
