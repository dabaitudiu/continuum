# 08 — Side-Effect Ledger

## Design status

The implemented local v1 ledger demonstrates idempotency/reconciliation but does not yet implement the Module 01 Revision-6 semantic-sequence final-reauthorization contract. The following additions are architecture-under-review only；no production code change is authorized until that architecture is approved and separately planned。

## Problem

A retryable agent runtime can accidentally duplicate real-world actions.

Example:

1. Procurement Agent calls `activate_vendor`.
2. Simulator commits vendor status `ACTIVE`.
3. Worker dies before receiving the response.
4. Runtime retries.

Without an idempotency protocol the vendor could be activated/provisioned twice or two external records could be created.

## Protocol

### Step 1 — ActionIntent

Before invoking a side-effecting tool, persist:

- action type;
- normalized request hash;
- deterministic idempotency key;
- target resource;
- status `INTENDED`.
- authorizing Decision ID and `DecisionValidityEnvelope` hash;
- preliminary authorization receipt、authorized `semantic_sequence` and exclusive `authorization_not_after`.

### Step 2 — Final reauthorization and execution start

In one conditional database transaction, `ReauthorizeForExecutionTxn` rereads the current owner-scope semantic sequence and checks the exact Decision/upstream envelopes、every intervening contiguous ChangeSet、trusted clock and side-effect policy. Under an unchanged pointer/hashes it persists a fresh execution-start receipt and transitions `INTENDED | RETRYABLE_FAILURE → EXECUTING`. Relevant change、range gap、invalid upstream、expiry or CAS race transitions to `CANCELLED_STALE_AUTHORIZATION`; the tool is not called。

After `EXECUTING` commits, call the external tool with the persisted idempotency key/executor fence. The external network call is not atomic with Continuum's database transaction。

### Step 3 — Commit

Persist external reference and mark `COMMITTED`.

### Retry behavior

- `COMMITTED`: return previous result; never execute again.
- `INTENDED` with no external evidence: retry may proceed.
- `EXECUTING/UNKNOWN`: reconcile with simulator/external system before retry.
- `RETRYABLE_FAILURE`: a new attempt must pass fresh execution reauthorization；`FAILED_FINAL` never retries automatically.
- `CANCELLED_STALE_AUTHORIZATION`: terminal for that intent；no external call occurred.

Crash semantics are exact：before reauthorization, retry the full check；after checking but before `EXECUTING` commit, the transaction rolls back；after `EXECUTING` but before/after the network call, reconcile by idempotency key and never blindly create a second logical operation；unknown outcomes remain `RECONCILIATION_REQUIRED`. Automatic execution requires an external idempotency + authoritative reconciliation contract, otherwise human reconciliation is mandatory。

## MVP actions

At minimum implement two:

1. `send_vendor_email` — idempotent.
2. `activate_vendor` — idempotent and blocks if upstream authorization is stale.

## Safety rule

No decision in `STALE`, `INVALID`, or `REVALIDATING` may authorize an irreversible external action.
