# 08 — Side-Effect Ledger

## Design status

The implemented local v1 ledger demonstrates idempotency/reconciliation but does not yet implement the Module 01 Revision-7 immutable-intent/append-only-transition and semantic-sequence final-reauthorization contracts. P0-1～P0-37 remain frozen；the following P0-38 representation amendment is architecture-under-review only。No production code change is authorized until the architecture is approved and separately planned。

## Problem

A retryable agent runtime can accidentally duplicate real-world actions.

Example:

1. Procurement Agent calls `activate_vendor`.
2. Simulator commits vendor status `ACTIVE`.
3. Worker dies before receiving the response.
4. Runtime retries.

Without an idempotency protocol the vendor could be activated/provisioned twice or two external records could be created.

## Protocol

### Step 1 — Immutable intent core + admission transition

Before invoking a side-effecting tool, seal `SideEffectIntentCore` from exactly：

- owner scope、mission、action type and normalized request hash；
- deterministic idempotency key；
- authorizing Decision ID/hash and `DecisionValidityEnvelope` hash；
- preliminary intent-admission receipt、admitted `semantic_sequence` and exclusive `authorization_not_after`；
- creation time under the `SideEffectIntentCore,v7` hash schema。

Status、execution receipt、attempt/fence and external result are excluded from `intent_core_hash`。In the same conditional transaction, derive the registered intent-scoped `SideEffectTransitionGenesis,v7` predecessor、append transition `0: NONE→INTENDED` and advance the mutable, non-content-addressed `SideEffectLedgerHead`。

### Step 2 — Final reauthorization and execution start

In one conditional database transaction, `ReauthorizeForExecutionTxn` verifies the immutable core、complete contiguous transition chain/head、current owner-scope semantic sequence、exact Decision/upstream envelopes、every intervening contiguous ChangeSet、trusted clock and side-effect policy. Under unchanged semantic/ledger pointers/hashes it seals a fresh execution-start receipt and appends `INTENDED | RETRYABLE_FAILURE → EXECUTING`. Relevant change、range gap、invalid upstream、expiry or CAS race appends `CANCELLED_STALE_AUTHORIZATION`; the tool is not called。

After `EXECUTING` commits, call the external tool with the persisted idempotency key/executor fence. The external network call is not atomic with Continuum's database transaction。

### Step 3 — Commit

Append an immutable transition to `COMMITTED` with the authoritative external reference/result hash and advance the head by CAS。No prior record is rewritten。

### Retry behavior

- head=`COMMITTED`: return previous result; never execute again.
- head=`INTENDED` with no external evidence: retry may proceed through reauthorization.
- head=`EXECUTING | RECONCILIATION_REQUIRED`: reconcile with simulator/external system before retry.
- head=`RETRYABLE_FAILURE`: a new attempt must pass fresh execution reauthorization；`FAILED_FINAL` never retries automatically.
- head=`CANCELLED_STALE_AUTHORIZATION`: terminal for that intent；no external call occurred.

Every transition uses `transition_sequence=n+1` and `previous_transition_hash=current_head.latest_transition_hash`。Gap、fork、wrong predecessor、illegal status edge、history mutation or head mismatch blocks execution/reconciliation；repair is a new append, never an edit。Crash semantics are exact：before reauthorization, retry the full check；after checking but before the `EXECUTING` append commits, the transaction rolls back；after `EXECUTING` but before/after the network call, reconcile by idempotency key and never blindly create a second logical operation；unknown outcomes append `RECONCILIATION_REQUIRED`. Automatic execution requires an external idempotency + authoritative reconciliation contract, otherwise human reconciliation is mandatory。

## MVP actions

At minimum implement two:

1. `send_vendor_email` — idempotent.
2. `activate_vendor` — idempotent and blocks if upstream authorization is stale.

## Safety rule

No decision in `STALE`, `INVALID`, or `REVALIDATING` may authorize an irreversible external action.
